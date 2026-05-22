#!/bin/bash
set -e

# Ensure data and uploads directories exist
mkdir -p /app/web/data
mkdir -p /app/web/uploads
mkdir -p /app/web/cookies
mkdir -p /app/web/scratch

echo "Starting VNC Social Service..."
cd /app/web
# Run VNC in the background
node vnc_social.mjs &

echo "Starting FastAPI Backend..."
cd /app/web
# Use the DATABASE_URL environment variable or default to local sqlite
export DATABASE_URL=${DATABASE_URL:-sqlite:///data/social_growth.db}
export CORS_ALLOWED_ORIGINS="*"
export REDIRECT_ROOT_TO_FRONTEND="false"
uvicorn app.main:app --host 127.0.0.1 --port 8010 &

echo "Starting Next.js Frontend..."
cd /app/web/frontend
# Start Next.js on port 3000
npm start &

echo "Starting Unified Proxy..."
cd /app
# The proxy listens on $PORT (or 8000) and routes traffic
node proxy.js
