# Sections 13-18: Testing, CI/CD, Distribution, Launch (Standalone)

## Section 13: Testing

### 13.1 — Test Architecture
- **Unit tests**: 60% — crypto, validators, currency conversion, pagination
- **Integration tests**: 35% — API endpoints with in-memory SQLite
- **E2E tests**: 5% — Full setup → login → create asset → export flow
- **Target coverage**: 85%+
- **DB strategy**: In-memory SQLite (`sqlite+aiosqlite:///:memory:`) — no testcontainers needed

### 13.2 — Key Test Changes from Cloud Version

| Aspect | Cloud Version | Standalone Version |
|---|---|---|
| Test DB | testcontainers PostgreSQL | In-memory SQLite (instant) |
| Auth fixtures | JWT cookie helpers | Session token headers |
| Currency assertions | Compare float | Compare integer paise |
| File storage tests | Mock S3 boto3 | Real temp directory |
| Report generation | Mock Celery task | Direct function call |

### 13.3 — Test Configuration

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import create_app
from app.models.base import Base
from app.dependencies import get_db

@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession)
    async with session_factory() as session:
        yield session

@pytest_asyncio.fixture
async def client(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture
async def registered_user(client):
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "Arjun Sharma",
        "email": "arjun@test.com",
        "password": "SecureP@ss123!",
        "security_question": "First pet name?",
        "security_answer": "Bruno"
    })
    return resp.json()["data"]

@pytest_asyncio.fixture
async def auth_headers(client, registered_user):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "arjun@test.com", "password": "SecureP@ss123!"
    })
    token = resp.json()["data"]["session_token"]
    return {"Authorization": f"Bearer {token}"}
```

### 13.4 — Sample Integration Tests

```python
# tests/integration/test_auth.py
import pytest
pytestmark = pytest.mark.asyncio

async def test_register_first_user(client):
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "Arjun Sharma", "email": "arjun@test.com",
        "password": "SecureP@ss123!",
        "security_question": "First pet?", "security_answer": "Bruno"
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "arjun@test.com"

async def test_register_second_user_blocked(client, registered_user):
    """Standalone app: only one user allowed."""
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "Second User", "email": "second@test.com",
        "password": "SecureP@ss123!",
        "security_question": "Pet?", "security_answer": "Cat"
    })
    assert resp.status_code == 409  # Only one user allowed

async def test_login_success(client, registered_user):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "arjun@test.com", "password": "SecureP@ss123!"
    })
    assert resp.status_code == 200
    assert "session_token" in resp.json()["data"]

async def test_login_wrong_password(client, registered_user):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "arjun@test.com", "password": "WrongPassword"
    })
    assert resp.status_code == 401

async def test_password_reset_via_security_question(client, registered_user):
    resp = await client.post("/api/v1/auth/reset-password-local", json={
        "email": "arjun@test.com",
        "security_answer": "Bruno",
        "new_password": "NewSecureP@ss456!"
    })
    assert resp.status_code == 200
    # Verify new password works
    resp2 = await client.post("/api/v1/auth/login", json={
        "email": "arjun@test.com", "password": "NewSecureP@ss456!"
    })
    assert resp2.status_code == 200


