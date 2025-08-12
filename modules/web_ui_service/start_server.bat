@echo off
setlocal
if not exist venv (
  py -3.12 -m venv venv
)
call venv\Scripts\activate
pip install -r modules\web_ui_service\requirements.txt
set DJANGO_SETTINGS_MODULE=remote_ui.settings
python modules\web_ui_service\manage.py migrate --settings=remote_ui.settings
python modules\web_ui_service\manage.py runserver --settings=remote_ui.settings 0.0.0.0:8000
endlocal 