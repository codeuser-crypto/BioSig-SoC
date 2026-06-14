# Sections 6-7: Encryption (Unchanged) & Background Jobs (APScheduler)

## Section 6: Encryption Implementation

> **No changes.** The `crypto/vault.py` and `crypto/hashing.py` files from the original
> design are pure Python with zero infrastructure dependencies. They work identically
> whether the database is PostgreSQL or SQLite, cloud or local.

See: [05_encryption_and_jobs.md (Section 6 only)](./05_encryption_and_jobs.md)

The `derive_key()`, `encrypt_credential()`, `decrypt_credential()`, `generate_password()`,
`hash_password()`, and `verify_password()` functions are **unchanged**.

---

## Section 7: Background Jobs (APScheduler — replaces Celery)

### 7.1 — Scheduler Setup

```python
# app/scheduler/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


def setup_scheduler():
    """Register all background jobs. Called once at app startup."""

    # SIP due date reminders — daily at 8:00 AM IST
    scheduler.add_job(
        "app.scheduler.sip_jobs:check_sip_reminders",
        CronTrigger(hour=8, minute=0),
        id="sip_reminders",
        replace_existing=True,
    )

    # Cleanup old notifications — weekly Sunday 3:00 AM
    scheduler.add_job(
        "app.scheduler.cleanup_jobs:purge_old_notifications",
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="notification_cleanup",
        replace_existing=True,
    )

    # Auto-backup — daily at 2:00 AM
    scheduler.add_job(
        "app.scheduler.cleanup_jobs:auto_backup_database",
        CronTrigger(hour=2, minute=0),
        id="auto_backup",
        replace_existing=True,
    )

    scheduler.start()


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
```

### 7.2 — Integration with FastAPI

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.scheduler.scheduler import setup_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()

def create_app() -> FastAPI:
    app = FastAPI(title="FinVault", lifespan=lifespan)

    # Jinja2 template engine
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="app/templates")
    app.state.templates = templates

    # Serve static files (CSS, JS, images, vendor libs)
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Register page routers (server-rendered HTML)
    from app.api.v1 import router as v1_router
    app.include_router(v1_router, prefix="/api/v1")

    # Register page routes (HTML views)
    from app.pages import router as pages_router
    app.include_router(pages_router)

    return app

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    webbrowser.open("http://localhost:8000")
    uvicorn.run("app.main:create_app", factory=True, host="127.0.0.1", port=8000)
```

### 7.3 — Job Definitions

```python
# app/scheduler/sip_jobs.py
async def check_sip_reminders():
    """Daily: find SIPs due within user's reminder window, create notifications."""
    async with get_session() as db:
        prefs = await db.execute(select(UserPreferences))
        pref = prefs.scalar_one_or_none()
        if not pref or not pref.sip_reminders:
            return

        reminder_date = date.today() + timedelta(days=pref.sip_reminder_days)
        sips = await db.execute(
            select(SIPSchedule).where(
                SIPSchedule.status == "active",
                SIPSchedule.next_due_date <= reminder_date.isoformat()
            )
        )
        for sip in sips.scalars():
            await create_notification(db, sip.user_id, "sip_reminder",
                f"SIP due: {sip.asset.name}",
                f"₹{sip.amount/100:.2f} due on {sip.next_due_date}")


# app/scheduler/cleanup_jobs.py
import shutil
from pathlib import Path

async def purge_old_notifications():
    """Weekly: delete notifications older than 90 days."""
    async with get_session() as db:
        cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
        await db.execute(
            delete(Notification).where(Notification.created_at < cutoff)
        )
        await db.commit()

async def auto_backup_database():
    """Daily: copy the database file to backups directory."""
    from app.utils.paths import get_app_data_dir
    app_dir = get_app_data_dir()
    db_path = app_dir / "finvault.db"
    backup_dir = app_dir / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_path = backup_dir / f"finvault_{timestamp}.db"
    shutil.copy2(db_path, backup_path)

    # Keep only last 30 backups
    backups = sorted(backup_dir.glob("finvault_*.db"))
    for old in backups[:-30]:
        old.unlink()
```

---

## Section 8: Caching (In-Memory)

No Redis. Single-process in-memory cache:

```python
# app/utils/cache.py
from cachetools import TTLCache
from functools import wraps

# Shared cache instances
_caches = {
    "portfolio": TTLCache(maxsize=10, ttl=900),    # 15 min
    "expenses": TTLCache(maxsize=100, ttl=600),    # 10 min
    "health": TTLCache(maxsize=10, ttl=1800),      # 30 min
    "benchmarks": TTLCache(maxsize=50, ttl=86400), # 24 hours
}

def cached(cache_name: str, key_func=None):
    """Decorator for caching service method results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = _caches[cache_name]
            key = key_func(*args, **kwargs) if key_func else str(args) + str(kwargs)
            if key in cache:
                return cache[key]
            result = await func(*args, **kwargs)
            cache[key] = result
            return result
        return wrapper
    return decorator

def invalidate(cache_name: str):
    """Clear a cache after write operations."""
    _caches[cache_name].clear()
```
