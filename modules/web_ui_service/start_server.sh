#!/usr/bin/env bash
set -euo pipefail
python3 -m venv venv || true
source venv/bin/activate
pip install -r modules/web_ui_service/requirements.txt
export DJANGO_SETTINGS_MODULE=remote_ui.settings
python modules/web_ui_service/manage.py migrate --settings=remote_ui.settings
python modules/web_ui_service/manage.py runserver --settings=remote_ui.settings 0.0.0.0:8000 