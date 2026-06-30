#!/bin/bash
set -e

echo "[kasm-login] Starting Kasm login wrapper..."

# Start the Node.js API server in the background.
# It will wait for Chrome's debug port to become available before connecting.
cd /app && node kasm_login.mjs &
NODE_PID=$!

# Trap signals to clean up both processes
cleanup() {
  echo "[kasm-login] Shutting down..."
  kill $NODE_PID 2>/dev/null || true
  wait $NODE_PID 2>/dev/null || true
}
trap cleanup SIGTERM SIGINT

# Exec into Kasm's real entrypoint chain.
# This sets up the display (Xorg), KasmVNC, window manager, and Chrome.
# The Node.js process continues running as a background child.
echo "[kasm-login] Handing off to Kasm entrypoint..."
exec /dockerstartup/kasm_default_profile.sh \
     /dockerstartup/vnc_startup.sh \
     /dockerstartup/kasm_startup.sh \
     "$@"
