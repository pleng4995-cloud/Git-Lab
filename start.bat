@echo off
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" goto no_venv

rem Already serving? Then just open the browser.
call :is_up
if not errorlevel 1 goto ready

echo Starting the BJT bias server...
start "BJT Bias Server" /min "%PY%" -m bjt_bias.app

rem Wait until the port really accepts connections (max 30 s).
set /a tries=0
:wait
call :is_up
if not errorlevel 1 goto ready
set /a tries+=1
if %tries% geq 30 goto timeout
rem ping works even when stdin is redirected (timeout does not)
ping -n 2 127.0.0.1 >nul
goto wait

:ready
echo Server is up: http://127.0.0.1:5000/
echo The server runs in the minimized "BJT Bias Server" window.
echo Close that window (or run stop.bat) to stop it.
if not defined START_NO_BROWSER explorer "http://127.0.0.1:5000/"
endlocal
exit /b 0

:timeout
echo.
echo [ERROR] The server did not open port 5000 within 30 seconds.
echo Run this to see the real error:
echo   "%PY%" -m bjt_bias.app
echo.
pause
endlocal
exit /b 1

:no_venv
echo.
echo [ERROR] .venv not found in this folder: %CD%
echo Create it first:
echo   python -m venv .venv
echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
pause
endlocal
exit /b 1

:is_up
netstat -ano | findstr /C:"LISTENING" | findstr /C:":5000 " >nul 2>&1
exit /b %errorlevel%
