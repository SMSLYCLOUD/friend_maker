#!/bin/bash
set -e

# 1. Create opencode.json in project root to allow bash without approval
cat > /root/friend_maker/web/opencode.json << 'CONFIG'
{
  "permission": {
    "bash": { "*": "allow" }
  }
}
CONFIG

echo "[1/3] Config created at /root/friend_maker/web/opencode.json"

# 2. Restart gateway so config takes effect
openclaw gateway restart
sleep 3
echo "[2/3] Gateway restarted"

# 3. Install daily cron job
crontab -l 2>/dev/null | grep -v "run_campaign" | crontab -
(crontab -l 2>/dev/null; echo "0 9 * * * cd /root/friend_maker/web && node run_campaign.mjs >> /var/log/campaign_daily.log 2>&1") | crontab -
echo "[3/3] Cron job added — runs daily at 09:00"

echo ""
echo "=== Next, test with this Telegram command ==="
echo ""
echo "exec cd /root/friend_maker/web && node run_campaign.mjs"
echo ""
