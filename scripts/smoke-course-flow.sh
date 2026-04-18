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
echo "=== Admin CRUD smoke ==="

# Re-login as admin to refresh token (uses same credentials as above)
ADMIN_TOKEN=$(curl -sf -X POST "$HOST/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

echo "6. Create smoke task (theory)"
curl -sf -X POST "$HOST/api/admin/content/tasks" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"slug":"smoke-theory","title":"Smoke","type":"theory","config":{"content_kind":"text","content":"hi"}}' \
  > /dev/null

echo "7. Create smoke course"
COURSE_ID=$(curl -sf -X POST "$HOST/api/admin/content/courses" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"slug":"smoke-course","title":"Smoke Course"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "   course id: $COURSE_ID"
if [ -z "$COURSE_ID" ] || [ "$COURSE_ID" = "None" ]; then
  echo "FAIL: could not create smoke course"; exit 1
fi

# Cleanup trap: always try to remove smoke-course and smoke-theory even if later steps fail
cleanup_smoke() {
  curl -s -X PATCH "$HOST/api/admin/content/courses/$COURSE_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"is_visible":false}' > /dev/null 2>&1 || true
  curl -s -X DELETE "$HOST/api/admin/content/courses/$COURSE_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null 2>&1 || true
  TASK_ID=$(curl -s "$HOST/api/admin/content/tasks?search=smoke-theory" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d[0]["id"] if d else "")' 2>/dev/null || echo "")
  if [ -n "$TASK_ID" ]; then
    curl -s -X DELETE "$HOST/api/admin/content/tasks/$TASK_ID" \
      -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null 2>&1 || true
  fi
}
trap cleanup_smoke EXIT

echo "8. Publish smoke course"
curl -sf -X PATCH "$HOST/api/admin/content/courses/$COURSE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"is_visible":true}' > /dev/null

echo "9. Student GET /api/courses sees smoke-course"
SEEN=$(curl -sf -H "Authorization: Bearer $TOKEN" "$HOST/api/courses" \
  | python3 -c 'import json,sys; print(sum(1 for c in json.load(sys.stdin) if c.get("slug")=="smoke-course"))')
if [ "$SEEN" != "1" ]; then
  echo "FAIL: smoke-course not visible to student (found $SEEN)"; exit 1
fi

echo "10. Unpublish smoke course"
curl -sf -X PATCH "$HOST/api/admin/content/courses/$COURSE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"is_visible":false}' > /dev/null

echo "11. Delete smoke course"
curl -sf -X DELETE "$HOST/api/admin/content/courses/$COURSE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null

echo "12. Lookup and delete smoke task"
TASK_ID=$(curl -sf "$HOST/api/admin/content/tasks?search=smoke-theory" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);
import sys as _s
if not d: _s.exit("task-not-found")
print(d[0]["id"])')
if [ -z "$TASK_ID" ]; then
  echo "FAIL: smoke-theory task not found for cleanup"; exit 1
fi
curl -sf -X DELETE "$HOST/api/admin/content/tasks/$TASK_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null

# Disarm trap; clean exit
trap - EXIT

echo "=== Admin CRUD smoke OK ==="
echo ""
echo "ALL SMOKE TESTS PASSED"
