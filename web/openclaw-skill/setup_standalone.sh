#!/bin/bash
# ============================================================
# FriendMaker — Standalone VPS Setup (No Docker)
# Run as: sudo bash setup_standalone.sh
# ============================================================

set -e

echo "============================================"
echo " FriendMaker — Standalone VPS Installer"
echo "============================================"

OPENROUTER_KEY="${OPENROUTER_API_KEY:-}"
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
DOMAIN="${DOMAIN:-}"

# --- Detect OS ---
if [ -f /etc/debian_version ]; then
    PKG_MGR="apt-get"
elif [ -f /etc/redhat-release ]; then
    PKG_MGR="yum"
else
    echo "Unsupported OS. Use Ubuntu/Debian/CentOS."
    exit 1
fi

# --- System packages ---
echo "[1/9] Installing system packages..."
$PKG_MGR update -qq
$PKG_MGR install -y -qq curl git python3 python3-pip python3-venv ufw fail2ban

# --- Node.js 22 ---
echo "[2/9] Installing Node.js 22..."
curl -fsSL https://deb.nodesource.com/setup_22.x | bash - || true
$PKG_MGR install -y nodejs
node --version

# --- Python ---
echo "[3/9] Setting up Python..."
python3 --version
pip3 install --upgrade pip -q

# --- Clone repo ---
echo "[4/9] Cloning FriendMaker..."
if [ -d /opt/friendmaker ]; then
    echo "FriendMaker already exists at /opt/friendmaker — pulling latest..."
    cd /opt/friendmaker/web && git pull
else
    git clone https://github.com/SMSLYCLOUD/friend_maker.git /opt/friendmaker
    cd /opt/friendmaker/web
fi

# --- Python dependencies ---
echo "[5/9] Installing Python dependencies..."
cd /opt/friendmaker/web
pip3 install -r requirements.txt -q

# --- OpenClaw ---
echo "[6/9] Installing OpenClaw..."
npm install -g openclaw@latest
openclaw --version

# --- OpenRouter ---
if [ -n "$OPENROUTER_KEY" ]; then
    echo "[7/9] Configuring OpenRouter..."
    mkdir -p ~/.openclaw
    cat > ~/.openclaw/openclaw.json << 'OPENCLAW_CFG'
{
  "env": {
    "OPENROUTER_API_KEY": "__KEY__"
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "openrouter/google/gemini-2.5-flash-preview-05-20"
      }
    }
  }
}
OPENCLAW_CFG
    sed -i "s/__KEY__/$OPENROUTER_KEY/" ~/.openclaw/openclaw.json
    echo "OpenRouter configured."
else
    echo "[7/9] OpenRouter key not set. Run: openclaw onboard --auth-choice openrouter-api-key"
fi

# --- IG Agent Plugin ---
echo "[8/9] Installing IG Agent plugin..."
if [ -d /opt/friendmaker/web/openclaw-skill/dist ]; then
    openclaw plugins install /opt/friendmaker/web/openclaw-skill/dist
    openclaw gateway restart
else
    echo "Warning: plugin dist not found. Run: openclaw plugins install /opt/friendmaker/web/openclaw-skill/dist"
fi

# --- Systemd services ---
echo "[9/9] Setting up systemd services..."

cat > /etc/systemd/system/friendmaker-api.service << 'API_SERVICE'
[Unit]
Description=FriendMaker FastAPI Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/friendmaker/web
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
API_SERVICE

cat > /etc/systemd/system/friendmaker-gateway.service << 'GATEWAY_SERVICE'
[Unit]
Description=OpenClaw Gateway
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/openclaw gateway run
Restart=always
RestartSec=5
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
GATEWAY_SERVICE

systemctl daemon-reload
systemctl enable friendmaker-api
systemctl enable friendmaker-gateway
systemctl start friendmaker-api
systemctl start friendmaker-gateway

# --- Firewall ---
echo "Opening firewall ports..."
ufw allow 22/tcp comment "SSH"
ufw allow 8010/tcp comment "FriendMaker API"
ufw allow 18789/tcp comment "OpenClaw Control UI"
echo "y" | ufw --force enable 2>/dev/null || true

# --- Telegram channel ---
if [ -n "$BOT_TOKEN" ]; then
    echo "Setting up Telegram..."
    openclaw channels install telegram || true
    openclaw channels config telegram --token "$BOT_TOKEN"
    openclaw gateway restart
else
    echo ""
    echo "Telegram bot not configured. To set it up:"
    echo "  1. Message @BotFather on Telegram to get a bot token"
    echo "  2. openclaw channels install telegram"
    echo "  3. openclaw channels config telegram --token YOUR_TOKEN"
    echo "  4. systemctl restart friendmaker-gateway"
fi

echo ""
echo "============================================"
echo " Installation complete!"
echo "============================================"
echo ""
echo "Services:"
echo "  friendmaker-api     → http://localhost:8010 (FastAPI)"
echo "  friendmaker-gateway → http://localhost:18789 (OpenClaw)"
echo ""
echo "Commands:"
echo "  systemctl status friendmaker-api friendmaker-gateway"
echo "  journalctl -u friendmaker-api -f"
echo "  journalctl -u friendmaker-gateway -f"
echo "  openclaw logs -f"
echo ""
echo "Access:"
echo "  API:      http://<VPS_IP>:8010"
echo "  OpenClaw: http://<VPS_IP>:18789"
echo ""
echo "Telegram: Message your bot to verify it's working."
echo "============================================"