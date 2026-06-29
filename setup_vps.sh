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
    sudo apt-get install -y docker-compose-plugin
    sudo usermod -aG docker $USER
    echo "✅ Docker installed."
else
    echo "✅ Docker is already installed."
fi

# 4. Create Project Structure
echo "📁 Preparing folder architecture..."
mkdir -p data/db scratch logs
chmod 755 data scratch logs
find data scratch logs -type f -exec chmod 644 {} + 2>/dev/null || true

# 5. Handle Environment Variables
echo "⚙️  Configuring environment for Remote IP: $PUBLIC_IP"
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Ensure .env is writable by container's non-root user (fixes Docker volume mount PermissionError)
chmod 666 .env 2>/dev/null || true

# Inject Public IP into .env (replace if exists, append if missing)
sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://$PUBLIC_IP:8010|" .env
grep -q "^NEXT_PUBLIC_API_URL=" .env || echo "NEXT_PUBLIC_API_URL=http://$PUBLIC_IP:8010" >> .env

sed -i "s|^FRONTEND_URL=.*|FRONTEND_URL=http://$PUBLIC_IP|" .env
grep -q "^FRONTEND_URL=" .env || echo "FRONTEND_URL=http://$PUBLIC_IP" >> .env

sed -i "s|^CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=http://$PUBLIC_IP,http://$PUBLIC_IP:3000,http://localhost:3000,http://localhost|" .env
grep -q "^CORS_ALLOWED_ORIGINS=" .env || echo "CORS_ALLOWED_ORIGINS=http://$PUBLIC_IP,http://$PUBLIC_IP:3000,http://localhost:3000,http://localhost" >> .env

# Inject HOST_IP (required by docker-compose.yml for skyvern-ui)
sed -i "s|^HOST_IP=.*|HOST_IP=$PUBLIC_IP|" .env
grep -q "^HOST_IP=" .env || echo "HOST_IP=$PUBLIC_IP" >> .env

# Ensure rate-limit and Skyvern env vars exist (in case .env.example is older)
grep -q "^SKYVERN_INTER_TASK_DELAY=" .env || echo "SKYVERN_INTER_TASK_DELAY=5" >> .env
grep -q "^SKYVERN_API_URL=" .env || echo "SKYVERN_API_URL=http://skyvern:8000" >> .env
grep -q "^SKYVERN_API_KEY=" .env || echo "SKYVERN_API_KEY=" >> .env

# Ensure DeepSeek is configured as primary LLM provider
grep -q "^SKYVERN_LLM_PROVIDERS=" .env || echo "SKYVERN_LLM_PROVIDERS=DeepSeek" >> .env
sed -i "s|^SKYVERN_LLM_PROVIDERS=.*|SKYVERN_LLM_PROVIDERS=DeepSeek|" .env
grep -q "^SKYVERN_LLM_DEEPSEEK_MODEL=" .env || echo "SKYVERN_LLM_DEEPSEEK_MODEL=deepseek-chat" >> .env
grep -q "^SKYVERN_LLM_DEEPSEEK_BASE_URL=" .env || echo "SKYVERN_LLM_DEEPSEEK_BASE_URL=https://api.deepseek.com/v1" >> .env
grep -q "^SKYVERN_LLM_DEEPSEEK_RPM_LIMIT=" .env || echo "SKYVERN_LLM_DEEPSEEK_RPM_LIMIT=2500" >> .env

echo "⚠️  Don't forget to set SKYVERN_LLM_DEEPSEEK_API_KEY in .env!"

# 6. Pull latest code (if in a git repo)
if [ -d .git ]; then
    echo "📥 Pulling latest code..."
    git pull origin main || echo "⚠️  git pull failed, continuing with local code"
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

# 8b. Auto-generate SKYVERN_API_KEY and write to .env
echo "🔑 Auto-generating Skyvern API key..."
chmod +x init_skyvern_key.sh
sudo bash init_skyvern_key.sh || echo "⚠️  init_skyvern_key.sh failed (you may need to set SKYVERN_API_KEY manually)"

# 8c. Restart python-backend so it picks up SKYVERN_API_KEY
echo "🔄 Restarting python-backend to pick up new API key..."
sudo docker compose restart python-backend

# 9. Wait for backend
echo "⏳ Waiting for backend..."
MAX_RETRIES=30
COUNT=0
while ! curl -s -o /dev/null http://localhost:8010/docs; do
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
echo "📍 Frontend:       http://$PUBLIC_IP"
echo "📍 Backend API:    http://$PUBLIC_IP:8010"
echo "📍 Skyvern UI:     http://$PUBLIC_IP:8080"
echo "📍 Skyvern VNC:    http://$PUBLIC_IP:6080"
echo "📍 VNC (manual):   http://$PUBLIC_IP:6082"
echo "-------------------------------------------------------"
echo "🔐 SECURITY: ensure ports 80, 6082, 8000, 8080, 8010 are open."
echo "👉 NEXT: nano .env  →  set SKYVERN_LLM_DEEPSEEK_API_KEY and SKYVERN_API_KEY"
echo "           then run:  sudo docker compose restart python-backend skyvern"
echo "-------------------------------------------------------"
