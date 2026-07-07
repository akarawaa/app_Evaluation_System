#!/usr/bin/env bash
# Integration smoke test for the Phase 1 API (Step 5).
# Proves through real HTTP + real JWTs: auth required, JWT claims, RLS scoping
# via FastAPI, branch create + audit in one transaction, and RBAC (403).
#
# Prereqs:
#   1) local Supabase running:   npx supabase start
#   2) API running:              cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000
# Run:  bash backend/tests/test_api.sh
set -uo pipefail
API="http://127.0.0.1:8000"
AUTH="http://127.0.0.1:54321"
DBC="supabase_db_app_Evaluation_System"     # adjust if your project dir differs
A="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
B="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
PW="Passw0rd!123"
ANON=$(npx -y supabase@latest status -o env 2>/dev/null | grep '^ANON_KEY=' | cut -d'"' -f2)
runsql(){ docker exec -i "$DBC" psql -U postgres -d postgres -tA -v ON_ERROR_STOP=1 "$@"; }
jget(){ node -e "let d=JSON.parse(process.argv[1]);console.log(process.argv[2].split('.').reduce((o,x)=>o&&o[x],d))" "$1" "$2"; }
code(){ curl -s -o /dev/null -w "%{http_code}" "$@"; }

for i in $(seq 1 30); do curl -sf "$API/health" >/dev/null && break || sleep 1; done

HR_EMAIL="hr+$(date +%s)@a.test"; EMP_EMAIL="emp+$(date +%s)@a.test"
HR_UID=$(jget "$(curl -s -X POST "$AUTH/auth/v1/signup" -H "apikey:$ANON" -H 'Content-Type: application/json' -d "{\"email\":\"$HR_EMAIL\",\"password\":\"$PW\"}")" "user.id")
EMP_UID=$(jget "$(curl -s -X POST "$AUTH/auth/v1/signup" -H "apikey:$ANON" -H 'Content-Type: application/json' -d "{\"email\":\"$EMP_EMAIL\",\"password\":\"$PW\"}")" "user.id")

runsql <<SQL >/dev/null
delete from companies where slug in ('company-a','company-b');
insert into companies (id,name,slug) values ('$A','Company A','company-a'),('$B','Company B','company-b');
insert into profiles (id,company_id,display_name) values ('$HR_UID','$A','HR A'),('$EMP_UID','$A','Emp A');
insert into user_roles (profile_id,role_id,company_id) select '$HR_UID', id,'$A' from roles where code='hr_admin';
insert into user_roles (profile_id,role_id,company_id) select '$EMP_UID', id,'$A' from roles where code='employee';
insert into branches (company_id,name) values ('$A','A-HQ');
insert into employees (company_id,emp_code,full_name) values ('$A','A001','Alice A'),('$B','B001','Bob B');
SQL

signin(){ jget "$(curl -s -X POST "$AUTH/auth/v1/token?grant_type=password" -H "apikey:$ANON" -H 'Content-Type: application/json' -d "{\"email\":\"$1\",\"password\":\"$PW\"}")" "access_token"; }
HR=$(signin "$HR_EMAIL"); EMP=$(signin "$EMP_EMAIL")

echo "T1 no-token /api/employees (401):        $(code "$API/api/employees")"
echo "T2 /me company_id:                       $(jget "$(curl -s "$API/api/me" -H "Authorization: Bearer $HR")" company_id)"
echo "T3 employees visible to HR (1/Alice A):  $(curl -s "$API/api/employees" -H "Authorization: Bearer $HR" | node -e "process.stdin.once('data',d=>{let a=JSON.parse(d);console.log(a.length,'/',a.map(x=>x.full_name).join(','))})")"
echo "T4 create branch as HR (201):            $(code -X POST "$API/api/branches" -H "Authorization: Bearer $HR" -H 'Content-Type: application/json' -d '{"name":"A-Service"}')"
echo "T5 branches now (2):                     $(curl -s "$API/api/branches" -H "Authorization: Bearer $HR" | node -e "process.stdin.once('data',d=>{let a=JSON.parse(d);console.log(a.length,'/',a.map(x=>x.name).join(','))})")"
echo "T6 audit rows for A create (1):          $(runsql -c "select count(*) from audit_logs where company_id='$A' and action='create' and entity_type='branches';")"
echo "T7 create branch as employee (403):      $(code -X POST "$API/api/branches" -H "Authorization: Bearer $EMP" -H 'Content-Type: application/json' -d '{"name":"hack"}')"

runsql -c "delete from companies where slug in ('company-a','company-b'); delete from auth.users where id in ('$HR_UID','$EMP_UID');" >/dev/null
