#!/usr/bin/env bash
# End-to-end test for the Custom Access Token Hook (Phase 1, Step 3).
# Proves a real login JWT carries company_id / is_super_admin / roles claims
# (the exact claims the RLS helpers in migration 0002 read).
#
# Prereq: local stack running (npx supabase start).
# Usage:  bash supabase/tests/test_auth_hook.sh
set -euo pipefail

API="http://127.0.0.1:54321"
DBC="supabase_db_app_Evaluation_System"      # adjust if your project dir differs
EMAIL="hr+$(date +%s)@company-a.test"
PASS="Passw0rd!123"

ANON=$(npx -y supabase@latest status -o env 2>/dev/null | grep '^ANON_KEY=' | cut -d'"' -f2)
runsql() { docker exec -i "$DBC" psql -U postgres -d postgres -v ON_ERROR_STOP=1 "$@"; }

echo "=== 1) sign up (hook fires before profile exists) ==="
SIGNUP=$(curl -s -X POST "$API/auth/v1/signup" \
  -H "apikey: $ANON" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
USER_ID=$(node -e "let d=JSON.parse(process.argv[1]); console.log((d.user||d).id)" "$SIGNUP")
echo "user id: $USER_ID"

echo "=== 2) create company + profile + hr_admin role ==="
runsql <<SQL
delete from companies where slug='company-a';
insert into companies (id,name,slug) values ('11111111-1111-1111-1111-111111111111','Company A','company-a');
insert into profiles (id, company_id, display_name) values ('$USER_ID','11111111-1111-1111-1111-111111111111','HR A');
insert into user_roles (profile_id, role_id, company_id)
  select '$USER_ID', r.id, '11111111-1111-1111-1111-111111111111' from roles r where r.code='hr_admin';
SQL

echo "=== 3) direct unit call of the hook ==="
runsql -c "select jsonb_pretty(app.custom_access_token_hook(jsonb_build_object('user_id','$USER_ID','claims','{}'::jsonb)) -> 'claims') as claims;"

echo "=== 4) sign in -> decode JWT payload (end-to-end) ==="
SIGNIN=$(curl -s -X POST "$API/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
node -e "
const t=JSON.parse(process.argv[1]).access_token;
const p=JSON.parse(Buffer.from(t.split('.')[1],'base64').toString());
console.log('company_id     =', p.company_id);
console.log('is_super_admin =', p.is_super_admin);
console.log('roles          =', JSON.stringify(p.roles));
" "$SIGNIN"

echo "=== cleanup ==="
runsql -c "delete from companies where slug='company-a'; delete from auth.users where id='$USER_ID';" >/dev/null
echo "done"
