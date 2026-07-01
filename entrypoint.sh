#!/bin/bash
echo "[kasm-login] Starting Kasm login wrapper..."

# ── 1. Start nginx (HTTP/HTTPS demux on port 6901) ───────
nginx -t 2>&1 && nginx || echo "[WARN] nginx failed to start — HTTP redirect won't work"
echo "[kasm-login] nginx started (6901→TLS:6903, HTTP→redirect)"

# ── 2. Start Node.js login API ───────────────────────────
cd /app && node kasm_login.mjs &
NODE_PID=$!

cleanup() {
  echo "[kasm-login] Shutting down..."
  kill $NODE_PID 2>/dev/null || true
  nginx -s stop 2>/dev/null || true
  wait $NODE_PID 2>/dev/null || true
}
trap cleanup SIGTERM SIGINT

# ── 3. Start Kasm display + Chrome (in subshell so exec doesn't kill us) ──
(
  trap - SIGTERM SIGINT
  exec /dockerstartup/kasm_default_profile.sh \
       /dockerstartup/vnc_startup.sh \
       /dockerstartup/kasm_startup.sh \
       "$@"
) &
KASM_PID=$!

wait $KASM_PID
EXIT_CODE=$?
kill $NODE_PID 2>/dev/null || true
nginx -s stop 2>/dev/null || true
exit $EXIT_CODE
