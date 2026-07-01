#!/bin/bash
echo "[kasm-login] Starting Kasm login wrapper..."

# ── 1. Start nginx (HTTP/HTTPS demux on port 6901) ───────
if nginx -t 2>&1; then
  nginx
  echo "[kasm-login] nginx started — port 6901 demuxes TLS→6903 / HTTP→redirect"
else
  echo "[WARN] nginx config test failed — skipping (direct HTTPS only)"
fi

# ── 2. Start Node.js login API ───────────────────────────
cd /app && node kasm_login.mjs &
NODE_PID=$!

# ── 3. Auto-login: disable VNC password after Kasm sets it up ──
(
  for i in $(seq 1 60); do
    sleep 1
    # Clear VNC password files so browser connects without prompting
    for f in /home/kasm-user/.vnc/passwd /home/kasm-user/.vnc/.vnc_pass; do
      if [ -f "$f" ]; then
        > "$f" 2>/dev/null || true
        echo "[auto-login] Cleared $f"
      fi
    done
  done
) &
CLEANER_PID=$!

cleanup() {
  echo "[kasm-login] Shutting down..."
  [ -n "$NODE_PID" ] && kill "$NODE_PID" 2>/dev/null || true
  [ -n "$CLEANER_PID" ] && kill "$CLEANER_PID" 2>/dev/null || true
  nginx -s stop 2>/dev/null || true
  wait "$NODE_PID" 2>/dev/null || true
}
trap cleanup SIGTERM SIGINT

# ── 4. Start Kasm display + Chrome ───────────────────────
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
cleanup
exit $EXIT_CODE
