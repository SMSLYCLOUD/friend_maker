#!/bin/bash
echo "=== VNC reachable from container? ==="
docker exec socialgrowthai-python-backend sh -c 'python3 -c "import requests; r = requests.get(\"http://host.docker.internal:6100/capture\", timeout=10); print(r.json())"'
echo ""
echo "=== Backend capture via API ==="
TOKEN=$(curl -s -X POST http://localhost:8010/api/login -H "Content-Type: application/json" -d '{"username":"test@test.com","password":"test123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('token','fail'))")
echo "Token OK: ${TOKEN:0:20}..."
ACCOUNTS=$(curl -s http://localhost:8010/api/accounts -H "Authorization: Bearer $TOKEN")
GMAIL_ID=$(echo "$ACCOUNTS" | python3 -c "import sys,json; accts=[a for a in json.load(sys.stdin) if a['platform']=='gmail']; print(accts[0]['id'] if accts else 'none')")
echo "Gmail account ID: $GMAIL_ID"
if [ "$GMAIL_ID" != "none" ]; then
  echo ""
  echo "=== Capture result ==="
  curl -s -X POST "http://localhost:8010/api/accounts/${GMAIL_ID}/capture-gmail-cookies" -H "Authorization: Bearer $TOKEN"
  echo ""
fi
