# Project Status — E-Appraisal  *(อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง)*

> เอกสารมีชีวิต (living doc) — **อัปเดตทุกครั้งที่จบงาน** เพื่อส่งต่อ session ถัดไป

**อัปเดตล่าสุด:** 2026-07-06
**Phase ปัจจุบัน:** Phase 1 — Foundation
**สเต็ปที่กำลังทำ:** Phase 1–3 + admin tooling ครบ + **role-based UI ทุกหน้า** เสร็จ+พิสูจน์ (pytest 54/54 · browser เดินครบ 5 role) → เหลือรอ HR (สูตร attendance, BARS anchors) + bundle ฟอนต์ OFL

---

## ✅ ทำไปแล้ว
- อ่าน/วิเคราะห์ใบประเมินเดิม FMHR07 → `docs/evaluation-form-analysis.md`
- วิเคราะห์ช่องโหว่ PROJECT_PLAN.md (multi-tenant) → สะท้อนใน SECURITY.md
- ตัดสินใจสถาปัตยกรรมหลัก + tooling (ดู "การตัดสินใจที่ล็อกแล้ว")
- `git init` + commit แรก (เอกสารควบคุมงานครบ)
- **โครงโฟลเดอร์:** `backend/` (FastAPI: app/core/api/services/repositories/schemas + config + main + requirements + .env.example), `frontend/` (package.json + .env.example), `supabase/`
- **SQL migrations (เขียนแล้ว ยังไม่รัน):** `supabase/migrations/0001–0006` — extensions, auth helpers (JWT claim readers), tenant+identity schema (FK/CHECK/index), criteria (BARS), audit_logs, **RLS policies ครบทุกตาราง**
- **Seed:** `supabase/seed.sql` — role catalog + master template FMHR07 (operational 28 ข้อ, supervisor 42 ข้อ; desc_1..5 เว้นให้ HR เติม)
- **รัน migration จริงผ่านแล้ว** บน Supabase local (Docker) — `supabase init` + `supabase start` (ปิด `[analytics]` ใน config.toml เพราะ container นี้ล้มบน Windows)
- **RLS ยืนยันด้วย negative test 7 เคส ผ่านหมด** → `supabase/tests/rls_negative_test.sql` (บริษัท A เห็น/แก้ข้อมูลบริษัท B ไม่ได้, master template แชร์ได้, audit ลบไม่ได้)
- **Step 3 Auth Hook เสร็จ+พิสูจน์แล้ว** → `supabase/migrations/0007_auth_hook.sql` (SECURITY DEFINER, ฝัง company_id/is_super_admin/roles), เปิดใน `config.toml` `[auth.hook.custom_access_token]`. JWT จริงจากการ login มี claims ครบ → `supabase/tests/test_auth_hook.sh`
- **Step 5 FastAPI เสร็จ+พิสูจน์แล้ว** → `backend/app/` (core: config/logging/security/db/middleware · api/routes · services/audit · schemas/branch). JWT verify ผ่าน **JWKS/ES256**, `get_tenant_session` ตั้ง `request.jwt.claims` + `set local role authenticated` ต่อ request ให้ RLS ทำงานผ่าน API, middleware request_id + structured log + security headers, audit เขียนใน transaction เดียวกับ mutation, RBAC ผ่าน `require_roles`. **API test 7/7 ผ่าน** → `backend/tests/test_api.sh`
- **ข้อค้นพบสำคัญ:** Supabase CLI ใหม่เซ็น access token ด้วย **ES256 + JWKS** (ไม่ใช่ HS256 secret) → verify ต้องดึง public key จาก `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`; ต้องมี `cryptography`. Python 3.9 บนเครื่องนี้ต้อง pin `greenlet==3.1.1` (ไม่มี wheel cp39 รุ่นใหม่ + ไม่มี MSVC)
- **Step 6 Provisioning เสร็จ+พิสูจน์แล้ว** → `0008_platform_tenant.sql` (platform tenant ที่อยู่ super_admin), `0009_clone_templates.sql` (ฟังก์ชัน clone master→tenant, self-guard super_admin), `backend/app/api/admin.py` (POST /api/admin/tenants: สร้าง company + clone 2 template/70 items + สร้าง hr_admin ผ่าน GoTrue admin API + audit), `POST /api/employees` (hr_admin). **test 7/7** → `backend/tests/test_provisioning.sh`
- **Step 7 React เสร็จ+พิสูจน์แล้ว** → `frontend/` (Vite+React+TS+Tailwind): AuthContext (supabase-js), ProtectedRoute, Login, Dashboard (เรียก /api/me + /api/employees). `npm run build` ผ่าน; login จริงใน browser → Dashboard แสดง claims + พนักงาน scope ตาม tenant. `.claude/launch.json` = preview config (`npm --prefix frontend run dev`)
- **Step 8 Hardening เสร็จ** →
  - **pytest security suite 15/15 ผ่าน** → `backend/tests/test_security_isolation.py` + `conftest.py` (fixtures: 2 tenants + hr/employee/super_admin ผ่าน GoTrue admin API, cleanup ด้วย asyncpg). ครอบ: ทุก endpoint ต้องมี auth (401), tenant isolation ของ read/write ทุก endpoint, RBAC (403), super_admin provisioning + clone, security headers, invalid token. รัน: `cd backend && .venv/Scripts/python -m pytest`
  - **npm audit:** อัป vite→8.1.3 + plugin-react→6.0.3 → **0 vulnerabilities** (build ยังผ่าน)
  - **pip-audit:** รันแล้ว — ส่วนใหญ่เป็น dev tooling (pip/setuptools/pytest/filelock/msgpack/requests). runtime (starlette/urllib3) ติดตั้งเวอร์ชันล่าสุดที่มีแล้ว fix version ยังไม่ปล่อย = **no-fix-available, track ไว้** (ทบทวนเมื่อ FastAPI/starlette ออกแพตช์)

