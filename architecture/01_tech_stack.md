# Section 1: Technology Stack Decisions

## Deployment Model: Standalone Localhost Application

FinVault runs **entirely on the user's machine**. No cloud, no public IP, no external
services. The user extracts a zip (or runs an installer), launches `finvault.exe`,
and opens `http://localhost:8000` in their browser.

```
User's Machine
├── finvault.exe  (or: python -m finvault)
│   ├── FastAPI → serves API on localhost:8000
│   ├── SQLite  → ~/.finvault/finvault.db
│   ├── APScheduler → in-process background jobs
│   └── Jinja2 templates → server-rendered HTML
└── Browser → http://localhost:8000
```

## Stack

| Layer | Technology | Version | Rationale |
|---|---|---|---|
| **Backend Framework** | FastAPI | 0.115+ | Async-native, auto OpenAPI docs, Pydantic validation. Lightweight enough to run as a single local process. |
| **ORM** | SQLAlchemy 2.0 | 2.0.36+ | Industry standard. Supports SQLite via `aiosqlite` with the same model code that would work with PostgreSQL if you ever scale to cloud. |
| **Primary Database** | SQLite 3 | 3.45+ (bundled with Python 3.12) | Zero-config, serverless, single-file database. Perfect for single-user standalone apps. WAL mode for concurrent reads. |
| **Database Encryption** | SQLCipher | 4.6+ (via `sqlcipher3`) | AES-256 full-database encryption. The entire `.db` file is encrypted at rest — even table names and schema are protected. Optional: can use standard SQLite + field-level encryption instead. |
| **Cache Layer** | `cachetools.TTLCache` | 5.5+ | In-memory cache with TTL eviction. No external Redis needed. Single-process, so in-memory cache is sufficient. |
| **Task Scheduler** | APScheduler | 3.10+ | In-process scheduler for background jobs (SIP reminders, cleanup). Replaces Celery+Redis — no broker infrastructure needed. |
| **File Storage** | Local filesystem (`pathlib`) | Built-in | Files stored in `~/.finvault/storage/`. No S3, no MinIO. Just the local disk. |
| **Search** | SQLite FTS5 | Built-in | Full-text search extension built into SQLite. Sufficient for searching assets, expenses, vault entries. |
| **Auth** | Simple session (in-memory) | — | No JWT needed. User logs in → password verified → session flag set in memory. Auto-lock after inactivity. No cookies, no refresh tokens. |
| **Password Hashing** | argon2-cffi | 23.1+ | Argon2id for user login password. Same as cloud version — security doesn't change for standalone. |
| **Vault Encryption** | cryptography (AES-256-CBC) | 43.0+ | Same AES-256 vault encryption. PBKDF2 key derivation from master password. Pure Python — no DB dependency. |
| **Export: PowerPoint** | python-pptx | 1.0+ | .pptx generation with matplotlib charts. Unchanged from cloud version. |
| **Export: CSV** | Python stdlib csv | 3.12 | UTF-8 with BOM for Excel. No dependency needed. |
| **Export: PDF** | WeasyPrint | 62+ | HTML/CSS to PDF. Works fully offline. |
| **Frontend (Templating)** | Jinja2 | 3.1+ | Server-side rendered HTML templates. Built into FastAPI. No Node.js, no npm, no build step. Pure Python. |
| **Frontend (Interactivity)** | HTMX | 2.0+ | Lightweight (14KB) library for AJAX, WebSocket, SSE — all via HTML attributes. No JavaScript framework needed. Loaded via CDN or bundled single file. |
| **Frontend (Client State)** | Alpine.js | 3.14+ | Minimal JS framework (15KB) for tabs, modals, dropdowns, form validation. Declared in HTML attributes. Used where HTMX alone isn't enough (e.g. vault password reveal toggle, chart interactions). |
| **Charts** | Chart.js | 4.4+ | Lightweight charting library (single JS file). Renders portfolio allocation pie charts, expense bar charts, P&L trend lines directly in the browser. Data passed from Jinja2 templates as JSON. |
| **CSS Framework** | PicoCSS or custom CSS | 2.0+ | Minimal classless CSS framework for clean, professional look. Or hand-crafted CSS with the FinVault design system (Sage Green, Inter font). No Tailwind, no build step. |
| **Packaging** | PyInstaller | 6.0+ | Bundles Python + dependencies + SQLite into a single `finvault.exe` (Windows) or equivalent. User extracts zip and runs. |
| **Testing** | pytest | 8.3+ | Same test framework. Tests run against in-memory SQLite. |
| **Linting** | Ruff + Black + mypy | latest | Unchanged. |
| **Env Management** | Pydantic Settings | 2.6+ | Loads from `~/.finvault/config.ini` or env vars. Defaults to sensible local values. |

## What's Gone (vs. Cloud Architecture)

| Removed | Why |
|---------|-----|
| PostgreSQL | Replaced by SQLite — no server to install |
| Redis | Replaced by in-memory TTLCache — single process |
| Celery + Celery Beat | Replaced by APScheduler — in-process, no broker |
| Nginx | No reverse proxy needed — direct localhost access |
| Gunicorn (multi-worker) | Single Uvicorn process — one user, one machine |
| Docker (for deployment) | Replaced by PyInstaller zip/exe — no containers |
| S3 / MinIO | Replaced by local filesystem — `~/.finvault/storage/` |
| SMTP / Email | Removed — no email reset flows. Password recovery via master password hint or local reset. |
| JWT tokens | Replaced by in-memory session — no cookie/token management |
| CORS / CSRF | Not needed — same-origin localhost |
| Rate Limiting | Not needed — local app, no abuse vector |
| Sentry / Prometheus / Grafana | Replaced by local log file — `~/.finvault/logs/` |
| Public DNS / SSL | Not needed — localhost only, no TLS required |

## Key Tradeoffs

1. **SQLite over PostgreSQL**: Lose concurrent writes, RLS, JSONB. Gain zero-config, single-file backup, zero infrastructure. For single-user finance app, SQLite is objectively better.
2. **APScheduler over Celery**: Lose distributed execution, gain zero infrastructure. All jobs run in the same Python process.
3. **In-memory session over JWT**: Lose stateless auth, gain simplicity. Session is just a Python variable — if the process restarts, user logs in again (acceptable for desktop use).
4. **PyInstaller over Docker**: Lose reproducible environments, gain "extract and run" simplicity for non-technical users.
5. **Jinja2 + HTMX over React SPA**: Lose rich client-side state management and component ecosystem. Gain zero Node.js dependency, zero build step, instant server-rendered pages, and a 100% Python codebase. HTMX + Alpine.js cover 95% of interactive UI needs (modals, tabs, live search, form submission without reload).
6. **No email flows**: Password reset is handled locally (security questions, master password hint, or direct DB reset via a CLI tool). No SMTP dependency.
