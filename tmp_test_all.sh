#!/bin/bash
echo "=== Kasm login service ==="
curl -s http://localhost:6100/status | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Platform: {d.get(\"platform\")}, Running: {d.get(\"running\")}, Login detected: {d.get(\"loginDetected\")}')"
echo ""
echo "=== Create test accounts + Kasm login for each platform ==="
TOKEN=$(curl -s -X POST http://localhost:8010/api/login -H "Content-Type: application/json" -d '{"username":"test@test.com","password":"test123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('token','fail'))")
for platform in gmail instagram twitter facebook linkedin tiktok; do
  echo ""
  echo "--- $platform ---"
  CREATE=$(curl -s -X POST http://localhost:8010/api/accounts -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "{\"platform\":\"$platform\",\"username\":\"test_${platform}@test.com\",\"password\":\"test123\"}")
  AID=$(echo "$CREATE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','fail'))")
  echo "Created $platform -> $AID"
  KASM=$(curl -s -X POST "http://localhost:8010/api/accounts/${AID}/kasm-login" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Kasm URL: {d.get(\"kasm_url\")}, Platform: {d.get(\"platform\")}')")
  echo "$KASM"
  STATUS=$(curl -s "http://localhost:8010/api/accounts/${AID}/kasm-session-status" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Login detected: {d.get(\"login_detected\")}, has_session: {d.get(\"has_session\")}')")
  echo "$STATUS"
  # Cleanup
  curl -s -X DELETE "http://localhost:8010/api/accounts/${AID}" -H "Authorization: Bearer $TOKEN" > /dev/null
done
echo ""
echo "DONE"
