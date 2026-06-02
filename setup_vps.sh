#!/bin/bash
# SocialGrowthAI - VPS Master Setup Script
# Version: 2.0.0 — adds Skyvern AI browser automation

set -e

echo "🚀 Starting SocialGrowthAI VPS Installation..."

# 1. Detect Public IP
PUBLIC_IP=$(curl -s https://ifconfig.me)
if [ -z "$PUBLIC_IP" ]; then
    echo "⚠️  Could not auto-detect Public IP. Please enter your VPS IP manually:"
    read -p "IP Address: " PUBLIC_IP
fi
echo "🌐 Using Public IP: $PUBLIC_IP"

# 2. Update System
echo "📦 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y curl git unzip jq

# 3. Install Docker
if ! command -v docker &> /dev/null
then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installed."
else
    echo "✅ Docker is already installed."
fi

# 4. Create Project Structure
echo "📁 Preparing folder architecture..."
mkdir -p data/db scratch logs
chmod -R 777 data scratch logs

# 5. Handle Environment Variables
echo "⚙️  Configuring environment for Remote IP: $PUBLIC_IP"
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Inject Public IP into .env
sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://$PUBLIC_IP:8010|" .env
sed -i "s|FRONTEND_URL=.*|FRONTEND_URL=http://$PUBLIC_IP:3000|" .env
sed -i "s|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=http://$PUBLIC_IP:3000,http://localhost:3000|" .env

# Ensure rate-limit and Skyvern env vars exist (in case .env.example is older)
grep -q "^SKYVERN_INTER_TASK_DELAY=" .env || echo "SKYVERN_INTER_TASK_DELAY=120" >> .env
grep -q "^SKYVERN_API_URL=" .env || echo "SKYVERN_API_URL=http://skyvern:8000" >> .env
grep -q "^OPENROUTER_MODEL=" .env || echo "OPENROUTER_MODEL=google/gemma-4-31b-it:free" >> .env
grep -q "^SKYVERN_API_KEY=" .env || echo "SKYVERN_API_KEY=" >> .env

# 6. Pull latest code (if in a git repo)
if [ -d .git ]; then
    echo "📥 Pulling latest code..."
    sudo git pull origin main || echo "⚠️  git pull failed, continuing with local code"
fi

# 7. Build and Launch
echo "🏗️  Building Social Media AI Factory (Skyvern + backend + frontend)..."
sudo docker compose build --build-arg NEXT_PUBLIC_API_URL="http://$PUBLIC_IP:8010"
sudo docker compose up -d

# 8. Wait for Skyvern to be ready
echo "⏳ Waiting for Skyvern to be healthy (this can take 2-3 minutes)..."
MAX_RETRIES=60
COUNT=0
while ! curl -s http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; do
    sleep 5
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Skyvern failed to start. Last 30 log lines:"
        sudo docker compose logs skyvern --tail 30
        break
    fi
done
SKYVERN_HEALTH=$(curl -s http://localhost:8000/api/v1/heartbeat 2>/dev/null || echo "down")
echo "Skyvern heartbeat: $SKYVERN_HEALTH"

# 9. Wait for backend
echo "⏳ Waiting for backend..."
MAX_RETRIES=30
COUNT=0
while ! curl -s http://localhost:8010/ > /dev/null 2>&1; do
    sleep 1
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Backend failed to start. Logs:"
        sudo docker compose logs python-backend --tail 30
        break
    fi
done
echo "✅ Backend is online!"

# 10. Run DB migrations
echo "🗄️  Running database migrations..."
sudo docker compose exec -T python-backend python -c "from app.database.connection import init_db; init_db(); print('Migrations OK')" || echo "⚠️  migrations failed"

# 11. Verify schema
echo "🔍 Verifying Target schema..."
sudo docker compose exec -T python-backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/social_growth.db')
cols = [r[1] for r in c.execute('PRAGMA table_info(targets)').fetchall()]
print('targets columns:', cols)
needed = ['comment_id', 'source_post_url']
missing = [n for n in needed if n not in cols]
if missing:
    print('⚠️  Missing columns:', missing)
else:
    print('✅ Schema OK')
" 2>/dev/null || echo "⚠️  schema check failed"

echo "-------------------------------------------------------"
echo "🎉 INSTALLATION COMPLETE!"
echo "-------------------------------------------------------"
echo "📍 Frontend:       http://$PUBLIC_IP:3000"
echo "📍 Backend API:    http://$PUBLIC_IP:8010"
echo "📍 Skyvern UI:     http://$PUBLIC_IP:8080"
echo "📍 Skyvern VNC:    http://$PUBLIC_IP:6080"
echo "📍 VNC (manual):   http://$PUBLIC_IP:6082"
echo "-------------------------------------------------------"
echo "🔐 SECURITY: ensure ports 3000, 6082, 8000, 8080, 8010 are open."
echo "👉 NEXT: nano .env  →  set OPENROUTER_API_KEY and SKYVERN_API_KEY"
echo "           then run:  sudo docker compose restart python-backend skyvern"
echo "-------------------------------------------------------"
