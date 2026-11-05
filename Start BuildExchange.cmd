@echo off
setlocal
cd /d "%~dp0buildexchange"
if not exist ".venv\Scripts\python.exe" (
  echo First-time setup: creating the local Python environment.
  python -m venv --without-pip .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -c "import django, rest_framework, PIL, psycopg" >nul 2>&1
if errorlevel 1 (
  python -m pip --python .venv\Scripts\python.exe install -r requirements.txt
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe manage.py migrate
if errorlevel 1 goto fail
.venv\Scripts\python.exe manage.py seed_demo
if errorlevel 1 goto fail
.venv\Scripts\python.exe manage.py seed_marketplace
if errorlevel 1 goto fail
echo Open http://127.0.0.1:8000 after the server starts. Press Ctrl+C to stop.
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
exit /b
:fail
echo Setup failed. See buildexchange README instructions and check your Python installation.
pause
exit /b 1
