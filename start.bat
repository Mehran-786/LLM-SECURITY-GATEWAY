@echo off
title Secure AI Gateway
color 0A

echo.
echo  ==========================================
echo    SECURE AI GATEWAY - Starting Server...
echo  ==========================================
echo.

:: Activate virtual environment
echo [1/2] Activating virtual environment...
call "%~dp0venv\Scripts\activate.bat"

echo [2/2] Starting Uvicorn server on port 8001...
echo.
echo  Gateway running at: http://127.0.0.1:8001
echo  Press CTRL+C to stop the server.
echo  ==========================================
echo.

:: Start the server
uvicorn app.main:app --reload --port 8001

:: If server stops, pause so window stays open
echo.
echo  Server stopped. Press any key to close.
pause > nul
