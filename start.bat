@echo off
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" goto no_venv

rem If something already serves port 5000, just open the browser.
netstat -ano | findstr /C:"LISTENING" | findstr /C:":5000 " >nul 2>&1
if not errorlevel 1 goto already_running

echo Starting Flask on http://127.0.0.1:5000/
echo Keep this window open. Press Ctrl+C to stop.
if not defined START_NO_BROWSER start "" /min cmd /c "timeout /t 3 /nobreak >nul & explorer http://127.0.0.1:5000/"
"%PY%" -m bjt_bias.app
goto end

:already_running
echo Port 5000 is already serving - opening the browser.
if not defined START_NO_BROWSER explorer "http://127.0.0.1:5000/"
goto end

:no_venv
echo [ERROR] .venv not found in this folder.
echo Create it first:
echo   python -m venv .venv
echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
pause
exit /b 1

:end
endlocal
