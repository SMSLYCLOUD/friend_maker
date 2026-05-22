#!/bin/bash
# Create a small test image
python3 -c "
import struct, zlib
def create_png(w,h):
    raw = b''
    for y in range(h):
        raw += b'\\x00' + bytes([255,0,0] * w)[:w*3]
    c = zlib.compress(raw)
    sig = b'\\x89PNG\\r\\n\\x1a\\n'
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    def chunk(t,d):
        return struct.pack('>I',len(d)) + t + d + struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    return sig + chunk(b'IHDR',ihdr) + chunk(b'IDAT',c) + chunk(b'IEND',b'')
with open('/tmp/test_ref.png','wb') as f: f.write(create_png(64,64))
print('Created test image')
"
# Get token
TOKEN=$(curl -s -X POST http://localhost:8010/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@test.com","password":"test123"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('token','fail'))")
echo "Token: ${TOKEN:0:16}..."

# Upload
echo "=== Upload image ==="
UPLOAD=$(curl -s -X POST http://localhost:8010/api/settings/upload-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_ref.png")
echo "$UPLOAD"
FILENAME=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('filename','fail'))")
echo "Filename: $FILENAME"

# List
echo "=== List images ==="
curl -s http://localhost:8010/api/settings/images \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Images: {len(d.get(\"images\",[]))}')"

# Serve
echo "=== Serve image ==="
curl -s -o /dev/null -w "HTTP %{http_code}, Size: %{size_download} bytes\n" \
  http://localhost:8010/api/settings/images/$FILENAME

# Delete
echo "=== Delete image ==="
curl -s -X DELETE "http://localhost:8010/api/settings/images/$FILENAME" \
  -H "Authorization: Bearer $TOKEN"

echo ""
echo "DONE"
