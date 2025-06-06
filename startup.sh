#!/bin/bash
# Startup script for RAGdoll containers

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 RAGdoll Startup Script${NC}"

# Set working directory
cd /app

# Create necessary directories
mkdir -p /app/app/indexes /app/backups /app/data

# Set Python path
export PYTHONPATH=/app

# Check if BGE model exists
if [ -d "/app/bge-m3_repo" ]; then
    echo -e "${GREEN}✅ BGE-M3 model repository found${NC}"
else
    echo -e "${YELLOW}⚠️  BGE-M3 model repository not found, will download${NC}"
fi

# Check Redis connection
echo -e "${BLUE}🔍 Checking Redis connection...${NC}"
until python -c "
import redis
import sys
try:
    r = redis.Redis(host='redis', port=6379, db=0)
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; do
    echo -e "${YELLOW}⏳ Waiting for Redis...${NC}"
    sleep 2
done

echo -e "${GREEN}✅ Startup checks complete${NC}"

# Execute the provided command
exec "$@"
