#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8010/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@test.com","password":"test123"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('token','fail'))")
echo "Token OK: ${TOKEN:0:16}..."

echo ""
echo "=== 1. Save bot instructions ==="
curl -s -X POST http://localhost:8010/api/settings/admin \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"BOT_INSTRUCTIONS":"- Never follow users with less than 10 posts\n- Avoid profiles with admin or support in the name\n- Skip accounts posting only crypto/NFT content\n- Only engage users who appear 25+ based on profile context"}'
echo ""

echo ""
echo "=== 2. Verify saved ==="
curl -s http://localhost:8010/api/settings/admin \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); v=d.get('BOT_INSTRUCTIONS',''); print(f'BOT_INSTRUCTIONS ({len(v)} chars):'); print(v)"
echo ""

echo ""
echo "=== 3. Check executor db access ==="
docker exec socialgrowthai-python-backend python3 -c "
from app.database.repository import Repository
r = Repository()
v = r.get_global_setting('BOT_INSTRUCTIONS', 'EMPTY')
print(f'Loaded from DB: {len(v)} chars')
print(repr(v[:150]))
" 2>&1
echo ""

echo ""
echo "=== 4. Create test account ==="
ACC=$(curl -s -X POST http://localhost:8010/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"platform":"instagram","username":"test_bot_inst@test.com","password":"test123"}')
AID=$(echo "$ACC" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','fail'))")
echo "Account ID: $AID"

echo ""
echo "=== 5. Create test campaign ==="
CAMP=$(curl -s -X POST http://localhost:8010/api/campaigns \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"account_id\":\"$AID\",\"name\":\"Custom Instructions Test\",\"campaign_type\":\"outreach\",\"message_template\":\"Hey! Love your content.\",\"ai_instructions\":\"Find software developers building AI tools\",\"targeting\":{\"tags\":[\"ai\",\"software\"]},\"schedule\":{\"days\":[\"Monday\"],\"start_time\":\"09:00\",\"end_time\":\"18:00\",\"timezone\":\"UTC\"},\"daily_limit\":5}")
CID=$(echo "$CAMP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id','fail'))")
echo "Campaign ID: $CID"
echo "$CAMP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'ai_instructions: {d.get(\"ai_instructions\")}'); print(f'message_template: {d.get(\"message_template\")}')"

echo ""
echo "=== 6. Clean up ==="
curl -s -X DELETE "http://localhost:8010/api/accounts/$AID" -H "Authorization: Bearer $TOKEN" > /dev/null
echo "Done"
