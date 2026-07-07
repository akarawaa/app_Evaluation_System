#!/usr/bin/env bash
# Integration test for tenant provisioning + RBAC (Step 6).
# Proves: super_admin provisions a tenant (company + cloned BARS templates +
# first hr_admin), the new hr_admin is scoped to its own tenant, hr can create
# employees, and non-super users get 403 on the admin API.
#
# Prereqs: supabase running + API running on :8000. Run: bash backend/tests/test_provisioning.sh
set -uo pipefail
API="http://127.0.0.1:8000"; AUTH="http://127.0.0.1:54321"
DBC="supabase_db_app_Evaluation_System"
PLATFORM="00000000-0000-0000-0000-000000000001"
PW="Passw0rd!123"
ANON=$(npx -y supabase@latest status -o env 2>/dev/null | grep '^ANON_KEY=' | cut -d'"' -f2)
runsql(){ docker exec -i "$DBC" psql -U postgres -d postgres -tA -v ON_ERROR_STOP=1 "$@"; }
jget(){ node -e "let d=JSON.parse(process.argv[1]);console.log(process.argv[2].split('.').reduce((o,x)=>o&&o[x],d))" "$1" "$2"; }
code(){ curl -s -o /dev/null -w "%{http_code}" "$@"; }
signin(){ jget "$(curl -s -X POST "$AUTH/auth/v1/token?grant_type=password" -H "apikey:$ANON" -H 'Content-Type: application/json' -d "{\"email\":\"$1\",\"password\":\"$PW\"}")" access_token; }

for i in $(seq 1 30); do curl -sf "$API/health" >/dev/null && break || sleep 1; done

echo "### bootstrap a super_admin (in platform tenant) ###"
SU_EMAIL="super+$(date +%s)@platform.test"
SU_UID=$(jget "$(curl -s -X POST "$AUTH/auth/v1/signup" -H "apikey:$ANON" -H 'Content-Type: application/json' -d "{\"email\":\"$SU_EMAIL\",\"password\":\"$PW\"}")" user.id)
runsql <<SQL >/dev/null
insert into profiles (id,company_id,display_name) values ('$SU_UID','$PLATFORM','Root');
insert into user_roles (profile_id,role_id,company_id) select '$SU_UID', id,'$PLATFORM' from roles where code='super_admin';
SQL
SU=$(signin "$SU_EMAIL")
echo "super is_super_admin claim: $(node -e "const p=JSON.parse(Buffer.from(process.argv[1].split('.')[1],'base64').toString());console.log(p.is_super_admin)" "$SU")"

echo; echo "########## TESTS ##########"
SLUG="acme-$(date +%s)"; HR_EMAIL="hr@$SLUG.test"
BODY="{\"name\":\"Acme Co\",\"slug\":\"$SLUG\",\"hr_email\":\"$HR_EMAIL\",\"hr_password\":\"$PW\"}"

echo "T1 provision tenant as super_admin (expect 201):"
OUT=$(curl -s -w $'\n%{http_code}' -X POST "$API/api/admin/tenants" -H "Authorization: Bearer $SU" -H 'Content-Type: application/json' -d "$BODY")
HTTP=$(printf '%s' "$OUT" | tail -1); RESP=$(printf '%s' "$OUT" | sed '$d')
CID=$(jget "$RESP" company.id); CLONED=$(jget "$RESP" templates_cloned)
echo "     http=$HTTP  new company_id=$CID  templates_cloned=$CLONED (expect 2)"

echo "T2 cloned criteria for tenant (expect templates=2, items=70):"
echo "     templates=$(runsql -c "select count(*) from criteria_templates where company_id='$CID';")  items=$(runsql -c "select count(*) from criteria_items where company_id='$CID';")"

echo "T3 new hr_admin logs in, company_id scoped to tenant:"
HR=$(signin "$HR_EMAIL")
echo "     hr company_id=$(jget "$(curl -s "$API/api/me" -H "Authorization: Bearer $HR")" company_id)  (expect $CID)"

echo "T4 hr creates an employee (expect 201): $(code -X POST "$API/api/employees" -H "Authorization: Bearer $HR" -H 'Content-Type: application/json' -d '{"emp_code":"E001","full_name":"Somchai","level":"operational"}')"
echo "T5 hr sees only its employees (expect 1/Somchai): $(curl -s "$API/api/employees" -H "Authorization: Bearer $HR" | node -e "process.stdin.once('data',d=>{let a=JSON.parse(d);console.log(a.length,'/',a.map(x=>x.full_name).join(','))})")"
echo "T6 hr_admin CANNOT provision tenant (expect 403): $(code -X POST "$API/api/admin/tenants" -H "Authorization: Bearer $HR" -H 'Content-Type: application/json' -d "{\"name\":\"X\",\"slug\":\"x-$(date +%s)\",\"hr_email\":\"x@x.test\",\"hr_password\":\"$PW\"}")"
echo "T7 audit has tenant_created (expect >=1): $(runsql -c "select count(*) from audit_logs where action='tenant_created' and company_id='$CID';")"

echo; echo "### cleanup ###"
runsql -c "delete from companies where id='$CID' or slug like '${SLUG}%'; delete from auth.users where id='$SU_UID' or email like '%@$SLUG.test';" >/dev/null
echo done
