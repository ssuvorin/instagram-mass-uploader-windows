# Modules: Web UI Service and Bulk Worker Service

This document explains how to deploy and operate the distributed setup: one UI server (Django) with Postgres and N worker servers (FastAPI) that execute tasks and report statuses back to the UI.

## Overview

- Web UI Service (`modules/web_ui_service`)
  - Django service exposing the dashboard screens from the main project and a thin API layer ("dashboard") for workers: aggregates fetch, status updates, counters.
  - Stores all data in Postgres.
- Bulk Worker Service (`modules/bulk_worker_service`)
  - FastAPI microservice that runs tasks in pull-mode.
  - Fetches aggregates from the UI API, downloads media, executes actions (Playwright + Dolphin or instagrapi), updates statuses/logs on the UI.

Scaling: run 1 UI server and N workers. The UI can dispatch starts to a worker pool; each worker further batches and parallelizes within itself.

## Requirements

- Python 3.12 for both UI and Worker
- Postgres for UI database
- On workers: Playwright and optional Dolphin Anty Remote API

## Deploy: Web UI Service

Directory: `modules/web_ui_service`

Install dependencies and run migrations:
```bash
cd modules/web_ui_service
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Environment (.env):
```bash
# Core
SECRET_KEY=change-me
DEBUG=false
ALLOWED_HOSTS=ui.example.com
DATABASE_URL=postgres://user:pass@dbhost:5432/ig_uploader

# Authentication for worker calls → UI
WORKER_API_TOKEN=super-secret-token

# Worker endpoints: either single worker or a pool
WORKER_BASE_URL=https://worker-1.example.com
# Or a pool (comma-separated):
# WORKER_POOL=https://worker-1.example.com,https://worker-2.example.com

# Dispatch settings (UI → workers)
DISPATCH_BATCH_SIZE=5
DISPATCH_CONCURRENCY=2
```

Run server (example):
```bash
gunicorn remote_ui.wsgi:application --bind 0.0.0.0:8000
```

Notes:
- `remote_ui/urls.py` maps both the main uploader URLs and the thin dashboard API at root (`/`). Set reverse proxy accordingly.

## Deploy: Bulk Worker Service

Directory: `modules/bulk_worker_service`

Install dependencies and Playwright:
```bash
cd modules/bulk_worker_service
pip install -r requirements.txt
python -m playwright install
```

Environment (.env):
```bash
# UI base URL for worker to call. Because dashboard APIs are mounted at '/', use UI root.
UI_API_BASE=https://ui.example.com
# Must match WORKER_API_TOKEN set on the UI side
UI_API_TOKEN=super-secret-token

# Upload method for Bulk Upload: playwright | instagrapi
UPLOAD_METHOD=playwright

# Concurrency and batching
CONCURRENCY_LIMIT=2
BATCH_SIZE=2
HEADLESS=1
VISIBLE_BROWSER=0

# HTTP/SSL behavior
REQUEST_TIMEOUT_SECS=60
VERIFY_SSL=1

# Temporary directory for media
MEDIA_TEMP_DIR=/tmp/ig_media

# Dolphin Anty (optional, for Playwright + Remote API cookies persistence)
DOLPHIN_API_TOKEN=your_dolphin_token
DOLPHIN_API_HOST=http://127.0.0.1:3001
```

Run server (example):
```bash
uvicorn bulk_worker_service.app:app --host 0.0.0.0 --port 9000
```

## Task Coverage

Worker supports the following tasks in pull-mode:

- Bulk Upload (full)
  - Playwright flow: login via `Auth`, upload via `Upload`, human-like delays, Dolphin profile support
  - Instagrapi flow: stable mobile device/session, per-account uniquification, logs
  - Select upload method via `UPLOAD_METHOD` env or per-run `options.upload_method` in start request
- Warmup (instagrapi): timeline scrolls, likes, stories, optional follows
- Avatar (instagrapi): change profile picture
- Bio (instagrapi): set external URL
- Follow (instagrapi): follow random targets between min/max
- Proxy diagnostics (placeholder): marks OK; extend with real checks
- Media uniq: unique video files (no publishing)

## UI API (consumed by Worker)

Base: `UI_API_BASE` (e.g., `https://ui.example.com`)

- Aggregates (GET):
  - `/api/bulk-tasks/{task_id}/aggregate`
  - `/api/bulk_login/{task_id}/aggregate`
  - `/api/warmup/{task_id}/aggregate`
  - `/api/avatar/{task_id}/aggregate`
  - `/api/bio/{task_id}/aggregate`
  - `/api/follow/{task_id}/aggregate`
  - `/api/proxy_diag/{task_id}/aggregate`
  - `/api/media_uniq/{task_id}/aggregate`
- Download media:
  - `/api/media/{video_id}/download`