- **Phase 2 Step 1 (schema) เสร็จ+พิสูจน์แล้ว** → `docs/EVALUATION_DESIGN.md` + `docs/PHASE_2_PLAN.md`; migrations `0010` (roles dept_manager/md), `0011` (evaluation_cycles/evaluations/items snapshot/scores(CHECK 1–5 step .5)/comments/attendance + RLS ทุกตาราง), `0012` (evaluation_approvals append-only), `0013` (fn `snapshot_evaluation_items`, `recompute_evaluation_totals` equal-weight). Smoke test: snapshot 28 → 112/140 +att30 → 142/180=78.89%, CHECK กัน 4.3 ✓
- **การตัดสินใจ Phase 2:** 2 ชนิด (annual/probation), หัวหน้าให้คะแนน (ไม่มี self), workflow หลายชั้น routing **ตามสายบังคับบัญชาจริง** (supervisor_id→manager_id→role md→role hr_admin), คะแนนเท่ากันทุกข้อ, snapshot เกณฑ์ตอนสร้างใบ

- **Phase 2 Step 2 (backend lifecycle) เสร็จ+พิสูจน์** → `backend/app/api/evaluations.py`, `services/evaluations.py`, `schemas/evaluation.py`. Endpoints: POST /api/evaluations (สร้าง+snapshot), GET (list/detail), PUT /{id}/scores (คะแนน+comment+attendance, เฉพาะ evaluator, สถานะ draft/returned), POST /{id}/submit·/approve·/return·/finalize. Routing ตามสายจริง (evaluator=supervisor_id, approve dept=manager_id, md=role, hr finalize=role), audit ทุก transition. **pytest 18/18** (`test_evaluation_lifecycle.py` เดิน draft→submit→dept→md→finalize + เช็ค 403 ทุกชั้น + cross-tenant 404)

- **Phase 2 Step 3 (frontend) เสร็จ+พิสูจน์** → `frontend/src/pages/Evaluations.tsx` (list + สร้างใบ), `EvaluationDetail.tsx` (ฟอร์มให้คะแนนราย item 1–5 step .5 + comment ระดับหมวด + attendance + ปุ่ม submit/approve/return/finalize ตามสถานะ), `lib/api.ts` (+apiSend), `types.ts`; backend เพิ่ม `GET /api/templates`. `npm run build` ผ่าน; ทดสอบ browser จริง: login หัวหน้า → สร้างใบ (snapshot 28) → ให้คะแนน 4 ทุกข้อ+att30 → บันทึก (112/140, 78.89%) → submit (→รอ ผจก.แผนก) ไม่มี console error

