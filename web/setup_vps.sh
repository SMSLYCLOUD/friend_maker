#!/bin/bash

# SocialGrowthAI - VPS Master Setup Script (Remote Access Enabled)
# Version: 1.1.0

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
sudo apt-get install -y curl git unzip

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
mkdir -p data/android data/db scratch logs
chmod -R 777 data scratch logs

# 5. Handle Environment Variables & IP Binding
echo "⚙️  Configuring environment for Remote IP: $PUBLIC_IP"
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Inject the Public IP into the .env file for the build
sed -i "s|localhost|$PUBLIC_IP|g" .env
sed -i "s|127.0.0.1|$PUBLIC_IP|g" .env

# 6. Build and Launch
echo "🏗️  Building Social Media AI Factory (Baking in IP)..."
# Pass the IP as a build argument to the frontend
NEXT_PUBLIC_API_URL="http://$PUBLIC_IP:8010" sudo -E docker compose build
sudo docker compose up -d

echo "-------------------------------------------------------"
echo "🎉 INSTALLATION COMPLETE!"
echo "-------------------------------------------------------"
echo "📍 Dashboard:    http://$PUBLIC_IP:3000"
echo "📍 API Backend: http://$PUBLIC_IP:8010"
echo "📱 Android VNC:  http://$PUBLIC_IP:6080"
echo "-------------------------------------------------------"
echo "🔐 SECURITY NOTE: Ensure ports 3000, 8010, and 6080 are open on your VPS firewall."
echo "👉 Next Step: Run 'nano .env' to add your real OpenRouter API Key."
echo "-------------------------------------------------------"
