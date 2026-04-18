#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-http://localhost}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin}"

echo "1. Login"
TOKEN=$(curl -sf -X POST "$HOST/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

echo "2. List courses"
COUNT=$(curl -sf -H "Authorization: Bearer $TOKEN" "$HOST/api/courses" \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
echo "   got $COUNT courses"
if [ "$COUNT" -lt 4 ]; then echo "FAIL: expected >= 4 courses"; exit 1; fi

echo "3. SAST detail"
MODS=$(curl -sf -H "Authorization: Bearer $TOKEN" "$HOST/api/courses/sast-secrets-track" \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["modules"]))')
echo "   sast has $MODS modules"
if [ "$MODS" -lt 8 ]; then echo "FAIL: expected >= 8 modules in sast"; exit 1; fi

echo "4. SQLi detail (short course)"
SMODS=$(curl -sf -H "Authorization: Bearer $TOKEN" "$HOST/api/courses/sqli-track" \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["modules"]))')
echo "   sqli has $SMODS modules"
if [ "$SMODS" -ne 1 ]; then echo "FAIL: expected 1 module in sqli"; exit 1; fi

echo "5. Redirect /api/tracks"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$HOST/api/tracks")
echo "   /api/tracks -> $CODE"
if [ "$CODE" != "308" ]; then echo "FAIL: expected 308 on /api/tracks"; exit 1; fi

echo ""
echo "ALL SMOKE TESTS PASSED"