- **Phase 3 (PDF export) เสร็จ+พิสูจน์** → `backend/app/services/pdf.py` (ReportLab + ฟอนต์ไทย Leelawadee UI, path ตั้งค่าผ่าน `PDF_FONT_PATH` เผื่อ Linux), `GET /api/evaluations/{id}/pdf` (RLS-scoped + audit `evaluation_exported`), `services/evaluations.get_report_context` (resolve ชื่อ emp/evaluator/company). Frontend: `apiDownload` + ปุ่ม "ดาวน์โหลด PDF". พิสูจน์: อ่าน PDF จริง — ฟอนต์ไทยถูก, layout (header บริษัท·ตารางข้อมูล·เกณฑ์รายหมวด·สรุปคะแนน·การอนุมัติ). pytest 19/19 (+`test_pdf_export`)
  > production ควร bundle ฟอนต์ OFL (เช่น Sarabun) แทนฟอนต์ระบบ Windows

- **Approval Inbox เสร็จ+พิสูจน์** → `GET /api/evaluations/inbox` (`services/evaluations.list_inbox`, ประกาศ**ก่อน** `/{eval_id}` ใน router กัน path collision) resolve งานที่รอผู้ใช้ตาม role/สายบังคับบัญชาแบบเดียวกับ authorization จริง (score=evaluator, dept_approve=manager_id, md_approve=role md, finalize=role hr_admin). Frontend: `pages/Inbox.tsx` + type `InboxItem`/`ACTION_LABEL`, ลิงก์ "งานที่รอฉัน" บน Dashboard/Evaluations, route `/inbox`. พิสูจน์: pytest เดินครบ 4 ชั้น (inbox ของแต่ละคนถูก/ไม่ถูกตามช่วง) + browser จริง (login ผจก.แผนก → เห็นใบรออนุมัติ → กดอนุมัติ → inbox ว่าง "ไม่มีงานค้าง 🎉"). **pytest 20/20**

- **หน้าจัดการ employee/branch เสร็จ+พิสูจน์** → `backend/app/services/employees.py` (list/create/update employee, list/create/rename branch; **validate branch_id/supervisor_id/manager_id ผ่าน RLS-scoped SELECT** — plain FK ไม่พอเพราะไม่รู้ tenant, ต้องยืนยันว่าแถวที่อ้างอิงมองเห็นได้ใน session ของผู้เรียกจริง ๆ), `schemas/employee.py` (+EmployeeUpdate, ขยาย EmployeeOut ให้มี branch/supervisor/manager id+name). Routes: `GET/PATCH /api/employees/{id}`, `PATCH /api/branches/{id}` (เดิมมี GET/POST อยู่แล้ว). Frontend: `pages/People.tsx` (จัดการสาขา + ฟอร์มเพิ่ม/แก้ไขพนักงานพร้อม dropdown branch/supervisor/manager + toggle active/inactive), route `/people`, ลิงก์ "พนักงาน & สาขา" (เฉพาะ hr_admin/super_admin). พิสูจน์: pytest 6 เคสใหม่ (`test_admin_management.py`: rename branch, สร้าง employee พร้อม org chain, แก้ไข, **กัน self-supervisor (400)**, **กัน cross-tenant branch/supervisor (400)**, RBAC 403) + browser จริงครบ flow (สร้างสาขา→เพิ่มหัวหน้า→เพิ่มลูกน้องผูก branch+supervisor→แก้ไขตำแหน่ง→ปิดใช้งาน→rename สาขา). **pytest 26/26**