- Status/logs (Bulk Upload specific):
  - `POST /api/bulk-tasks/{task_id}/status` body: `{status?, log?, log_append?}`
  - `POST /api/bulk-accounts/{account_task_id}/status` body: `{status?, log_append?}`
  - `POST /api/bulk-accounts/{account_task_id}/counters` body: `{success?, failed?}`
- Generic status/logs (other kinds):
  - `POST /api/{kind}/{task_id}/status` body: `{status?, log?, log_append?}`
  - `POST /api/{kind}/accounts/{account_task_id}/status` body: `{status?, log_append?}`
  - `POST /api/{kind}/accounts/{account_task_id}/counters` body: numeric fields (e.g., `success`, `failed`, `likes`, `follows`, `viewed`) will be added to model fields if present

Kinds supported: `bulk_login|warmup|avatar|bio|follow|proxy_diag|media_uniq`.

Authentication: Worker must send `Authorization: Bearer {UI_API_TOKEN}` for all requests.

## Worker API (called by UI)

Base: worker host (e.g., `https://worker-1.example.com`)

- Health:
  - `GET /api/v1/health` → `{ "ok": true }`
- Jobs:
  - `GET /api/v1/jobs`
  - `GET /api/v1/jobs/{job_id}/status`
- Start tasks:
  - Bulk Upload: `POST /api/v1/bulk-tasks/start`
    - JSON body:
```json
{
  "mode": "pull",
  "task_id": 123,
  "options": {
    "concurrency": 2,
    "headless": true,
    "visible": false,
    "batch_index": 0,
    "batch_count": 1,
    "upload_method": "instagrapi"
  }
}
```
    - Response: `{ "job_id": "uuid", "accepted": true }`
  - Other pull tasks (query param `task_id`):
    - `POST /api/v1/bulk-login/start?task_id=...`
    - `POST /api/v1/warmup/start?task_id=...`
    - `POST /api/v1/avatar/start?task_id=...`
    - `POST /api/v1/bio/start?task_id=...`
    - `POST /api/v1/follow/start?task_id=...`
    - `POST /api/v1/proxy-diagnostics/start?task_id=...`
    - `POST /api/v1/media-uniq/start?task_id=...`

Authentication: UI must send `Authorization: Bearer {WORKER_API_TOKEN}` (set in UI env and forwarded in `dashboard/views.py`).

## Choosing Upload Method (Bulk Upload)

- Default method on the worker via `UPLOAD_METHOD=playwright|instagrapi`.
- Per-run override via `options.upload_method` in the Bulk Upload start request.
- No UI change required — if not provided, ENV is used.

## Cookies / Sessions

- Playwright (Dolphin): worker attempts to fetch cookies from Dolphin Remote API after runs and logs the count. Persisting cookies to DB is handled in the main project.
- Instagrapi: uses persistent mobile device/session, saved through `InstagramDevice.session_settings` if Django models are reachable (already integrated in shared `instgrapi_func`).

## Concurrency and Human-like Behavior

- Worker-level parallelism via `CONCURRENCY_LIMIT`, local batching via `BATCH_SIZE`.
- Instagrapi runner sets small randomized delays, and Playwright pipeline emulates human actions.
- `UiClient` has tenacity-based retries for API robustness.

## Scaling Pattern

- Add more workers; list them in UI `WORKER_POOL`.
- UI distributes start calls across the pool with `batch_index/batch_count` metadata; each worker filters accounts by index and batches locally.
- Horizontal scale is achieved by simply adding workers; all report back to the single UI.

## Extension Hooks

- Proxy diagnostics: replace the placeholder in `runners/proxy_diag_runner.py` with your real checker and specific counters.
- Avatar images: if images require download from UI, add an image download endpoint similar to `/api/media/{id}/download` and update `avatar_runner.py` accordingly.

## Troubleshooting

- 401/403 from UI: ensure worker is sending `Authorization: Bearer UI_API_TOKEN` and UI is configured with `WORKER_API_TOKEN`.
- Aggregates 404: verify that the task exists in UI and the path prefix matches `UI_API_BASE`.
- Instagrapi login challenges: ensure TOTP/email credentials are populated for accounts; email IMAP must be reachable for `AutoIMAPEmailProvider`.
- Playwright errors: install browsers on the worker host and provide Dolphin API tokens if used.

## File Map (Key)

- UI: `modules/web_ui_service/dashboard/api_views.py` (API), `dashboard/views.py` (start dispatch), `dashboard/urls.py` (routes)
- Worker: `bulk_worker_service/orchestrator.py` (dispatch), `.../ig_runner.py` (Playwright), `.../instagrapi_runner.py` (instagrapi bulk upload), `.../runners/*.py` (other tasks), `.../ui_client.py` (UI API)

---
This modules README documents the distributed architecture, deployment, configuration, endpoints, and scaling strategy for running the Web UI on one server and multiple Workers on other servers, with full feature parity to the original Django project’s functionality. 