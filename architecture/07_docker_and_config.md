# Section 7: Development Setup (Pure Python — No Node.js)

## Dev Environment Setup

```bash
# 1. Clone repo
git clone https://github.com/your-org/finvault.git
cd finvault

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements/base.txt -r requirements/dev.txt

# 4. Run app (hot reload)
python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000

# 5. Run tests
pytest tests/ -v --asyncio-mode=auto
```

**No npm, no Node.js, no frontend build step.** Jinja2 templates are served directly
by FastAPI. HTMX, Alpine.js, and Chart.js are single `.js` files in `app/static/vendor/`.
Edit a template → refresh browser → see changes instantly.

## Makefile

```makefile
.PHONY: dev test build clean lint

dev:
	python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000

test:
	pytest tests/ -v --asyncio-mode=auto --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/
	black --check app/ tests/
	mypy app/ --ignore-missing-imports

build:
	python scripts/build.py

clean:
	rm -rf build/ dist/ *.spec
```