- **นำเข้าพนักงานจาก CSV เสร็จ+พิสูจน์** (สำหรับตอนขึ้นระบบครั้งแรก/เพิ่มพนักงานจำนวนมาก) → `backend/app/services/employee_import.py`:
  - **Two-pass**: pass 1 upsert พนักงานทุกแถว (by emp_code) ไม่แตะสาย, pass 2 resolve `รหัสหัวหน้างาน`/`รหัสผจก.แผนก` เทียบกับ emp_code ในไฟล์เดียวกัน + พนักงานเดิมในระบบ — ทำให้อ้างอิงหัวหน้าที่อยู่แถวไหนของไฟล์ก็ได้
  - **Idempotent**: import ซ้ำด้วย emp_code เดิม = แก้ไข ไม่สร้างซ้ำ (แก้ไฟล์แล้วอัปโหลดใหม่ได้เรื่อย ๆ)
  - **Partial success ต่อแถว** ด้วย `session.begin_nested()` (SAVEPOINT ต่อแถว, บาง row error ไม่ทำให้ทั้งไฟล์ fail) — จุดที่ต้องระวัง: แยก branch upsert เป็น SAVEPOINT ของตัวเอง (ซ้อนอีกชั้น) ไม่งั้น cache ใน memory จะไม่ sync กับ DB ที่ rollback ไปแล้วถ้า insert พนักงานล้มเหลวทีหลัง
  - Endpoints: `GET /employees/import-template` (CSV UTF-8 BOM, header ไทย), `POST /employees/import` (multipart, hr_admin only) — **ต้องประกาศก่อน** `/employees/{employee_id}` กัน path collision (เหมือน `/inbox`)
  - เพิ่ม `python-multipart` ใน requirements
  - Frontend: `apiUpload` (FormData, ไม่ตั้ง Content-Type เอง), section ใน `People.tsx` (ดาวน์โหลด template + file input + สรุปผล created/updated/linked/branches_created + ตาราง error รายแถว)
  - พิสูจน์: pytest 9 เคสใหม่ (`test_employee_import.py`: สร้าง+link+branch auto-create, idempotent re-import, partial failure ไม่ทำทั้งไฟล์ล้ม, self-reference reject, unresolved code reject, **cross-tenant link reject**, wrong header reject, RBAC) + browser จริง (อัปโหลดไฟล์จำลอง 3 แถว → 2 สร้างสำเร็จ+ผูกสาย+สร้างสาขา, 1 error แสดงเลขแถว/ข้อความถูกต้อง, ตารางอัปเดต resolve ชื่อครบ). **pytest 35/35**

- **หน้าจัดการ tenant (super_admin) เสร็จ+พิสูจน์** →
  - **Suspend มี enforcement จริง** (จุดสำคัญ — ไม่ใช่แค่ flag สวยงาม): เพิ่มเช็คใน `core/db.get_tenant_session` (จุดเดียวที่ทุก request ผ่าน) — ถ้า `company.status != 'active'` และ user ไม่ใช่ super_admin → 403 ทันที ไม่ต้องแก้ RLS policy ทุกตาราง
  - `services/tenant_admin.py`: list/get/update-status/invite-user — เพราะ super_admin เอง `company_id` ชี้ไป platform tenant ไม่ใช่ tenant ที่กำลังจัดการ ทุก query จึง**ระบุ `company_id` (จาก path) ตรง ๆ** แทนที่จะพึ่ง RLS scope โดยนัยแบบ services อื่น
  - Routes: `GET/POST /api/admin/tenants`, `GET /api/admin/tenants/{id}`, `PATCH /api/admin/tenants/{id}/status`, `POST /api/admin/tenants/{id}/users` (invite — role ถูกจำกัดด้วย pattern ใน schema กัน mint super_admin ผ่านช่องทางนี้)
  - Frontend: `pages/Tenants.tsx` (list + สร้างบริษัทใหม่), `pages/TenantDetail.tsx` (ข้อมูล + ปุ่มระงับ/เปิดใช้งาน + เชิญผู้ใช้ + ตาราง users), route `/tenants`, `/tenants/:id`, ลิงก์ "จัดการบริษัท" (เฉพาะ super_admin)
  - พิสูจน์: pytest 11 เคสใหม่ (`test_tenant_admin.py`: list/detail RBAC, **suspend บล็อกจริง + reactivate คืนสิทธิ์**, invite+login ยืนยัน role ใน JWT, กัน mint super_admin (422), กัน cross-tenant employee_id (400)) + browser จริงครบ flow (สร้าง tenant→เชิญ dept_manager→กดระงับ→**ยืนยันด้วย curl ว่า hr_admin โดน 403 จริง**→เปิดใช้งานคืน→ยืนยัน 200). **pytest 46/46**

