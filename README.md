# 见景寻诗 API

FastAPI backend for image understanding and verified classical Chinese poetry matching.

## Stack

- Python 3.12
- FastAPI + Pydantic 2
- SQLAlchemy 2 + Alembic
- PostgreSQL
- Redis
- Docker Compose

## Local setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Start infrastructure:

```powershell
docker compose up -d postgres redis
```

Run migrations and API:

```powershell
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

If Docker Desktop is temporarily unavailable, run the local UI-test service:

```powershell
.\.venv\Scripts\python.exe scripts\run_local_demo.py
```

This mode still calls the configured vision providers, but loads the reviewed
50-poem seed directly and keeps the fingerprint quota in process memory. It is
for local manual testing only; restarting it resets the quota.

Tests:

```powershell
pytest
```

Build, validate and idempotently import the initial poetry corpus:

```powershell
python scripts/build_tang_seed.py
python scripts/validate_seed.py
python scripts/import_poems.py
```

The corpus contains all 366 records from
[`chinese-poetry/chinese-poetry`](https://github.com/chinese-poetry/chinese-poetry)
at the fixed commit recorded in `data/seeds/source-manifest.json` (MIT license).
The source text is converted from Traditional to Simplified Chinese with OpenCC, then a small
set of known historical variants is normalized to the current widely used standard display text.
The original 50 image-friendly poems retain their manually curated tags; the other 316 records
use rule-generated tags with `reviewed=false` so they can be distinguished during later review.

Endpoints:

- `GET /healthz`: process liveness
- `GET /readyz`: PostgreSQL and Redis readiness
- `POST /api/v1/poetry/match`: upload one JPG/PNG/WebP image and run image understanding plus verified poetry matching
- `POST /api/v1/poems/match`: match normalized image understanding to one verified poem
- `GET /api/v1/poems/{poem_slug}`: read one verified poem
- `GET /docs`: OpenAPI UI

The unified image endpoint accepts `multipart/form-data` with an `image` field and
requires `X-Device-Fingerprint`. Redis stores only an HMAC-SHA256 digest of that
fingerprint and enforces the configured 100-request daily quota in the Hong Kong
timezone. Vision provider keys are server-only environment variables.
