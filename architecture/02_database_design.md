# Section 2: Complete Database Design (SQLite)

## 2.1 — Design Notes for SQLite

Key differences from PostgreSQL:
- **No UUID type** — UUIDs stored as `TEXT` (36 chars), generated in Python via `uuid.uuid4()`
- **No NUMERIC precision** — Currency stored as `INTEGER` (paise). ₹1,234.56 → `123456`. Converted in service layer.
- **No TIMESTAMPTZ** — Timestamps stored as `TEXT` in ISO 8601 format (`2025-06-10T12:30:00Z`)
- **No GENERATED COLUMNS** — P&L computed in Python service layer
- **No INET type** — IP addresses stored as `TEXT`
- **No JSONB** — JSON stored as `TEXT`, parsed in Python
- **No RLS** — Single user, not needed
- **No extensions** — No uuid-ossp, no pgcrypto. All handled in Python.
- **WAL mode enabled** — Allows concurrent reads while writing

## 2.2 — Complete Schema (SQLite DDL)

```sql
-- ============================================================
-- FinVault Database Schema — SQLite 3
-- Applied via Alembic migrations or initial setup script
-- ============================================================

PRAGMA journal_mode=WAL;           -- Write-Ahead Logging for concurrency
PRAGMA foreign_keys=ON;            -- Enforce FK constraints (off by default in SQLite)
PRAGMA busy_timeout=5000;          -- Wait 5s on lock instead of failing immediately
PRAGMA cache_size=-64000;          -- 64MB cache

-- ============================================================
-- AUTH & USERS
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,                                -- UUID as text
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,                         -- Argon2id hash
    phone TEXT,
    date_of_birth TEXT,                                  -- ISO date: 2025-06-10
    age INTEGER,                                         -- For age-based allocation advice
    currency TEXT NOT NULL DEFAULT 'INR',                -- ISO 4217
    avatar_path TEXT,                                    -- Local file path
    master_password_hash TEXT,                           -- Argon2id hash for vault verification
    master_password_salt TEXT,                           -- Hex-encoded 32-byte salt
    -- 3 fixed security questions for local password recovery
    security_question_1 TEXT,                            -- e.g. "What is your mother's maiden name?"
    security_answer_1_hash TEXT,                         -- Argon2id hash
    security_question_2 TEXT,                            -- e.g. "What was the name of your first pet?"
    security_answer_2_hash TEXT,                         -- Argon2id hash
    security_question_3 TEXT,                            -- e.g. "What city were you born in?"
    security_answer_3_hash TEXT,                         -- Argon2id hash
    risk_profile TEXT DEFAULT 'moderate',                -- conservative|moderate|aggressive (computed from age)
    is_setup_complete INTEGER NOT NULL DEFAULT 0,        -- 0=false, 1=true
    is_active INTEGER NOT NULL DEFAULT 1,
    last_login_at TEXT,                                  -- ISO timestamp
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ----

CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash TEXT NOT NULL,                    -- SHA-256 of session token
    ip_address TEXT,
    expires_at TEXT NOT NULL,
    is_revoked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token_hash);

-- ----

CREATE TABLE IF NOT EXISTS user_preferences (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    dark_mode INTEGER NOT NULL DEFAULT 0,
    date_format TEXT NOT NULL DEFAULT 'DD/MM/YYYY',
    number_format TEXT NOT NULL DEFAULT 'en-IN',
    sip_reminders INTEGER NOT NULL DEFAULT 1,
    sip_reminder_days INTEGER NOT NULL DEFAULT 3,
    portfolio_alert_freq TEXT NOT NULL DEFAULT 'weekly',
    benchmark_alerts INTEGER NOT NULL DEFAULT 1,
    vault_inactivity_reminder INTEGER NOT NULL DEFAULT 0,
    auto_lock_minutes INTEGER NOT NULL DEFAULT 15,       -- Auto-lock app after inactivity
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- ASSETS
-- ============================================================

CREATE TABLE IF NOT EXISTS asset_types (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    icon TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

-- Seed data (inserted by setup script)
INSERT OR IGNORE INTO asset_types (id, name, slug, icon, sort_order) VALUES
    ('at_mf', 'Mutual Fund', 'mutual-fund', 'trending_up', 1),
    ('at_eq', 'Equity', 'equity', 'bar_chart', 2),
    ('at_sgb', 'Sovereign Gold Bond', 'sgb', 'workspace_premium', 3),
    ('at_re', 'Real Estate', 'real-estate', 'home', 4),
    ('at_dg', 'Digital Gold', 'digital-gold', 'toll', 5),
    ('at_pg', 'Physical Gold', 'physical-gold', 'diamond', 6),
    ('at_fd', 'Fixed Deposit', 'fixed-deposit', 'account_balance', 7),
    ('at_ppf', 'PPF', 'ppf', 'savings', 8);

-- ----

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    asset_type_id TEXT NOT NULL REFERENCES asset_types(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    serial_number TEXT,
    isin TEXT,                                           -- ISIN code (e.g. INF179K01CC4)
    ticker TEXT,                                         -- BSE/NSE ticker (e.g. HDFCMIDCAP)
    quantity REAL NOT NULL DEFAULT 0,                     -- Units/shares/grams
    price_per_unit INTEGER NOT NULL DEFAULT 0,            -- NAV or price at purchase (PAISE)
    invested_amount INTEGER NOT NULL DEFAULT 0,          -- Stored in PAISE (₹1234.56 = 123456)
    current_value INTEGER NOT NULL DEFAULT 0,            -- Stored in PAISE
    current_nav INTEGER,                                 -- Latest NAV/price per unit (PAISE)
    -- P&L computed in service layer: current_value - invested_amount
    -- current_value can be auto-computed: quantity × current_nav
    investment_date TEXT,                                 -- Date of initial investment (ISO date)
    purchase_date TEXT,                                   -- Alias for backward compat
    is_sip INTEGER NOT NULL DEFAULT 0,                   -- 1 if this asset has active SIP
    sip_monthly_amount INTEGER DEFAULT 0,                -- Monthly SIP amount (PAISE)
    notes TEXT,
    is_guaranteed INTEGER NOT NULL DEFAULT 0,
    guaranteed_return_pct REAL,                           -- 8.5 = 8.5%
    maturity_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_assets_user ON assets(user_id);
CREATE INDEX IF NOT EXISTS idx_assets_user_type ON assets(user_id, asset_type_id);

-- ----

CREATE TABLE IF NOT EXISTS asset_images (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,                             -- Relative to ~/.finvault/storage/
    file_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_asset_images_asset ON asset_images(asset_id);

-- ----

CREATE TABLE IF NOT EXISTS sip_schedules (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,                             -- PAISE
    frequency TEXT NOT NULL DEFAULT 'monthly',            -- monthly|quarterly
    start_date TEXT NOT NULL,
    end_date TEXT,
    next_due_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',                -- active|paused|completed
    auto_update_value INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sip_user ON sip_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_sip_next_due ON sip_schedules(next_due_date);

-- ----

CREATE TABLE IF NOT EXISTS asset_price_history (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    value INTEGER NOT NULL,                              -- PAISE (total value)
    nav INTEGER,                                         -- NAV per unit (PAISE)
    recorded_date TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',                -- manual|sip|api
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(asset_id, recorded_date)
);

CREATE INDEX IF NOT EXISTS idx_price_history ON asset_price_history(asset_id, recorded_date);

-- ============================================================
-- FINANCIAL GOALS
-- ============================================================

CREATE TABLE IF NOT EXISTS financial_goals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,                                  -- e.g. "Retirement", "Child Education", "Europe Trip"
    goal_type TEXT NOT NULL DEFAULT 'custom',             -- retirement|education|emergency|travel|home|wedding|custom
    target_amount INTEGER NOT NULL,                       -- PAISE
    current_amount INTEGER NOT NULL DEFAULT 0,            -- PAISE (auto-computed from linked assets)
    target_date TEXT,                                     -- ISO date
    priority TEXT NOT NULL DEFAULT 'medium',              -- high|medium|low
    icon TEXT,
    color_hex TEXT DEFAULT '#4A7C6F',
    notes TEXT,
    is_completed INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_goals_user ON financial_goals(user_id);

-- ----

CREATE TABLE IF NOT EXISTS goal_asset_links (
    id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL REFERENCES financial_goals(id) ON DELETE CASCADE,
    asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    allocation_pct REAL NOT NULL DEFAULT 100.0,           -- % of asset allocated to this goal
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(goal_id, asset_id)
);

CREATE INDEX IF NOT EXISTS idx_goal_assets ON goal_asset_links(goal_id);
CREATE INDEX IF NOT EXISTS idx_asset_goals ON goal_asset_links(asset_id);

-- ============================================================
-- INCOME (for income vs expense comparison)
-- ============================================================

CREATE TABLE IF NOT EXISTS income (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source TEXT NOT NULL,                                 -- Salary|Freelance|Business|Rental|Interest|Dividend|Other
    amount INTEGER NOT NULL,                              -- PAISE
    income_date TEXT NOT NULL,                            -- ISO date
    is_recurring INTEGER NOT NULL DEFAULT 0,
    frequency TEXT DEFAULT 'monthly',                     -- monthly|quarterly|yearly|one-time
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_income_user_date ON income(user_id, income_date);

-- ============================================================
-- EXPENSES
-- ============================================================

CREATE TABLE IF NOT EXISTS expense_categories (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    color_hex TEXT NOT NULL DEFAULT '#4A7C6F',
    icon TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    budget_amount INTEGER DEFAULT 0,                     -- Monthly budget target (PAISE) for insights
    is_active INTEGER NOT NULL DEFAULT 1,
    is_system INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO expense_categories (id, name, slug, color_hex, icon, sort_order, is_system) VALUES
    ('ec_food', 'Food & Dining', 'food-dining', '#D4956A', 'restaurant', 1, 1),
    ('ec_transport', 'Transportation', 'transportation', '#4A7C6F', 'directions_car', 2, 1),
    ('ec_housing', 'Housing & Utilities', 'housing-utilities', '#52A77E', 'home', 3, 1),
    ('ec_health', 'Healthcare', 'healthcare', '#E05C5C', 'favorite', 4, 1),
    ('ec_edu', 'Education', 'education', '#2D3142', 'school', 5, 1),
    ('ec_entertain', 'Entertainment & Leisure', 'entertainment', '#F0B429', 'movie', 6, 1),
    ('ec_shop', 'Shopping & Clothing', 'shopping-clothing', '#7FB5A8', 'shopping_bag', 7, 1),
    ('ec_save', 'Savings & Investments', 'savings-investments', '#6B7280', 'savings', 8, 1);

-- ----

CREATE TABLE IF NOT EXISTS household_members (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    relationship TEXT NOT NULL DEFAULT 'Self',            -- Self|Spouse|Parent|Child|Sibling|Other
    avatar_initial TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_household_user ON household_members(user_id);

-- ----

CREATE TABLE IF NOT EXISTS expenses (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id TEXT NOT NULL REFERENCES expense_categories(id) ON DELETE RESTRICT,
    spent_by_id TEXT NOT NULL REFERENCES household_members(id) ON DELETE RESTRICT,
    spent_for_id TEXT REFERENCES household_members(id) ON DELETE SET NULL,
    expense_date TEXT NOT NULL,                           -- ISO date
    amount INTEGER NOT NULL,                              -- PAISE
    description TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, expense_date);
CREATE INDEX IF NOT EXISTS idx_expenses_user_cat ON expenses(user_id, category_id);
CREATE INDEX IF NOT EXISTS idx_expenses_spent_by ON expenses(spent_by_id);

-- ============================================================
-- VAULT
-- ============================================================

CREATE TABLE IF NOT EXISTS vault_credential_categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO vault_credential_categories (id, name, slug, sort_order) VALUES
    ('vc_social', 'Social', 'social', 1),
    ('vc_finance', 'Finance', 'finance', 2),
    ('vc_work', 'Work', 'work', 3),
    ('vc_shop', 'Shopping', 'shopping', 4),
    ('vc_other', 'Other', 'other', 5);

-- ----

CREATE TABLE IF NOT EXISTS vault_credentials (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id TEXT REFERENCES vault_credential_categories(id) ON DELETE SET NULL,
    service_name_enc TEXT NOT NULL,                       -- AES-256-CBC encrypted
    url_enc TEXT,                                         -- AES-256-CBC encrypted
    username_enc TEXT NOT NULL,                           -- AES-256-CBC encrypted
    password_enc TEXT NOT NULL,                           -- AES-256-CBC encrypted
    notes_enc TEXT,                                       -- AES-256-CBC encrypted
    favicon_url TEXT,                                     -- Not encrypted
    password_strength INTEGER DEFAULT 0,                  -- 0-100 score computed on save
    has_2fa INTEGER NOT NULL DEFAULT 0,                   -- Track if 2FA is enabled
    is_compromised INTEGER NOT NULL DEFAULT 0,            -- Flag weak/reused passwords
    last_password_changed TEXT DEFAULT (datetime('now')),
    password_age_days INTEGER DEFAULT 0,                  -- Computed: days since last change
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_vault_user ON vault_credentials(user_id);

-- ----

CREATE TABLE IF NOT EXISTS vault_audit_log (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,                                 -- unlock|lock|view|copy|create|update|delete|export
    credential_id TEXT REFERENCES vault_credentials(id) ON DELETE SET NULL,
    ip_address TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_vault_audit_user ON vault_audit_log(user_id, created_at);

-- ============================================================
-- REPORTS & NOTIFICATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS report_exports (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    format TEXT NOT NULL DEFAULT 'pdf',                   -- pdf|csv|json (PDF replaces PPT)
    status TEXT NOT NULL DEFAULT 'completed',             -- No async queue, generated synchronously
    file_path TEXT,                                       -- Relative to ~/.finvault/exports/
    included_sections TEXT NOT NULL DEFAULT '[]',         -- JSON array as text
    date_from TEXT,
    date_to TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reports_user ON report_exports(user_id);

-- ----

CREATE TABLE IF NOT EXISTS benchmark_data (
    id TEXT PRIMARY KEY,
    benchmark_name TEXT NOT NULL,                         -- Nifty50|Sensex|GoldRate|FDRate
    recorded_date TEXT NOT NULL,
    value REAL NOT NULL,
    return_pct REAL,
    period TEXT NOT NULL,                                 -- 1M|3M|6M|1Y
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(benchmark_name, recorded_date, period)
);

CREATE INDEX IF NOT EXISTS idx_benchmark ON benchmark_data(benchmark_name, recorded_date);

-- ----

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,                                   -- sip_reminder|portfolio_alert|vault_reminder|export_ready|system
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    icon TEXT,
    action_url TEXT,
    is_read INTEGER NOT NULL DEFAULT 0,
    read_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_notif_user_unread ON notifications(user_id, is_read, created_at);

-- ============================================================
-- SYSTEM
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,                             -- auth.login|data.export|data.delete|settings.change
    entity_type TEXT,
    entity_id TEXT,
    metadata TEXT DEFAULT '{}',                           -- JSON as text
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id, created_at);

-- ============================================================
-- EXPENSE INSIGHTS (pre-computed monthly summaries for trend analysis)
-- ============================================================

CREATE TABLE IF NOT EXISTS monthly_summaries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    total_income INTEGER NOT NULL DEFAULT 0,              -- PAISE
    total_expenses INTEGER NOT NULL DEFAULT 0,            -- PAISE
    total_invested INTEGER NOT NULL DEFAULT 0,            -- PAISE
    savings_rate REAL DEFAULT 0,                          -- (income - expenses) / income × 100
    category_breakdown TEXT DEFAULT '{}',                 -- JSON: { "ec_food": 25000, ... }
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, year, month)
);

CREATE INDEX IF NOT EXISTS idx_monthly_user ON monthly_summaries(user_id, year, month);

-- ============================================================
-- FTS5 VIRTUAL TABLES (Full-Text Search)
-- ============================================================

CREATE VIRTUAL TABLE IF NOT EXISTS assets_fts USING fts5(
    name, serial_number, isin, ticker, notes,
    content='assets', content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS expenses_fts USING fts5(
    description, notes,
    content='expenses', content_rowid='rowid'
);
```

## 2.3 — Currency Storage: Paise Convention

All monetary amounts are stored as **integers in paise** (1/100 of a rupee):

```python
# Service layer conversion
def rupees_to_paise(amount: float) -> int:
    """₹1,234.56 → 123456"""
    return round(amount * 100)

def paise_to_rupees(paise: int) -> float:
    """123456 → ₹1,234.56"""
    return paise / 100

# API response always returns rupees as float
# Database always stores paise as integer
# This avoids ALL floating point precision issues with SQLite's REAL type
```

## 2.4 — Migration Strategy

- **Tool**: Alembic 1.14+ with `aiosqlite` dialect
- **Naming**: `YYYY_MM_DD_HHMM_description.py`
- **Initial setup**: `alembic upgrade head` creates all tables + seeds lookup data
- **Backup before migrate**: Automatic copy of `.db` file before any migration runs
- **Rollback**: `alembic downgrade -1` (every migration has downgrade)

## 2.5 — Backup Strategy

```
# Backup is just copying one file:
cp ~/.finvault/finvault.db ~/.finvault/backups/finvault_2025-06-10.db

# The app provides a "Backup" button in Settings that does this automatically
# Also provides "Restore from backup" that replaces the DB file
```
