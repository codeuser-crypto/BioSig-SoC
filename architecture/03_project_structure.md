# Section 3: Project Structure (Standalone)

```
finvault/
├── app/
│   ├── __init__.py
│   ├── main.py                             # FastAPI app factory + Uvicorn launcher + system tray
│   ├── config.py                           # Pydantic Settings, loads from ~/.finvault/config.ini
│   ├── database.py                         # SQLite engine via aiosqlite, session factory, WAL mode
│   ├── dependencies.py                     # FastAPI deps: get_db, get_current_user, get_scheduler
│   │
│   ├── models/                             # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py                         # DeclarativeBase, UUID generation, timestamp mixin
│   │   ├── user.py                         # User, UserSession, UserPreferences
│   │   ├── asset.py                        # Asset, AssetType, AssetImage, SIPSchedule, PriceHistory
│   │   ├── expense.py                      # Expense, ExpenseCategory, HouseholdMember
│   │   ├── vault.py                        # VaultCredential, VaultCredentialCategory, VaultAuditLog
│   │   ├── notification.py                 # Notification
│   │   └── report.py                       # ReportExport, BenchmarkData
│   │
│   ├── schemas/                            # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth.py                         # LoginRequest, SetupWizardRequest
│   │   ├── user.py                         # UserProfile, PreferencesUpdate
│   │   ├── asset.py                        # AssetCreate/Update/Response, BulkUploadResponse
│   │   ├── expense.py                      # ExpenseCreate/Response, CalendarView, CategorySummary
│   │   ├── vault.py                        # CredentialCreate/Response, VaultExport
│   │   ├── report.py                       # PortfolioSummary, FinancialHealth
│   │   ├── notification.py                 # NotificationResponse
│   │   └── common.py                       # PaginatedResponse, ErrorResponse, CurrencyField
│   │
│   ├── repositories/                       # Database access layer
│   │   ├── __init__.py
│   │   ├── base.py                         # BaseRepository CRUD helpers
│   │   ├── user_repo.py
│   │   ├── asset_repo.py
│   │   ├── expense_repo.py
│   │   ├── vault_repo.py
│   │   ├── notification_repo.py
│   │   └── report_repo.py
│   │
│   ├── services/                           # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py                 # Login, password verify, session management
│   │   ├── user_service.py                 # Profile CRUD, setup wizard
│   │   ├── asset_service.py                # Asset CRUD, P&L computation, bulk upload
│   │   ├── expense_service.py              # Expense CRUD, calendar aggregation, category totals
│   │   ├── vault_service.py                # Encrypt/decrypt, vault lock/unlock
│   │   ├── report_service.py               # Portfolio summary, health score, benchmark
│   │   ├── export_service.py               # PowerPoint, CSV, PDF generation (synchronous)
│   │   ├── notification_service.py         # Create, read, mark read
│   │   ├── backup_service.py               # DB file copy/restore, data export/import
│   │   └── file_storage_service.py         # Local filesystem read/write/delete
│   │
│   ├── api/                                # FastAPI routers
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                     # POST /login, /logout, /change-password
│   │   │   ├── users.py                    # GET/PUT /me, /me/preferences, /setup-wizard
│   │   │   ├── assets.py                   # CRUD /assets, image upload, bulk upload
│   │   │   ├── sip.py                      # CRUD /sip-schedules
│   │   │   ├── expenses.py                 # CRUD /expenses, /calendar, /categories
│   │   │   ├── household.py                # CRUD /household-members
│   │   │   ├── vault.py                    # /unlock, /lock, CRUD /credentials, /generate-password
│   │   │   ├── reports.py                  # Portfolio, health, benchmark, export
│   │   │   ├── notifications.py            # List, mark read
│   │   │   └── settings.py                 # Backup, restore, clear data, reset app
│   │   └── health.py                       # GET /health
│   │
│   ├── crypto/                             # Security (UNCHANGED from cloud version)
│   │   ├── __init__.py
│   │   ├── vault.py                        # AES-256-CBC encrypt/decrypt, PBKDF2 key derivation
│   │   ├── hashing.py                      # Argon2id password hashing
│   │   └── session.py                      # Simple in-memory session manager + auto-lock timer
│   │
│   ├── scheduler/                          # APScheduler background jobs (replaces Celery)
│   │   ├── __init__.py
│   │   ├── scheduler.py                    # APScheduler setup, job registration
│   │   ├── sip_jobs.py                     # SIP reminder notifications
│   │   ├── cleanup_jobs.py                 # Old notification purge, session cleanup
│   │   └── benchmark_jobs.py               # Market data fetch (optional, when online)
│   │
│   ├── templates/                          # Jinja2 HTML templates (server-rendered)
│   │   ├── base.html                       # Master layout: nav, sidebar, HTMX/Alpine.js/Chart.js imports
│   │   ├── auth/
│   │   │   ├── login.html                  # Login page
│   │   │   ├── register.html               # First-time setup
│   │   │   └── forgot_password.html        # Security question reset
│   │   ├── setup/
│   │   │   └── wizard.html                 # 3-step onboarding wizard
│   │   ├── dashboard/
│   │   │   └── index.html                  # Main dashboard with KPI cards, charts
│   │   ├── assets/
│   │   │   ├── list.html                   # Asset table with tab filters
│   │   │   ├── detail.html                 # Single asset view with images, SIP
│   │   │   └── partials/                   # HTMX partial fragments
│   │   │       ├── _asset_row.html         # Single row for hx-swap
│   │   │       ├── _asset_form.html        # Add/Edit modal content
│   │   │       └── _bulk_upload.html       # Bulk upload modal
│   │   ├── expenses/
│   │   │   ├── list.html                   # Expense list with calendar
│   │   │   └── partials/
│   │   │       ├── _expense_row.html
│   │   │       ├── _expense_form.html
│   │   │       ├── _calendar.html          # Calendar day-total grid
│   │   │       └── _category_summary.html  # Category breakdown chart
│   │   ├── vault/
│   │   │   ├── locked.html                 # Master password entry
│   │   │   ├── unlocked.html               # Credential list
│   │   │   └── partials/
│   │   │       ├── _credential_row.html
│   │   │       ├── _credential_form.html
│   │   │       └── _password_generator.html
│   │   ├── reports/
│   │   │   ├── dashboard.html              # Portfolio summary, health score, benchmark
│   │   │   └── partials/
│   │   │       └── _chart_container.html
│   │   ├── settings/
│   │   │   ├── index.html                  # Tabbed settings page
│   │   │   └── partials/
│   │   │       ├── _profile.html
│   │   │       ├── _security.html
│   │   │       ├── _notifications.html
│   │   │       ├── _categories.html
│   │   │       └── _data_backup.html
│   │   ├── notifications/
│   │   │   └── partials/
│   │   │       └── _notification_list.html # HTMX-swappable notification dropdown
│   │   └── components/                     # Reusable Jinja2 macros
│   │       ├── _modal.html                 # Generic modal macro
│   │       ├── _table.html                 # Sortable table macro
│   │       ├── _pagination.html            # Page navigation macro
│   │       ├── _toast.html                 # Toast notification macro
│   │       ├── _sidebar.html               # App sidebar navigation
│   │       └── _kpi_card.html              # Dashboard KPI card macro
│   │
│   ├── static/                             # Static files (CSS, JS, images)
│   │   ├── css/
│   │   │   ├── main.css                    # App styles (Sage Green design system)
│   │   │   └── components.css              # Component-specific styles
│   │   ├── js/
│   │   │   ├── app.js                      # Global helpers (toast, confirm dialogs)
│   │   │   ├── charts.js                   # Chart.js initialization helpers
│   │   │   └── vault.js                    # Vault-specific: copy to clipboard, password reveal
│   │   ├── vendor/                         # Third-party JS (no npm, just files)
│   │   │   ├── htmx.min.js                # HTMX 2.0 (~14KB gzipped)
│   │   │   ├── alpine.min.js              # Alpine.js 3.14 (~15KB gzipped)
│   │   │   └── chart.min.js               # Chart.js 4.4 (~60KB gzipped)
│   │   ├── fonts/
│   │   │   └── inter/                      # Inter font files (self-hosted, offline)
│   │   └── img/
│   │       ├── logo.svg                    # FinVault logo
│   │       └── favicon.ico
│   │
│   └── utils/
│       ├── __init__.py
│       ├── pagination.py                   # Offset pagination helper
│       ├── response.py                     # API response envelope
│       ├── currency.py                     # Paise ↔ rupees conversion helpers
│       ├── validators.py                   # Custom Pydantic validators
│       ├── date_utils.py                   # IST timezone, Indian date formatting
│       ├── csv_parser.py                   # Bulk upload CSV parsing
│       └── paths.py                        # App data directory resolution (~/.finvault/)
│
├── tests/
│   ├── conftest.py                         # In-memory SQLite fixtures, test client
│   ├── factories.py                        # factory_boy factories
│   ├── unit/
│   │   ├── test_crypto_vault.py
│   │   ├── test_crypto_hashing.py
│   │   ├── test_currency.py
│   │   └── test_validators.py
│   ├── integration/
│   │   ├── test_auth.py
│   │   ├── test_assets.py
│   │   ├── test_expenses.py
│   │   ├── test_vault.py
│   │   └── test_reports.py
│   └── e2e/
│       └── test_onboarding_flow.py
│
├── scripts/
│   ├── build.py                            # PyInstaller build script
│   ├── seed_db.py                          # Seed lookup tables
│   └── reset_password.py                   # CLI tool: reset user password locally
│
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
│
├── .github/
│   └── workflows/
│       ├── ci.yml                          # Lint + Test
│       └── release.yml                     # Build exe/zip, create GitHub Release
│
├── finvault.spec                           # PyInstaller spec file
├── pyproject.toml
├── requirements/
│   ├── base.txt
│   └── dev.txt
├── README.md
└── Makefile                                # make dev, make test, make build
```

## Runtime Data Directory

When FinVault runs, it creates/uses this structure on the user's machine:

```
~/.finvault/                                # %APPDATA%\finvault on Windows
├── finvault.db                             # SQLite database (all user data)
├── config.ini                              # User-editable config (port, auto-lock time)
├── storage/
│   ├── avatars/                            # User avatar images
│   ├── asset-images/{asset_id}/            # Scanned documents
│   └── exports/                            # Generated .pptx, .csv, .pdf files
├── backups/
│   └── finvault_2025-06-10_143000.db       # Manual/auto backup copies
└── logs/
    └── finvault.log                        # Application log (rotated, 10MB max)
```
