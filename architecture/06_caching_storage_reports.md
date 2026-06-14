# Sections 9-12: Storage, Reports, Packaging & Config (Standalone)

## Section 9: File Storage (Local Filesystem)

### 9.1 — Storage Structure
```
~/.finvault/storage/
├── avatars/{user_id}.webp
├── asset-images/{asset_id}/{uuid}.webp
└── exports/{filename}.pptx
```

### 9.2 — Storage Service

```python
# app/services/file_storage_service.py
import shutil
from pathlib import Path
from uuid import uuid4
from PIL import Image
from app.utils.paths import get_storage_dir

class LocalFileStorage:
    def __init__(self):
        self.base = get_storage_dir()
        self.base.mkdir(parents=True, exist_ok=True)

    async def save_image(self, category: str, sub_id: str, file_data: bytes,
                          filename: str, max_width: int = 1920) -> str:
        """Save and optimize an image. Returns relative path."""
        ext = Path(filename).suffix.lower()
        dest_dir = self.base / category / sub_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_name = f"{uuid4()}.webp"
        dest_path = dest_dir / dest_name

        # Resize + convert to WebP
        img = Image.open(io.BytesIO(file_data))
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
        img.save(dest_path, "WEBP", quality=85)

        return f"{category}/{sub_id}/{dest_name}"

    async def get_file_path(self, relative_path: str) -> Path:
        return self.base / relative_path

    async def delete_file(self, relative_path: str) -> None:
        path = self.base / relative_path
        if path.exists():
            path.unlink()

    async def get_storage_size(self) -> int:
        """Total bytes used by storage directory."""
        return sum(f.stat().st_size for f in self.base.rglob("*") if f.is_file())
```

No signed URLs needed — files served directly via FastAPI `FileResponse`.

---

## Section 10: Report Generation (Synchronous)

Reports generated **synchronously** (no Celery task queue). The user clicks
"Export" and gets the file immediately — single user, no background queue needed.

```python
# app/services/export_service.py
from app.utils.currency import paise_to_rupees

async def generate_portfolio_report(
    db_session, user_id: str, date_from: str, date_to: str, sections: list[str]
) -> Path:
    """Generate PowerPoint report synchronously. Returns local file path."""
    # ... (same logic as cloud version: matplotlib charts → python-pptx slides)
    # Only difference: saves to local path instead of S3

    file_name = f"finvault_report_{date.today().isoformat()}.pptx"
    file_path = get_storage_dir() / "exports" / file_name
    file_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(file_path))

    # Record in DB
    export = ReportExport(id=str(uuid4()), user_id=user_id, format="pptx",
                          status="completed", file_path=f"exports/{file_name}",
                          date_from=date_from, date_to=date_to)
    db_session.add(export)
    await db_session.commit()

    return file_path
```

The API endpoint returns the file directly:

```python
# app/api/v1/reports.py
@router.post("/export")
async def export_report(request: ExportRequest, db=Depends(get_db), user=Depends(get_current_user)):
    file_path = await generate_portfolio_report(db, user.id, request.date_from, request.date_to, request.sections)
    return FileResponse(path=str(file_path), filename=file_path.name,
                        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
```

---

## Section 11: Packaging & Distribution (Replaces Docker)

### 11.1 — PyInstaller Build

```python
# scripts/build.py
import PyInstaller.__main__
import subprocess
import shutil
from pathlib import Path

def build():
    # No frontend build step needed — Jinja2 templates are served directly.
    # HTMX, Alpine.js, Chart.js are static vendor files already in app/static/vendor/.

    # Bundle with PyInstaller
    PyInstaller.__main__.run([
        "app/main.py",
        "--name=FinVault",
        "--onedir",
        "--add-data=app/templates:app/templates",  # Include Jinja2 templates
        "--add-data=app/static:app/static",        # Include CSS, JS, vendor libs, fonts
        "--add-data=alembic:alembic",              # Include migrations
        "--hidden-import=uvicorn",
        "--hidden-import=aiosqlite",
        "--hidden-import=sqlalchemy",
        "--hidden-import=jinja2",
        "--icon=app/static/img/favicon.ico",
        "--noconfirm",
    ])

if __name__ == "__main__":
    build()
```