- **Self-service invite เสร็จ+พิสูจน์** (hr_admin เชิญผู้ใช้เองในบริษัทตัวเอง ไม่ต้องพึ่ง super_admin) →
  - **Reuse `services/tenant_admin.invite_user` เดิม** ตรง ๆ แค่เรียกด้วย `company_id=user.company_id` (จาก JWT ที่ verify แล้ว ไม่รับจาก client) แทน path param ของ super_admin — validation (role ที่ mint ได้, กัน cross-tenant employee_id) ใช้ร่วมกันไม่ต้องเขียนซ้ำ
  - `services/users.py` ใหม่ (`list_users`) — ต่างจาก `tenant_admin.py` ตรงที่ query **ไม่ต้องระบุ company_id เอง** เพราะ RLS scope โดยนัยผ่าน `user.company_id` ของ hr_admin ทำงานถูกต้องอยู่แล้ว (คนละสถานการณ์กับ super_admin ที่ company_id ชี้ไป platform tenant)
  - Routes: `GET /api/users`, `POST /api/users/invite` (ทั้งคู่ hr_admin only)
  - Frontend: เพิ่ม section "ผู้ใช้ระบบ (บัญชีเข้าสู่ระบบ)" ใน `People.tsx` — ฟอร์ม invite + ตาราง users, อธิบายชัดว่าต่างจาก "พนักงาน" ยังไง (employees=ใครถูกประเมิน, users=ใครล็อกอินได้)
  - พิสูจน์: pytest 7 เคสใหม่ (`test_self_invite.py`: list เห็นเฉพาะ tenant ตัวเอง, invite+login ยืนยัน role, **เชิญข้าม tenant ไม่ได้เพราะไม่มีช่องรับ company_id เลย**, RBAC, กัน mint super_admin, กัน cross-tenant employee_id) + browser จริง (login hr_admin→invite manager→login ผู้ถูกเชิญจริงผ่าน curl ยืนยัน company_id/role ถูกต้อง). **pytest 53/53**

- **Role-based UI ทุกหน้า เสร็จ+พิสูจน์** →
  - **🔒 พบ+ปิดช่องโหว่จริงระหว่างทำ (ไม่ใช่แค่ UI polish):** `services/evaluations.py` เทียบ `actor_emp == ev["emp_manager_id"]` แบบ Python ตรง ๆ — Python's `None == None` คืน `True` (ต่างจาก SQL ที่ `NULL = NULL` เป็น unknown/false เสมอ) ทำให้ผู้ใช้ที่ยังไม่ผูก `employee_id` (เช่นเพิ่ง invite ใหม่) อาจอนุมัติใบของพนักงานที่ยังไม่มี `manager_id` ได้ทั้งที่ไม่ควรมีสิทธิ์ **แก้ด้วย `_same_employee(a, b)` helper** (คืน False ถ้าฝั่งใดฝั่งหนึ่งเป็น None) ใช้แทนทุกจุดเทียบ actor_emp ในไฟล์ (4 จุด: create, _require_evaluator, approve, return_to_draft) + regression test `test_unlinked_profile_cannot_approve_managerless_employee`
  - `GET /api/me` เพิ่ม `employee_id` (lookup จาก profiles) — เป็นกุญแจให้ frontend เช็คสิทธิ์แบบเป๊ะ (ไม่ใช่แค่ role) ว่า "ฉันคือ evaluator/ผจก.แผนกของใบนี้จริงไหม"
  - `AuthContext` ยกระดับให้ fetch+เก็บ `me` ส่วนกลาง (แยก `meLoading` ออกจาก `loading` ของ session กันเช็คสิทธิ์ก่อน `me` โหลดเสร็จ) ทุกหน้าดึงจาก context เดียวกัน ไม่ fetch ซ้ำ
  - `components/RequireRole.tsx` ใหม่ — gate route `/people` (hr_admin), `/tenants`, `/tenants/:id` (super_admin) แสดง "คุณไม่มีสิทธิ์เข้าถึงหน้านี้" แทนหน้าที่พังจาก 403 กระจาย
  - `Evaluations.tsx`: ซ่อนฟอร์ม "สร้างใบประเมิน" ทั้งหมดถ้าไม่ใช่ hr_admin/super_admin/มีลูกน้อง + กรอง dropdown พนักงานให้เหลือเฉพาะที่ตัวเองเป็นหัวหน้า (ตรงกับ backend `create()` เป๊ะ)
  - `EvaluationDetail.tsx`: ปุ่มทุกปุ่ม (บันทึก/ส่ง/อนุมัติ/ตีกลับ/สรุปปิดใบ) โผล่เฉพาะผู้มีสิทธิ์จริงตามสถานะปัจจุบัน ไม่ใช่ทุกคนที่เห็นหน้า — ช่องกรอกคะแนนก็ disabled ถ้าไม่ใช่ evaluator; มีข้อความ "รอ...อนุมัติ" แทนที่ปุ่มให้คนที่ไม่มีสิทธิ์เห็นสถานะรอ
  - พิสูจน์: pytest 54/54 (รวม regression ใหม่) + browser เดินครบ 5 login (employee ธรรมดา→ไม่เห็นฟอร์มสร้าง/เข้า `/people`,`/tenants` ไม่ได้; หัวหน้า→สร้าง+ให้คะแนน+submit เห็นแค่ปุ่มตัวเอง; ผจก.แผนก→เห็นปุ่มเฉพาะตอน submitted; MD→เห็นเฉพาะตอน dept_approved; HR→เห็นเฉพาะตอน md_approved) ครบวงจรจนถึง "ปิดใบแล้ว" ไม่มี console error

