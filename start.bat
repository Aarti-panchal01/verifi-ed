@echo off
REM VerifiedProtocol — Quick Start Script (Windows)
REM ================================================

echo 🚀 Starting VerifiedProtocol...
echo.

REM Check if .env exists
if not exist .env (
    echo ❌ Error: .env file not found
    echo    Please copy .env.example to .env and configure it
    exit /b 1
)

REM Start backend
echo 📡 Starting backend API server...
start "VerifiedProtocol Backend" cmd /k "poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait for backend to start
timeout /t 5 /nobreak > nul

REM Check if backend is running
curl -s http://localhost:8000/health > nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Backend API running on http://localhost:8000
    echo    API docs: http://localhost:8000/docs
) else (
    echo ❌ Backend failed to start
    exit /b 1
)

REM Start frontend
echo.
echo 🎨 Starting frontend development server...
cd frontend
start "VerifiedProtocol Frontend" cmd /k "npm run dev"
cd ..

REM Wait for frontend to start
timeout /t 3 /nobreak > nul

echo.
echo ✅ VerifiedProtocol is running!
echo.
echo 📍 Endpoints:
echo    Backend API: http://localhost:8000
echo    API Docs:    http://localhost:8000/docs
echo    Frontend:    http://localhost:3000
echo.
echo Press any key to stop all services...
pause > nul

REM Stop services
taskkill /FI "WindowTitle eq VerifiedProtocol Backend*" /F > nul 2>&1
taskkill /FI "WindowTitle eq VerifiedProtocol Frontend*" /F > nul 2>&1

echo ✅ All services stopped
