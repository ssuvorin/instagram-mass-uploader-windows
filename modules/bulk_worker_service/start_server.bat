@echo off
setlocal
if not exist venv (
  py -3.12 -m venv venv
)
call venv\Scripts\activate
pip install -r modules\bulk_worker_service\requirements.txt
set PYTHONPATH=%CD%
uvicorn bulk_worker_service.app:app --host 0.0.0.0 --port 8088 --workers 1
endlocal 