# tests/integration/test_assets.py
async def test_create_asset(client, auth_headers):
    resp = await client.post("/api/v1/assets", json={
        "asset_type_id": "at_mf", "name": "HDFC Mid Cap",
        "invested_amount": 100000.00, "current_value": 125000.00,
        "purchase_date": "2024-01-15"
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["pl_amount"] == 25000.00
    assert data["pl_percentage"] == 25.0

async def test_create_asset_paise_precision(client, auth_headers):
    """Verify currency stored as paise doesn't lose precision."""
    resp = await client.post("/api/v1/assets", json={
        "asset_type_id": "at_mf", "name": "Precision Test",
        "invested_amount": 1234.56, "current_value": 1234.57
    }, headers=auth_headers)
    data = resp.json()["data"]
    assert data["invested_amount"] == 1234.56
    assert data["current_value"] == 1234.57
    assert data["pl_amount"] == 0.01


# tests/integration/test_vault.py
async def test_vault_encryption_at_rest(client, auth_headers, db_session):
    # Setup master password
    await client.post("/api/v1/users/setup-wizard", json={
        "step": 2, "data": {"master_password": "MasterP@ss123!"}
    }, headers=auth_headers)
    # Unlock vault
    await client.post("/api/v1/vault/unlock",
        json={"master_password": "MasterP@ss123!"}, headers=auth_headers)
    # Create credential
    await client.post("/api/v1/vault/credentials", json={
        "service_name": "Gmail", "username": "arjun@gmail.com",
        "password": "GmailSecret123", "category_id": "vc_social"
    }, headers=auth_headers)
    # Verify raw DB value is encrypted
    from sqlalchemy import text
    result = await db_session.execute(text("SELECT password_enc FROM vault_credentials LIMIT 1"))
    raw = result.scalar_one()
    assert raw != "GmailSecret123"
    assert len(raw) > 40  # Base64 ciphertext
```

### 13.5 — Test Command
```bash
pytest tests/ -v --tb=short --cov=app --cov-report=term-missing \
    --asyncio-mode=auto --timeout=30 -x
```

---

## Section 14: CI/CD Pipeline (Build & Release)

No deployment to servers. CI builds the app and creates GitHub Releases.

```yaml
# .github/workflows/ci.yml
name: FinVault CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ruff black mypy
      - run: ruff check app/ tests/
      - run: black --check app/ tests/
      - run: mypy app/ --ignore-missing-imports

  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements/base.txt -r requirements/dev.txt
      - run: pytest tests/ -v --cov=app --cov-report=xml --asyncio-mode=auto
      - uses: codecov/codecov-action@v4
        with: { files: coverage.xml }

# .github/workflows/release.yml
name: Build & Release

on:
  push:
    tags: ["v*"]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements/base.txt pyinstaller
      - run: python scripts/build.py
      - name: Zip artifact
        run: Compress-Archive -Path dist/FinVault/* -DestinationPath FinVault-${{ github.ref_name }}-windows.zip
      - uses: softprops/action-gh-release@v2
        with:
          files: FinVault-${{ github.ref_name }}-windows.zip
          generate_release_notes: true

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements/base.txt pyinstaller
      - run: python scripts/build.py
      - run: tar -czf FinVault-${{ github.ref_name }}-linux.tar.gz -C dist FinVault/
      - uses: softprops/action-gh-release@v2
        with:
          files: FinVault-${{ github.ref_name }}-linux.tar.gz
```

### Release Workflow
```
Developer:
  git tag v1.0.0
  git push origin v1.0.0

GitHub Actions:
  → Lint → Test → Build Windows exe → Build Linux binary → Create GitHub Release

User:
  → Go to GitHub Releases → Download zip → Extract → Run FinVault.exe
```

---

## Section 15: "Deployment" (It's Just Running an EXE)

No server deployment. No infrastructure diagram. The "deployment" is:

```
1. User downloads FinVault-v1.0.0-windows.zip (GitHub Releases)
2. Extracts to C:\FinVault\ (or any folder)
3. Runs FinVault.exe
4. Server starts on localhost:8000
5. Browser opens automatically
6. First run: Setup wizard (create account, set master password)
7. Subsequent runs: Login screen
```

Data location: `%LOCALAPPDATA%\FinVault\` (Windows) or `~/.finvault/` (Linux/Mac)

---

## Section 16: Monitoring (Local Logging)

No Prometheus, no Grafana, no Sentry. Just log files.

```python
# Configured in app/main.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_dir: Path):
    log_file = log_dir / "finvault.log"
    handler = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=5)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.WARNING)
```

The Settings page shows:
- App version
- Database file size
- Storage directory size
- Last backup date
- Log file location (for debugging)

---

## Section 17: Data Privacy (Simplified)

Since data never leaves the user's machine:
- **No DPDP Act compliance needed** — you don't process personal data, the user does locally
- **No privacy policy needed** — no data collection
- **No cookie banner** — no cookies
- **No data breach notification** — no server to breach
- **User owns all data** — it's a file on their disk they can copy, delete, or move

---

## Section 18: Launch Checklist (Standalone)

### Build
- [ ] `make build` succeeds on Windows
- [ ] `make build` succeeds on Linux
- [ ] Exe starts and opens browser
- [ ] SQLite database created on first run
- [ ] Alembic migrations run on first launch
- [ ] Seed data populated (asset types, expense categories, vault categories)

### Core Flow
- [ ] First-run setup wizard completes (profile, master password, categories)
- [ ] Login/logout works
- [ ] Password reset via security question works
- [ ] Auto-lock after inactivity works

### Assets
- [ ] Create, read, update, delete asset
- [ ] P&L computed correctly (paise precision)
- [ ] Image upload works (stored locally)
- [ ] Bulk CSV upload works
- [ ] SIP schedule CRUD works

### Expenses
- [ ] Create, read, update, delete expense
- [ ] Calendar view shows daily totals
- [ ] Category summary calculates percentages
- [ ] Household member CRUD works
- [ ] Custom categories work

### Vault
- [ ] Master password setup during wizard
- [ ] Vault unlock/lock works
- [ ] Credentials encrypted at rest (verified in raw DB)
- [ ] Credentials decrypted in UI after unlock
- [ ] Password generator works
- [ ] Bulk import/export works

### Reports
- [ ] Portfolio summary KPIs display
- [ ] Financial health score calculates
- [ ] PowerPoint export generates and downloads
- [ ] CSV export generates correctly (₹ formatting, UTF-8 BOM)

### Settings
- [ ] Manual backup creates .db copy
- [ ] Restore from backup works
- [ ] Export all data (JSON) works
- [ ] Import data works
- [ ] Clear expenses works
- [ ] Reset app works

### Distribution
- [ ] Windows zip < 150 MB
- [ ] Linux tar.gz < 150 MB
- [ ] GitHub Release created with release notes
- [ ] Download link works
- [ ] README includes quick start instructions