### 11.2 — Distribution Format

```
FinVault-v1.0.0-windows/                     # Zip file
├── FinVault.exe                             # Main executable
├── _internal/                               # PyInstaller runtime (Python + deps)
├── README.txt                               # Quick start guide
└── LICENSE.txt
```

**User workflow:**
1. Download `FinVault-v1.0.0-windows.zip` from GitHub Releases
2. Extract to any folder
3. Double-click `FinVault.exe`
4. Browser opens `http://localhost:8000`
5. First run → setup wizard → start using

### 11.3 — App Startup Sequence

```python
# app/main.py — entry point
import sys
import webbrowser
import uvicorn
from pathlib import Path

def main():
    """Entry point for FinVault standalone app."""
    from app.utils.paths import ensure_app_dirs
    from app.database import run_migrations

    # 1. Create app data directories
    ensure_app_dirs()  # Creates ~/.finvault/ and subdirs

    # 2. Run database migrations (creates tables on first run)
    run_migrations()

    # 3. Open browser
    webbrowser.open("http://localhost:8000")

    # 4. Start server (blocks until Ctrl+C or window close)
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="127.0.0.1",          # Localhost only — not accessible from network
        port=8000,
        log_level="warning",
        access_log=False,
    )

if __name__ == "__main__":
    main()
```

---

## Section 12: Configuration (Standalone)

### 12.1 — Config File (`~/.finvault/config.ini`)

```ini
# FinVault Configuration
# Edit this file to customize behavior. Restart FinVault after changes.

[app]
port = 8000                          # Port for the local web server
auto_open_browser = true             # Open browser on startup
log_level = WARNING                  # DEBUG | INFO | WARNING | ERROR

[security]
auto_lock_minutes = 15               # Lock app after inactivity (0 = never)
vault_kdf_iterations = 600000        # PBKDF2 iterations (don't reduce below 600000)

[backup]
auto_backup = true                   # Daily automatic backup
max_backups = 30                     # Keep last N backup files

[display]
date_format = DD/MM/YYYY             # DD/MM/YYYY | MM/DD/YYYY | YYYY-MM-DD
currency = INR                       # ISO 4217 currency code
number_format = en-IN                # en-IN (12,34,567) | en-US (1,234,567)
```

### 12.2 — Config Class

```python
# app/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

def get_app_data_dir() -> Path:
    """Platform-aware app data directory."""
    import platform
    if platform.system() == "Windows":
        base = Path.home() / "AppData" / "Local" / "FinVault"
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "FinVault"
    else:
        base = Path.home() / ".finvault"
    base.mkdir(parents=True, exist_ok=True)
    return base

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(get_app_data_dir() / ".env"),
        extra="ignore"
    )

    # App
    APP_PORT: int = 8000
    APP_HOST: str = "127.0.0.1"
    AUTO_OPEN_BROWSER: bool = True
    LOG_LEVEL: str = "WARNING"

    # Database
    DATABASE_PATH: Path = get_app_data_dir() / "finvault.db"

    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite+aiosqlite:///{self.DATABASE_PATH}"

    # Security
    AUTO_LOCK_MINUTES: int = 15
    VAULT_KDF_ITERATIONS: int = 600_000

    # Backup
    AUTO_BACKUP: bool = True
    MAX_BACKUPS: int = 30

    # Storage
    STORAGE_DIR: Path = get_app_data_dir() / "storage"
    BACKUP_DIR: Path = get_app_data_dir() / "backups"
    LOG_DIR: Path = get_app_data_dir() / "logs"
```

### 12.3 — Database Connection (SQLite)

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import Settings

settings = Settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={
        "check_same_thread": False,          # Required for SQLite + async
    },
)

# Enable WAL mode and foreign keys on every connection
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.close()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
```
