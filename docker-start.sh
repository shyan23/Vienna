#!/bin/bash

echo "🚀 Starting Docker Compose"
echo "=========================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Using .env.example as template."
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Build and start containers
echo "Building and starting containers..."
docker compose up --build -d

echo ""
echo "✅ Docker Compose started successfully!"
echo ""
echo "Running containers:"
docker compose ps
echo ""
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:8080"
echo ""
echo "To view logs, run: docker compose logs -f"
