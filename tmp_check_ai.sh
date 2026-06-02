#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8010/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@test.com","password":"test123"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('token','fail'))")

echo "=== Create campaign ==="
ACC=$(curl -s -X POST http://localhost:8010/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"platform":"instagram","username":"test_show@test.com","password":"test123"}')
AID=$(echo "$ACC" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id','fail'))")
echo "Account: $AID"

CAMP=$(curl -s -X POST http://localhost:8010/api/campaigns \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"account_id\":\"$AID\",\"name\":\"My Campaign\",\"campaign_type\":\"outreach\",\"message_template\":\"Hey nice profile!\",\"ai_instructions\":\"Find AI developers\",\"targeting\":{\"tags\":[\"ai\"]},\"schedule\":{\"days\":[\"Monday\"],\"start_time\":\"09:00\",\"end_time\":\"18:00\",\"timezone\":\"UTC\"}}")
echo "$CAMP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'ai_instructions: \"{d.get(\"ai_instructions\")}\"')
print(f'message_template: \"{d.get(\"message_template\")}\"')
print(f'account_id: \"{d.get(\"account_id\")}\"')
"

curl -s -X DELETE "http://localhost:8010/api/accounts/$AID" -H "Authorization: Bearer $TOKEN" > /dev/null
echo "Done"
