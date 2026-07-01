#!/bin/bash

echo "[kasm-login] Starting Kasm login wrapper..."

# Start the Node.js API server in the background.
# It will retry CDP connection until Chrome starts.
cd /app && node kasm_login.mjs &
NODE_PID=$!

# Run the Kasm startup chain in a subshell.
# The scripts chain via `exec "$@"` internally — this replaces the subshell
# process, not our parent shell. So our Node.js background process survives.
# The chain: kasm_default_profile.sh → vnc_startup.sh → kasm_startup.sh --wait
(
  trap - SIGTERM SIGINT  # Don't inherit parent's signal traps
  exec /dockerstartup/kasm_default_profile.sh \
       /dockerstartup/vnc_startup.sh \
       /dockerstartup/kasm_startup.sh \
       "$@"
) &
KASM_PID=$!

# Wait for either process — if one dies, kill the other
wait $KASM_PID
EXIT_CODE=$?
kill $NODE_PID 2>/dev/null || true
exit $EXIT_CODE