## 🔜 ทำต่อ (ถัดไป)
1. bundle ฟอนต์ OFL สำหรับ PDF (deploy Linux) + review pip-audit runtime advisories เมื่อมี fix
2. รอ HR: สูตร attendance (เต็ม 40), เนื้อหา `desc_1..5`, เกณฑ์ probation ต่อ checkpoint
3. (พบระหว่างทาง ยังไม่ทำ) `GET /api/evaluations` และ `GET /api/evaluations/{id}` ไม่มีการกรอง "ใครควรเห็นใบไหน" เลย — พนักงานทั่วไปในบริษัทเดียวกัน "อ่าน" คะแนนใบของคนอื่นได้หมดถ้ารู้/เดา id (เขียน/อนุมัติถูกป้องกันครบแล้ว แต่การ "ดู" ยังกว้างกว่าที่ควร) ควรพิจารณาว่าใครควรมองเห็นใบประเมินของใครได้บ้าง

## 🖥️ วิธีรัน local (สำหรับ session ถัดไป)
```
npx supabase start          # Postgres @54322, API @54321, Studio @54323
# รัน RLS test (DB layer):
cat supabase/tests/rls_negative_test.sql | docker exec -i supabase_db_app_Evaluation_System psql -U postgres -d postgres -v ON_ERROR_STOP=1
# รัน backend API:
cd backend && cp .env.example .env   # (ค่า local ใช้ได้เลย; SUPABASE_URL=http://localhost:54321)
py -3.9 -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # ถ้า greenlet build ล้ม: pip install greenlet==3.1.1 ก่อน
.venv/Scripts/python -m uvicorn app.main:app --port 8000
# รัน API test 7/7 (อีก terminal): bash backend/tests/test_api.sh
npx supabase stop           # ตอนเลิกงาน
```

## 🔒 การตัดสินใจที่ล็อกแล้ว (อย่าเปลี่ยนโดยไม่คุย)
| หัวข้อ | ค่าที่เลือก |
|---|---|
| Tenant model | SaaS multi-tenant, tenant = `companies`, isolate ด้วย company_id + RLS |
| Infra/Auth | Supabase (Auth + Postgres + RLS) |
| Criteria | BARS template-driven; master default + clone ต่อ tenant; ไม่ hardcode |
| Phase 1 scope | DB + auth + RBAC + criteria foundation; **ไม่ทำ** approval workflow |
| Roles | super_admin, hr_admin, manager, employee (ต่อเติมได้) |
| Login Phase 1 (default) | HR/Admin + หัวหน้า ก่อน (พนักงานทั่วไปเป็น record) |
| Security | OWASP Top 10 by design (docs/SECURITY.md) |
| Audit | append-only audit_logs + structured app logs (docs/LOGGING_AND_AUDIT.md) |
| Supabase env | Local (CLI/Docker) สำหรับ dev + Cloud แยกสำหรับ staging/prod |
| DB access | SQLAlchemy + asyncpg (async) + supabase-py เฉพาะ Auth admin |
| Frontend pkg manager | npm |

## ❓ คำถามค้าง (รอผู้ใช้ยืนยัน — ไม่บล็อกงาน)
- Supabase local หรือ cloud สำหรับรันจริงรอบแรก? (ผมออกแบบให้ local ก่อน)
- Criteria scope ต่อ tenant, login scope, role set — ใช้ default ที่เสนอไว้ (แก้ได้)

## 🧭 จุดอ้างอิงเร็ว
- แผนละเอียด: `docs/PHASE_1_PLAN.md`
- schema: `docs/DATABASE_SCHEMA.md`
- กติกา/DoD: `CLAUDE.md`

## 📌 ค้าง/ความเสี่ยงที่ต้องจำ
- สูตรคะแนน attendance (max 40) ยังไม่รู้ — ต้องถาม HR (Phase 2)
- BARS anchors (desc_1..5) ยังเป็น placeholder — HR ต้องเติมเนื้อหาจริง
- ยืนยันว่า "500 คน" เป็นต่อ tenant หรือรวมทุก tenant (กระทบ capacity planning)
