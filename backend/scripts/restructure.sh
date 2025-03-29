#!/bin/bash

# Create necessary directories
mkdir -p app/docs/api
mkdir -p app/utils
mkdir -p app/services

# Move files to their new locations
mv app/core/base_service.py app/services/ 2>/dev/null || true
mv app/core/base_repository.py app/repositories/ 2>/dev/null || true
mv app/core/ai.py app/services/ai_service.py 2>/dev/null || true
mv app/core/analytics.py app/services/analytics_service.py 2>/dev/null || true
mv app/core/video.py app/utils/video_utils.py 2>/dev/null || true
mv app/core/storage.py app/utils/storage_utils.py 2>/dev/null || true
mv app/api/deps.py app/core/dependencies.py 2>/dev/null || true
mv app/api/v1/docs.py app/docs/api/ 2>/dev/null || true

# Remove redundant files
rm -f app/core/crud.py 2>/dev/null || true
rm -f app/core/redis.py 2>/dev/null || true
rm -rf app/backend 2>/dev/null || true

# Create __init__.py files
touch app/services/__init__.py
touch app/utils/__init__.py
touch app/docs/__init__.py
touch app/docs/api/__init__.py

echo "Restructuring completed successfully!" 