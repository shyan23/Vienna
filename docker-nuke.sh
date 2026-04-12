#!/bin/bash

echo "🔴 Nuclear Docker Cleanup"
echo "========================="

# Stop all running containers
echo "Stopping all running containers..."
docker stop $(docker ps -q) 2>/dev/null || echo "No running containers to stop"

# Remove all containers (running and stopped)
echo "Removing all containers..."
docker rm -f $(docker ps -aq) 2>/dev/null || echo "No containers to remove"

# Remove all Docker images
echo "Removing all Docker images..."
docker rmi -f $(docker images -q) 2>/dev/null || echo "No images to remove"

# Remove all Docker volumes
echo "Removing all unused Docker volumes..."
docker volume prune -f

# Remove all unused networks
echo "Removing all unused Docker networks..."
docker network prune -f

# Remove all build cache
echo "Removing all build cache..."
docker builder prune -f

# System prune (removes everything not in use)
echo "Running system prune..."
docker system prune -af --volumes

echo "✅ Nuclear cleanup complete!"
echo ""
echo "Disk usage after cleanup:"
docker system df
