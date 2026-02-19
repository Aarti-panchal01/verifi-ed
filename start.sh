#!/bin/bash
# VerifiedProtocol — Quick Start Script
# ======================================

echo "🚀 Starting VerifiedProtocol..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "   Please copy .env.example to .env and configure it"
    exit 1
fi

# Start backend
echo "📡 Starting backend API server..."
poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend API running on http://localhost:8000"
    echo "   API docs: http://localhost:8000/docs"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start frontend
echo ""
echo "🎨 Starting frontend development server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
sleep 3

echo ""
echo "✅ VerifiedProtocol is running!"
echo ""
echo "📍 Endpoints:"
echo "   Backend API: http://localhost:8000"
echo "   API Docs:    http://localhost:8000/docs"
echo "   Frontend:    http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '✅ All services stopped'; exit 0" INT

wait
