#!/bin/bash
set -e

echo "[kasm-login] Starting Kasm login wrapper..."

# Start the Node.js API server in the background.
# It will retry CDP connection until Chrome starts.
cd /app && node kasm_login.mjs &
NODE_PID=$!

# Trap signals to clean up both processes
cleanup() {
  echo "[kasm-login] Shutting down..."
  kill $NODE_PID 2>/dev/null || true
  wait $NODE_PID 2>/dev/null || true
}
trap cleanup SIGTERM SIGINT

# Run the Kasm entrypoint scripts sequentially.
# kasm_default_profile.sh — sets up user profile
# vnc_startup.sh — starts KasmVNC + display server
# kasm_startup.sh — starts window manager + Chrome (keeps running)
echo "[kasm-login] Running Kasm profile setup..."
source /dockerstartup/kasm_default_profile.sh

echo "[kasm-login] Starting VNC display..."
source /dockerstartup/vnc_startup.sh

echo "[kasm-login] Starting Kasm desktop + Chrome..."
exec /dockerstartup/kasm_startup.sh "$@"
