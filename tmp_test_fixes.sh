#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8010/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@test.com","password":"test123"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('token','fail'))")
echo "Token OK: ${TOKEN:0:16}..."

echo ""
echo "=== 1. Test campaign create with wrong account_id ==="
BAD=$(curl -s -X POST http://localhost:8010/api/campaigns \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"account_id":"fake-id","name":"Test","campaign_type":"outreach","targeting":{"tags":["ai"]},"message_template":"Hi","schedule":{"days":["Mon"],"start_time":"09:00","end_time":"18:00","timezone":"UTC"}}')
echo "$BAD"
echo ""

echo ""
echo "=== 2. Create valid account + campaign ==="
ACC=$(curl -s -X POST http://localhost:8010/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"platform":"instagram","username":"test_fix@test.com","password":"test123"}')
AID=$(echo "$ACC" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','fail'))")
echo "Account: $AID"
CAMP=$(curl -s -X POST http://localhost:8010/api/campaigns \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"account_id\":\"$AID\",\"name\":\"Test Campaign\",\"campaign_type\":\"outreach\",\"ai_instructions\":\"Find devs\",\"message_template\":\"Hi there!\",\"targeting\":{\"tags\":[\"ai\"]},\"schedule\":{\"days\":[\"Monday\"],\"start_time\":\"09:00\",\"end_time\":\"18:00\",\"timezone\":\"UTC\"}}")
CID=$(echo "$CAMP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','fail'))")
PLATFORM=$(echo "$CAMP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('platform','none'))")
echo "Campaign: $CID (platform: $PLATFORM)"
echo ""

echo ""
echo "=== 3. Update campaign ==="
UPD=$(curl -s -X PUT "http://localhost:8010/api/campaigns/$CID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Campaign","daily_limit":100}')
echo "$UPD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Name: {d.get(\"name\")}, Limit: {d.get(\"daily_limit\")}')"
echo ""

echo ""
echo "=== 4. Delete campaign ==="
DEL=$(curl -s -X DELETE "http://localhost:8010/api/campaigns/$CID" \
  -H "Authorization: Bearer $TOKEN")
echo "$DEL"
echo ""

echo ""
echo "=== 5. Verify deleted ==="
LIST=$(curl -s "http://localhost:8010/api/campaigns" \
  -H "Authorization: Bearer $TOKEN")
echo "$LIST" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Campaigns remaining: {len(d)}')"
echo ""

echo ""
echo "=== 6. Test optimize with path param ==="
OPT=$(curl -s -X POST "http://localhost:8010/api/optimize/fake-id" \
  -H "Authorization: Bearer $TOKEN")
echo "$OPT"
echo ""

echo ""
echo "=== 7. Test image serve with auth ==="
IMG=$(curl -s -o /dev/null -w "HTTP %{http_code}" "http://localhost:8010/api/settings/images/nonexistent.png" \
  -H "Authorization: Bearer $TOKEN")
echo "Image serve auth: $IMG"
echo ""

echo ""
echo "=== 8. Cleanup ==="
curl -s -X DELETE "http://localhost:8010/api/accounts/$AID" -H "Authorization: Bearer $TOKEN" > /dev/null
echo "Done"
