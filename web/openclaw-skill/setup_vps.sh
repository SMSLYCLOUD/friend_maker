#!/bin/bash
# ============================================================
# FriendMaker + OpenClaw Deployment on VPS
# Run this ON the VPS after initial server setup
# ============================================================

set -e

echo "=== FriendMaker + OpenClaw VPS Setup ==="

# 1. Install Node.js 22 LTS
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs
node --version

# 2. Install OpenClaw globally
npm install -g openclaw@latest

# 3. Run OpenClaw onboarding with OpenRouter
export OPENROUTER_API_KEY="$OPENROUTER_API_KEY"
openclaw onboard --auth-choice openrouter-api-key

# 4. Set OpenRouter as default model
openclaw models set openrouter/google/gemini-2.5-flash-preview-05-20

# 5. Install IG Agent plugin
npm install -g @friendmaker/openclaw-ig-agent
openclaw plugins install @friendmaker/openclaw-ig-agent
openclaw gateway restart

# 6. Install Telegram channel (optional but recommended for remote control)
openclaw channels install telegram
echo "After this, get a bot token from @BotFather on Telegram, then run:"
echo "openclaw channels config telegram --token YOUR_TOKEN"
echo "openclaw gateway restart"

# 7. Open firewall for Control UI
apt install -y ufw
ufw allow 18789/tcp comment "OpenClaw Control UI"
ufw allow 22/tcp
ufw --force enable

echo ""
echo "=== Setup complete ==="
echo "Control UI: http://YOUR_VPS_IP:18789"
echo "Or pair via mobile node for canvas + voice"
echo ""
echo "Then trigger campaigns via:"
echo "  - Telegram bot (recommended)"
echo "  - Web Control UI"
echo "  - API webhook to FastAPI backend"
