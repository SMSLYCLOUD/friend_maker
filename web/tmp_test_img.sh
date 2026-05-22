#!/bin/bash
echo "=== Test backend endpoints ==="
echo "GET /api/settings/admin:"
curl -s http://localhost:8010/api/settings/admin | python3 -c "
import sys,json
d=json.load(sys.stdin)
bi = d.get('BOT_INSTRUCTIONS','')
bii = d.get('BOT_INSTRUCTION_IMAGES','[]')
print(f'  Bot instructions: {len(bi)} chars')
print(f'  Bot instruction images: {bii}')
"
echo ""
echo "GET /api/settings/images:"
curl -s http://localhost:8010/api/settings/images | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'  Images: {len(d.get(\"images\",[]))}')
"
echo ""
echo "OK"
