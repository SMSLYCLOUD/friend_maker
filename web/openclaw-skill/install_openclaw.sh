#!/bin/bash
# ============================================================
# FriendMaker + OpenClaw VPS Installation Script
# Run ON the VPS as root (sudo bash setup_openclaw.sh)
# ============================================================

set -e

OPENCLAW_VERSION="${OPENCLAW_VERSION:-latest}"
OPENROUTER_KEY="${OPENROUTER_API_KEY:-}"

echo "============================================"
echo " FriendMaker + OpenClaw Installer"
echo "============================================"

# --- Node.js 22 ---
echo "[1/8] Installing Node.js 22 LTS..."
curl -fsSL https://deb.nodesource.com/setup_22.x | bash - || true
apt-get install -y nodejs 2>/dev/null || true
node --version

# --- OpenClaw ---
echo "[2/8] Installing OpenClaw..."
npm install -g openclaw@"$OPENCLAW_VERSION"
openclaw --version

# --- OpenRouter config ---
echo "[3/8] Configuring OpenRouter..."
mkdir -p ~/.openclaw
cat > ~/.openclaw/openclaw.json << 'OPENCLAW_CONFIG'
{
  "env": {
    "OPENROUTER_API_KEY": "__YOUR_KEY_HERE__"
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "openrouter/google/gemini-2.5-flash-preview-05-20"
      }
    }
  }
}
OPENCLAW_CONFIG
echo "Edit ~/.openclaw/openclaw.json and replace __YOUR_KEY_HERE__ with your key."

# --- Onboard with OpenRouter ---
if [ -n "$OPENROUTER_KEY" ]; then
    echo "[4/8] Running OpenClaw onboarding with OpenRouter..."
    export OPENROUTER_API_KEY="$OPENROUTER_KEY"
    openclaw onboard --auth-choice openrouter-api-key --non-interactive 2>/dev/null || true
    sed -i "s/__YOUR_KEY_HERE__/$OPENROUTER_KEY/" ~/.openclaw/openclaw.json
else
    echo "[4/8] Skipping onboarding (OPENROUTER_API_KEY not set). Run manually:"
    echo "  openclaw onboard --auth-choice openrouter-api-key"
fi

# --- IG Agent plugin ---
echo "[5/8] Installing IG Agent plugin..."
cd /tmp
git clone https://github.com/SMSLYCLOUD/friend_maker.git friendmaker-repo 2>/dev/null || \
  git clone https://github.com/SMSLYCLOUD/friend_maker.git friendmaker-repo
cd friendmaker-repo/web/openclaw-skill
npm install
npm run build 2>/dev/null || true
npm pack
openclaw plugins install ./friendmaker-ig-agent-*.tgz 2>/dev/null || \
  openclaw plugins install /tmp/friendmaker-repo/web/openclaw-skill 2>/dev/null || true
echo "IG Agent plugin installed."

# --- Telegram channel (optional) ---
echo "[6/8] Telegram setup..."
read -p "Do you want to set up Telegram bot control? (y/n): " SETUP_TELEGRAM
if [ "$SETUP_TELEGRAM" = "y" ]; then
    openclaw channels install telegram || true
    echo "Get a bot token from @BotFather on Telegram, then run:"
    echo "  openclaw channels config telegram --token YOUR_TOKEN_HERE"
fi

# --- Restart ---
echo "[7/8] Restarting OpenClaw gateway..."
openclaw gateway restart || openclaw restart 2>/dev/null || true

# --- Firewall ---
echo "[8/8] Opening firewall for Control UI..."
apt-get install -y ufw 2>/dev/null || true
ufw allow 18789/tcp comment "OpenClaw Control UI" 2>/dev/null || true
ufw allow 22/tcp comment "SSH" 2>/dev/null || true
echo "y" | ufw --force enable 2>/dev/null || true

echo ""
echo "============================================"
echo " Installation complete!"
echo "============================================"
echo "Control UI:  http://<VPS_IP>:18789"
echo "Config:      ~/.openclaw/openclaw.json"
echo "Logs:        ~/.openclaw/logs/"
echo "Gateway:     openclaw gateway status"
echo ""
echo "To trigger campaigns from Telegram:"
echo "  1. Message @mybot on Telegram"
echo "  2. Say: Login to Instagram as @myusername"
echo "  3. Say: Run bombing campaign on @target1, @target2"
echo ""
echo "To use via API:"
echo "  POST /api/openclaw/execute"
echo "============================================"
