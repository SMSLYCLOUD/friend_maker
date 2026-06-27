#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting SocialGrowthAI VPS Deployment...${NC}"

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo"
  exit 1
fi

echo -e "${GREEN}[1/6] Updating system packages...${NC}"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

echo -e "${GREEN}[2/6] Installing prerequisites...${NC}"
DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl gnupg lsb-release nginx gettext-base jq

echo -e "${GREEN}[3/6] Installing Docker & Docker Compose...${NC}"
# Check if Docker is already installed
if ! command -v docker &> /dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
    echo "Docker is already installed, skipping."
fi

# Enable and start Docker service
systemctl enable docker
systemctl start docker

echo -e "${GREEN}[4/6] Auto-detecting IP and setting up environment variables...${NC}"
PUBLIC_IP=$(curl -s ifconfig.me)
if [ -z "$PUBLIC_IP" ]; then
    # Fallback to another service if ifconfig.me fails
    PUBLIC_IP=$(curl -s icanhazip.com)
fi

echo "Detected Public IP: $PUBLIC_IP"

# Navigate to the web directory where docker-compose lives
# Assuming the script is run from the root of the repo
cd "$(dirname "$0")/web" || exit 1

# Configure environment variables
cat > .env <<EOF
NEXT_PUBLIC_API_URL=http://$PUBLIC_IP
FRONTEND_URL=http://$PUBLIC_IP
CORS_ALLOWED_ORIGINS=http://$PUBLIC_IP,http://localhost:3000
DATABASE_URL=sqlite:///data/social_growth.db
REDIRECT_ROOT_TO_FRONTEND=true
OPENROUTER_API_KEY=YOUR_OPENROUTER_KEY_HERE
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
EOF

echo -e "${GREEN}[5/6] Starting application with Docker Compose...${NC}"
# We must force the Public IP into the build argument to prevent CORS/localhost errors
PUBLIC_IP=$(curl -s ifconfig.me)
# Clean up previous volumes so they inherit correct permissions from the container
docker compose down -v --remove-orphans || true
docker compose build --build-arg NEXT_PUBLIC_API_URL="http://$PUBLIC_IP"
docker compose up -d

echo -e "${YELLOW}Waiting for Backend to initialize (this may take 30s)...${NC}"
MAX_RETRIES=30
COUNT=0
while ! curl -s http://localhost:8010/ > /dev/null; do
    sleep 1
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo -e "${RED}❌ Backend failed to start. Checking logs...${NC}"
        docker compose logs python-backend
        exit 1
    fi
done
echo -e "${GREEN}✅ Backend is online!${NC}"

echo -e "${GREEN}[6/6] Configuring Nginx reverse proxy...${NC}"
NGINX_CONF_PATH="/etc/nginx/sites-available/socialgrowthai"
cat > $NGINX_CONF_PATH <<EOF
server {
    listen 80;
    server_name $PUBLIC_IP;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8010/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the site and restart nginx
ln -sf $NGINX_CONF_PATH /etc/nginx/sites-enabled/
# Remove default nginx site if it exists
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration and reload
nginx -t
systemctl reload nginx

echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "You can access your application at: ${YELLOW}http://$PUBLIC_IP${NC}"
