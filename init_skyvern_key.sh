#!/bin/bash
# init_skyvern_key.sh — Auto-generate SKYVERN_API_KEY and write to .env
#
# Uses Skyvern's /api/v1/internal/auth/repair endpoint (self-hosted only)
# which generates a new API key, invalidates old ones, and updates .env
# inside the Skyvern container automatically. We then read it back and
# mirror it into the host's .env so the python-backend can use it.
#
# Idempotent: if .env already has a valid SKYVERN_API_KEY, does nothing.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
SKYVERN_API_URL="${SKYVERN_API_URL:-http://localhost:8000}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[init-skyvern]${NC} $*"; }
warn() { echo -e "${YELLOW}[init-skyvern]${NC} $*"; }
err()  { echo -e "${RED}[init-skyvern]${NC} $*" >&2; }

# 1. Ensure .env exists
if [ ! -f "$ENV_FILE" ]; then
    warn ".env not found, creating from .env.example"
    cp "${SCRIPT_DIR}/.env.example" "$ENV_FILE"
fi

# 2. If SKYVERN_API_KEY is already set and non-empty, verify it works
existing=$(grep -E "^SKYVERN_API_KEY=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")
if [ -n "$existing" ] && [ "$existing" != "YOUR_API_KEY" ] && [ "$existing" != "PLACEHOLDER" ]; then
    if curl -s -f -H "x-api-key: $existing" "$SKYVERN_API_URL/api/v1/internal/auth/status" > /dev/null 2>&1; then
        log "SKYVERN_API_KEY already valid, skipping"
        exit 0
    else
        warn "Existing SKYVERN_API_KEY is invalid, regenerating..."
    fi
fi

# 3. Wait for Skyvern to be ready (up to 3 minutes)
log "Waiting for Skyvern at $SKYVERN_API_URL ..."
MAX=36
for i in $(seq 1 $MAX); do
    if curl -s -f "$SKYVERN_API_URL/api/v1/heartbeat" > /dev/null 2>&1; then
        log "Skyvern is healthy"
        break
    fi
    if [ "$i" -eq "$MAX" ]; then
        err "Skyvern did not become healthy in 3 minutes"
        err "Check: sudo docker compose logs skyvern"
        exit 1
    fi
    sleep 5
done

# 4. Hit the repair endpoint to generate a fresh key
log "Calling /api/v1/internal/auth/repair ..."
response=$(curl -s -X POST "$SKYVERN_API_URL/api/v1/internal/auth/repair" \
    -H "Content-Type: application/json" \
    -d '{}' 2>&1)

if [ $? -ne 0 ]; then
    err "Repair request failed: $response"
    exit 1
fi

# 5. Extract the api_key (works whether response is JSON, has nested objects, etc.)
new_key=$(echo "$response" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('api_key',''))" 2>/dev/null)

if [ -z "$new_key" ]; then
    err "Could not extract api_key from response:"
    echo "$response" | head -5
    exit 1
fi

log "Got new API key (fingerprint: $(echo "$response" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('fingerprint','?'))" 2>/dev/null))"

# 6. Write to host .env
if grep -qE "^SKYVERN_API_KEY=" "$ENV_FILE"; then
    sed -i "s|^SKYVERN_API_KEY=.*|SKYVERN_API_KEY=$new_key|" "$ENV_FILE"
else
    echo "SKYVERN_API_KEY=$new_key" >> "$ENV_FILE"
fi

log "Wrote SKYVERN_API_KEY to $ENV_FILE"

# 7. Verify
if curl -s -f -H "x-api-key: $new_key" "$SKYVERN_API_URL/api/v1/internal/auth/status" > /dev/null 2>&1; then
    log "✅ Verified: new key works"
else
    err "New key verification failed"
    exit 1
fi

log "All done. Restart python-backend so it picks up the new key:"
log "  sudo docker compose restart python-backend"
