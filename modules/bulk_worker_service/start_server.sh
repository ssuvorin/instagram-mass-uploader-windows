#!/usr/bin/env bash
set -euo pipefail
python3 -m venv venv || true
source venv/bin/activate
pip install -r modules/bulk_worker_service/requirements.txt
export PYTHONPATH="$(pwd)"
uvicorn bulk_worker_service.app:app --host 0.0.0.0 --port 8088 --workers 1 