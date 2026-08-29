# Project Status — E-Appraisal  *(อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง)*

> เอกสารมีชีวิต (living doc) — **อัปเดตทุกครั้งที่จบงาน** เพื่อส่งต่อ session ถัดไป

**อัปเดตล่าสุด:** 2026-08-28
**Phase ปัจจุบัน:** Phase 1 — Foundation (+ pilot deployment ขึ้น production จริงแล้ว — ดู [DEPLOYMENT_PILOT.md](DEPLOYMENT_PILOT.md))
**สเต็ปที่กำลังทำ:** Phase 1–3 + admin tooling + role-based UI + read-visibility + BARS anchors + ระบบ attendance + bundle ฟอนต์ OFL + export Excel + หน้า HR ปรับสูตร attendance + หน้าเปรียบเทียบผลประเมิน + อัปเกรด Python 3.9→3.11 + การรับทราบของพนักงานแบบกระดาษ + ย้ายจุดรับทราบเข้าไปในสายอนุมัติ + **ลืมรหัสผ่าน/SMTP** + **นำทาง (nav bar) เดียวทุกหน้า + badge ผู้ใช้ปัจจุบัน/บริษัท/สาขา** + **multi-company account switching** + **frontend cold-start retry** + **super_admin ดูพนักงาน/user แยกตามบริษัท** + **ปิดใช้งานบัญชี login รายคน** + **สร้างใบประเมิน: แก้บั๊ก template ข้ามบริษัท + company_id ผิด** + **แก้ label "ระดับ" กำกวม** + **แก้ AppHeader ล้นจอมือถือ** + **แก้วรรณยุกต์ซ้อนสระเพี้ยนใน PDF** — ครบทุกอย่างนี้ deploy ขึ้น production แล้ว, รอ HR ตรวจ/ปรับถ้อยคำ BARS + ยืนยันสูตร attendance
**ล่าสุด:** **ถอด role เดียวออกโดยไม่ปิดทั้งบัญชี** (ใช้ร่วมกับ `app_leave_approve` เพราะ user_roles เป็นตารางกลาง) — เสร็จ+พิสูจน์ local แล้ว, pytest 131/131, **deploy ขึ้น production แล้ว** (commit `e873540`, ยืนยัน route จริงบน `e-appraisal-api.onrender.com` ตอบ 401 ไม่ใช่ 404 หลัง push)

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

- **Read visibility + role GM/MD เสร็จ+พิสูจน์** →
  - **นโยบายการมองเห็นใบประเมิน (ปิดช่องโหว่ที่บันทึกไว้รอบก่อน):** ผู้ถูกประเมินเห็นเฉพาะของตัวเอง · สายบังคับบัญชา (supervisor_id/manager_id ของ subject) เห็นของลูกน้อง · HR + GM/MD เห็นทั้ง tenant · คนอื่นในบริษัทเดียวกันที่ไม่เกี่ยวข้อง → 404 (ไม่รั่วแม้แต่การมองเห็น). กรองใน `list_all` (SQL WHERE) + `_load_viewable` (GET detail/pdf → 404 ถ้าไม่มีสิทธิ์). `GET /api/me` เพิ่ม employee_id ไปแล้วรอบก่อน ใช้เช็คฝั่ง UI
  - **Role `gm` (General Manager) ใหม่** — `0014_gm_role.sql`; สิทธิเทียบเท่า MD ทุกที่ที่เช็ค md → `_is_md_or_gm()` (approve/return ชั้น MD, inbox, visibility). approval record ยังใช้ step='md' (stage เดียวกัน), actor_id บันทึกว่าใครทำ. Frontend: `INVITE_ROLES` + `ROLE_LABEL` เพิ่ม gm, ป้าย "รออนุมัติ (GM/MD)", isMd รวม gm
  - พิสูจน์: pytest **56/56** (+`test_gm_approves_at_md_stage`, +`test_read_visibility`: subject/chain/HR/GM/MD เห็น, คนนอกสาย list ว่าง+detail 404+pdf 404) + browser จริง (login GM→เห็น inbox "รออนุมัติ (GM/MD)"→อนุมัติได้→สถานะ MD อนุมัติ; login คนนอกสาย→list "ยังไม่มีใบประเมิน"+เข้า detail ตรง id ได้ 404)

- **BARS anchors (desc_1..5) เสร็จ+พิสูจน์** →
  - **เนื้อหา BARS 42 ตัวชี้วัด × 5 ระดับ** เขียนเป็นชุดตั้งต้น (HR ปรับถ้อยคำได้) ต่อท้าย `supabase/seed.sql` — UPDATE คีย์ด้วย (category_order, item_order) ลง master template (company_id null) ทั้ง operational+supervisor. Verify: 70/70 master items มี desc ครบ
  - **`0015_bars_snapshot.sql`**: เพิ่ม `desc_1..5` เข้า `evaluation_items` (snapshot) + แก้ `app.snapshot_evaluation_items` ให้ copy anchors มาตอนสร้างใบ (ใบเก่าเป็น NULL) — เพราะ desc อยู่บน template แต่การให้คะแนนอ่านจาก snapshot
  - `get_detail` ดึง `desc_1..5` ไปด้วย; `EvalItem` type + `EvaluationDetail.tsx` แสดง `<details>` "เกณฑ์การให้คะแนน (BARS)" พับเก็บได้ต่อ item (5→1) + ไฮไลต์ระดับที่เลือก (score .5 คร่อม 2 ระดับ)
  - `pdf.py` เพิ่มคำบรรยาย "ระดับ N: <anchor>" ใต้ชื่อตัวชี้วัดที่ให้คะแนน → ใบพิมพ์อธิบายตัวเองได้
  - พิสูจน์: pytest 56/56 (+assert desc snapshot ไหลถึง get_detail) + browser (สร้างใบ→เกณฑ์ BARS แสดง 5 ระดับ, เลือก 3.5→ไฮไลต์ระดับ 3+4) + PDF จริงมีบรรทัด "ระดับ N:" ทุกข้อ

## 🔜 ทำต่อ (ถัดไป)
0. **(เฟสถัดไป — ตัดสินใจแล้วว่าไม่ทำตอนนี้) การรับทราบทางอีเมล (magic link)** — ทำแบบกระดาษก่อนตามที่ตกลง (ดูหัวข้อ "ทำไปแล้ว" ด้านล่าง ว่าทำอะไรไปแล้วบ้าง) เมื่อจะกลับมาทำต่อ:
   - **ตัดสินใจไว้ล่วงหน้าแล้ว** (ยังไม่เปลี่ยน แค่ยังไม่เริ่ม): ใช้ magic link ทางอีเมล (ไม่ต้องให้พนักงานทุกคนมีบัญชี/รหัสผ่าน) ส่งผ่าน **Gmail ธรรมดา** (ไม่ใช่ Workspace) — ต้อง**แยกบัญชี Gmail ใหม่ต่างหากจากบัญชีที่ส่งสลิปเงินเดือน** (กันบัญชีโดนจำกัดจากการยิงเมลพร้อมกัน ~300 คน/บริษัทแล้วลากระบบสลิปพังไปด้วย), เปิด 2-Step Verification + สร้าง App Password
   - ยังไม่ทำ: `POST /api/evaluations/{id}/acknowledge` แบบ electronic (ตอนนี้มีแต่ `acknowledge-paper` สำหรับ HR บันทึกแทน — ดูด้านล่าง), บริการส่งอีเมล, หน้าพนักงานกดรับทราบเอง (ตอนนี้พนักงานทั่วไปยังไม่มีบัญชีล็อกอินตามการตัดสินใจ Phase 1 เดิม)
   - ยังไม่ตัดสินใจ: จะเพิ่ม second-factor ตอนกดรับทราบไหม (เช่นเลขบัตร ปชช. 4 ตัวท้าย) — ถ้าเอาต้องเพิ่มข้อมูลอ่อนไหวเข้าระบบอีก (PDPA)
1. รอ HR: **เข้าไปตั้งค่าสูตร attendance ที่หน้า `/people` ตามนโยบายบริษัทจริง** (ตอนนี้ยังเป็นค่าเริ่มต้น 40/4/1/0.5/1 จนกว่า HR จะปรับ), ตรวจ/ปรับถ้อยคำ BARS anchors, เกณฑ์ probation ต่อ checkpoint — ส่งไฟล์ `exports/evaluation-criteria-bars.docx` ให้ตรวจแล้ว
2. (ไอเดียถัดไป ยังไม่เริ่ม) ตัวกรอง export ตาม cycle_id ถ้าฟีเจอร์ evaluation_cycles เริ่มมีการใช้งานจริง (ตอนนี้ cycle_id ยังไม่มี UI สร้าง/เลือก cycle เลย)
3. **(ไอเดียถัดไป ยังไม่เริ่ม) branch-level access control** — ตอนนี้ "สาขา" เป็นแค่ข้อมูล descriptive บน employees, ไม่ใช่ขอบเขตสิทธิ์ (ทุกคนที่มี role ระดับบริษัทเห็นทุกสาขาในบริษัทเดียวกันหมด) ถ้าจะจำกัดสิทธิ์ตามสาขาจริง ต้องเพิ่มมิติ access-control ใหม่ทั้งหมด (RLS ระดับสาขา ไม่ใช่แค่ระดับบริษัท) — เป็นฟีเจอร์แยกต่างหาก ไม่ใช่ส่วนขยายของ multi-company switching ที่ทำไปแล้ว
4. **(ตัดสินใจรอ) ขยาย audit log ให้ครอบคลุม "sensitive read" กว้างขึ้น** — ตอนนี้ audit ครอบ mutation ทุกจุด + export (PDF/Excel) + compare แล้ว แต่ยังไม่ครอบการเปิดดูใบประเมิน/พนักงานแบบเจาะจงทีละรายการ (`GET /api/evaluations/{id}`, `GET /api/employees/{id}`) ตามที่ `docs/LOGGING_AND_AUDIT.md` ระบุไว้เป็นเป้าหมาย Phase 1 (`view_employee`) — ยังไม่ทำเพราะจะเพิ่มปริมาณ write เข้า audit_logs ทุก GET request อย่างมีนัยสำคัญ ควรคุยกับทีมก่อนว่าต้องการระดับละเอียดแค่ไหน (ทุกครั้งที่เปิดดู vs. เฉพาะการ export/เปรียบเทียบแบบที่ทำไปแล้ว)

## ✅ ทำไปแล้ว (ต่อ)

- **ระบบ attendance: HR กรอกข้อมูลดิบ + auto-calc + override + bulk import เสร็จ+พิสูจน์** →
  - **เปลี่ยนสถาปัตยกรรม**: attendance เดิมให้หัวหน้าพิมพ์คะแนน 0–40 เองใน `save_scores` — เปลี่ยนเป็น **HR เป็นเจ้าของข้อมูล** หัวหน้าเห็นได้อย่างเดียว (read-only) ป้องกันหัวหน้าพิมพ์ทับข้อมูลที่ HR กรอกไว้
  - `0016_attendance_override.sql`: เพิ่ม `attendance_score_overridden` ใน `evaluation_attendance` — เก็บ "คะแนนเดียว + flag" ไม่แยก computed_score ต่างหาก (ออกแบบให้ง่ายที่สุดที่ยังตอบโจทย์ได้)
  - `services/evaluations.compute_attendance_score`: **สูตรตั้งต้น (ค่าเริ่มต้น ปรับได้ รอ HR ยืนยัน)**: 40 − 4×วันขาด − 1×วันลากิจ − 0.5×วันลาป่วย − 1×ครั้งมาสาย, floor ที่ 0
  - `PUT /api/evaluations/{id}/attendance` (HR-only ผ่าน `require_roles`) — บันทึกข้อมูลดิบ + คำนวณคะแนนอัตโนมัติ, หรือ HR ระบุ `attendance_score` เพื่อ override เอง — **override อยู่รอด** แม้แก้ข้อมูลดิบซ้ำในภายหลัง (ไม่คำนวณทับโดยไม่ตั้งใจ) จนกว่าจะส่ง `clear_override: true` เพื่อกลับไปใช้สูตร. บล็อกแก้ไขหลัง `finalized` (409)
  - **Bulk import**: `services/attendance_import.py` (mirror `employee_import.py`) — จับคู่แถวด้วย emp_code กับใบประเมินที่ยังไม่ปิดของพนักงานคนนั้น (ต้องมีอยู่แล้ว 1 ใบเท่านั้น ไม่งั้น error ต่อแถว), **เคารพ override เดิม** (ข้ามแถวที่ HR ปรับเองไว้แล้ว นับใน `skipped_overridden`), SAVEPOINT ต่อแถว. Routes: `GET /api/evaluations/attendance-import-template`, `POST /api/evaluations/attendance-import` (ทั้งคู่ literal path ประกาศก่อน `/{eval_id}` กัน path collision เหมือน `/inbox`)
  - Frontend: `EvaluationDetail.tsx` — หัวหน้าเห็นคะแนน+รายละเอียดการมา-ลาแบบ read-only เท่านั้น (ไม่มีช่องกรอกอีกต่อไป); ฟอร์มแก้ไข (ลาป่วย/ลากิจ/สาย/ขาดงาน + ช่อง override) แสดงเฉพาะ HR และเฉพาะตอนยังไม่ finalized. `People.tsx` เพิ่ม section นำเข้า attendance จากไฟล์ (ดาวน์โหลดเทมเพลต + อัปโหลด + สรุปผล updated/skipped_overridden/errors)
  - พิสูจน์: pytest 10 เคสใหม่ (`test_attendance.py`: หัวหน้าตั้งค่าไม่ได้ (403), auto-compute ถูกสูตร, override อยู่รอดการแก้ข้อมูลดิบซ้ำ + clear_override กลับสูตรได้, ยอดรวมคำนวณถูก, บล็อกหลัง finalize (409), bulk import อัปเดตถูกใบ, bulk import ข้ามใบที่ override ไว้, bulk import แถวไม่พบใบประเมิน = error, RBAC) + แก้ 2 เคสเดิมที่เคยส่ง attendance ผ่าน `save_scores` ให้ใช้ endpoint ใหม่แทน — pytest 66/66 + browser จริง (login หัวหน้า → เห็น "คะแนน: — / 40" อย่างเดียว ไม่มีช่องกรอก; login HR → กรอกลาป่วย 1 + สาย 2 ครั้ง → บันทึก → คะแนนคำนวณเป็น 37.5 ถูกต้อง ยอดรวมอัปเดตทันที)

- **Bundle ฟอนต์ OFL (Sarabun) สำหรับ PDF เสร็จ+พิสูจน์** →
  - เดิม `pdf.py` พึ่งฟอนต์ที่ติดตั้งในเครื่อง (Leelawadee UI บน Windows / Sarabun-Tlwg บน Linux) — ถ้า deploy บน container ที่ไม่มีฟอนต์ไทยติดตั้งจะ export PDF ไม่ได้เลย (`RuntimeError: No Thai TTF font found`)
  - ดาวน์โหลด `Sarabun-Regular.ttf` + `OFL.txt` (สัญญาอนุญาต) จาก Google Fonts (`google/fonts` repo, OFL license) ไปไว้ที่ `backend/app/assets/fonts/` — เป็นไฟล์ในโปรเจกต์ ไม่ต้องพึ่งฟอนต์ระบบอีกต่อไป
  - `pdf.py`: เพิ่ม `_BUNDLED_FONT` (path แบบ relative ผ่าน `Path(__file__)` ใช้ได้ทุก deployment) เป็นลำดับที่ 2 ใน `_FONT_CANDIDATES` (รองจาก `PDF_FONT_PATH` env ที่ยัง override ได้ถ้าต้องการฟอนต์อื่น) ก่อนฟอนต์ระบบ Windows/Linux ที่เหลือไว้เป็น fallback สุดท้าย
  - พิสูจน์: เช็คว่า `pdfmetrics.getFont` โหลดจากไฟล์ที่ bundle จริง (ไม่ใช่ฟอนต์ระบบ) + สร้างใบประเมินจริงผ่าน API แล้ว render PDF เป็นภาพ (ใช้ PyMuPDF ชั่วคราวเพื่อตรวจสอบเท่านั้น ไม่ได้เพิ่มเป็น dependency ถาวร) — ตัวอักษรไทย สระ วรรณยุกต์ถูกต้องครบถ้วน, pytest 66/66 ผ่าน

- **Export คะแนนผลประเมินเป็น Excel เสร็จ+พิสูจน์** →
  - `services/excel_export.py` (openpyxl) — 2 ชีต: **"สรุป"** 1 แถวต่อ 1 ใบประเมิน (รหัสพนักงาน/ชื่อ/ตำแหน่ง/สาขา/ผู้ประเมิน/ชนิด/สถานะ/คะแนนประเมิน/คะแนนเต็ม/คะแนนมา-ลา/คะแนนรวม/ร้อยละ/วันที่สร้าง/วันที่ปิดใบ) เหมาะทำ pivot table, **"รายละเอียด"** 1 แถวต่อ 1 item ต่อใบ (สำหรับตรวจดูคะแนนรายข้อ) — ตัดสินใจแยก 2 ชีตแทนอัดทุก item เป็นคอลัมน์เดียวกัน เพราะจำนวน/รายชื่อ criteria items ปรับได้ต่อ tenant คอลัมน์แบบ item-per-column จะเลื่อนไม่คงที่
  - **Visibility scope เดียวกับ `list_all`/`view_detail` เป๊ะ** — reuse `_sees_all_evaluations`/`_actor_employee_id` ตรง ๆ ไม่เขียนกฎใหม่ซ้ำ (ผู้ถูกประเมินเห็นแถวตัวเอง, สายบังคับบัญชาเห็นลูกน้อง, HR/GM/MD เห็นทั้ง tenant) — export จะไม่มีแถวไหนที่ผู้เรียกดูทีละใบไม่ได้อยู่แล้ว
  - Route: `GET /api/evaluations/export` (literal path ประกาศก่อน `/{eval_id}` เหมือน `/inbox`/`/attendance-import`) — ไม่จำกัด role พิเศษเพราะ visibility filter ข้างในจัดการสิทธิ์ให้แล้ว (เหมือน list endpoint เดิม)
  - Frontend: ปุ่ม "ดาวน์โหลด Excel" บนหน้า `Evaluations.tsx` (ใช้ `apiDownload` แบบเดียวกับปุ่ม PDF)
  - พิสูจน์: pytest 3 เคสใหม่ (`test_excel_export.py`: subject/chain/HR เห็นแถวตัวเอง+คนที่เกี่ยวข้อง, คนนอกสายไม่เห็นข้อมูลคนอื่น, ชีตรายละเอียดมีครบทุก item ตามจำนวนจริง) + สร้างข้อมูลตัวอย่างจริงผ่าน API (3 พนักงาน คะแนนต่างกัน + 1 คนมี HR override attendance) แล้วเปิดไฟล์ตรวจ: หัวคอลัมน์ภาษาไทยถูกต้อง, ตัวเลขคำนวณตรง (attendance override 39.5/40 → total 151.5/180 = 84.17% ตรงกับที่ตั้งไว้), ชีตรายละเอียดมี 84 แถว = 3 คน × 28 ข้อ ถูกต้อง

- **HR ปรับสูตรคะแนน attendance เองผ่าน UI + ตัวกรองบน export Excel เสร็จ+พิสูจน์** →
  - **`0017_attendance_formula_settings.sql`**: ตาราง `company_attendance_formula` (company_id PK, full_score/coef_absent/coef_personal/coef_sick/coef_late, RLS ครบ 4 policy ตาม pattern มาตรฐาน + **grant select/insert/update/delete ให้ role authenticated ชัดเจน** — จุดพลาดที่เจอระหว่างทำ: migration 0006 ที่ grant ให้ตารางทั้งหมดใน schema public รันไปแล้วก่อนตารางนี้จะถูกสร้าง ไม่ครอบตารางใหม่ย้อนหลัง ต้อง grant เองในตารางที่สร้างทีหลังเสมอ (เหมือน pattern ที่ 0011/0012 ทำไว้แล้ว)
  - `services/attendance_formula.py`: `get_formula` (คืนค่า default ถ้ายังไม่มีแถวตั้งค่า — เพื่อไม่ให้ tenant เก่าพังถ้าไม่เคยเข้าไปตั้งค่า), `compute_score` (แยกจากการ query เพื่อทดสอบง่าย), `set_formula` (upsert + กันค่าติดลบ + audit log). ย้าย `compute_attendance_score` เดิมใน `services/evaluations.py` มาไว้ที่นี่ทั้งหมด แล้วให้ `set_attendance`/`attendance_import.py` ดึงสูตรของ tenant ตัวเองมาใช้แทนค่า hardcode
  - Routes: `GET/PUT /api/settings/attendance-formula` (hr_admin only). Frontend: section ใหม่ในหน้า `People.tsx` ("สูตรคำนวณคะแนนการมา-ลา") ให้กรอกตัวเลข 5 ช่องแล้วบันทึก
  - **ตัวกรอง export Excel**: `GET /api/evaluations/export?status=&date_from=&date_to=` — จุดที่ต้องระวัง: `text()` ของ SQLAlchemy ตีความ `::type` cast ชนกับ syntax bind param `:name` ทำให้ syntax error ต้องใช้ `cast(:param as type)` แทน; และต้อง cast type explicit เพราะ asyncpg ไม่สามารถ infer type ของ NULL param ได้เอง (`AmbiguousParameterError`). Frontend: เพิ่ม dropdown สถานะ + ช่วงวันที่เหนือปุ่มดาวน์โหลดใน `Evaluations.tsx`
  - พิสูจน์: pytest 5 เคสใหม่ (`test_attendance_formula.py`: ค่า default ตอนยังไม่ตั้งค่า, เฉพาะ HR แก้ได้ (403), กันค่าติดลบ (422), บันทึกแล้วมีผลจริงกับ `set_attendance` ที่ตามมา, **negative test cross-tenant** — สูตรที่ tenant A ตั้งไม่รั่วไป tenant B) + `test_excel_export.py` เพิ่ม 2 เคส (filter สถานะ, filter ช่วงวันที่) — pytest 76/76 + browser จริง (login HR → แก้ไข "ลด/วันลาป่วย" จาก 0.5 เป็น 2 → บันทึก → reload หน้าใหม่ทั้งหมด → ค่ายังเป็น 2 ยืนยันว่าบันทึกลง DB จริงไม่ใช่แค่ state ฝั่ง client; หน้า export มีตัวกรองสถานะ+วันที่ครบ กดดาวน์โหลดได้ 200)

- **หน้าเปรียบเทียบผลประเมิน (2 โหมด) เสร็จ+พิสูจน์** →
  - **สถาปัตยกรรม**: ทั้ง (ก) เทียบพนักงานหลายคนในรอบเดียวกัน และ (ข) เทียบพนักงานคนเดียวกันข้ามหลายรอบ ใช้ **endpoint เดียวกัน** — `GET /api/evaluations/compare?ids=&ids=...` (เลือกได้ 2-5 ใบ) เพราะทั้งสองแบบคือ "เลือกใบประเมิน 2-5 ใบมา pivot คะแนนเทียบกัน" ต่างกันแค่ผู้ใช้เลือกใบของคนเดียวกันหรือหลายคน — ไม่ต้องแยกหน้า/endpoint
  - **บังคับสิทธิ์แบบเดียวกับเปิดใบทีละใบเป๊ะ**: `services/compare.py` เรียก `view_detail()` (ตัวเดียวกับ `GET /{eval_id}`) ต่อใบ — ถ้าใบไหนอยู่นอกสายบังคับบัญชาของผู้เรียกและไม่ใช่ HR/GM/MD จะ 404 ทั้งการเปรียบเทียบทันที (ไม่ใช่แค่ซ่อนบางคอลัมน์) ตอบโจทย์ที่ระบุไว้ชัดว่า "ข้ามสายบังคับบัญชาไม่ได้"
  - **จับคู่แถวคะแนนด้วย item_name** (ไม่ใช่ id) เพราะเทมเพลต operational/supervisor มีจำนวน/รายชื่อ item ต่างกัน — เรียงตามลำดับที่พบก่อนในใบแรกที่มี item นั้น
  - เพิ่ม audit action `evaluations_compared` เข้าไปในระบบ audit log **เดียวกับที่ทุกฟีเจอร์ในระบบใช้อยู่แล้ว** (ดูหัวข้อ "audit log ครอบคลุมทั้งโปรแกรม" ด้านล่าง — ไม่ใช่ log แยกเฉพาะของหน้านี้)
  - Route: `GET /api/evaluations/compare` (literal path ก่อน `/{eval_id}`). Frontend: หน้าใหม่ `Compare.tsx` (route `/evaluations/compare`, ลิงก์จากหน้า `Evaluations.tsx`) — ตารางเลือกใบประเมิน (checkbox, จำกัด 2-5) จากรายการที่มองเห็นอยู่แล้ว (ใช้สิทธิ์เดียวกับ list เดิม) แล้วแสดงผลเป็นตารางเทียบข้าง (คอลัมน์ = ใบประเมิน, แถวบนสุด = คะแนนรวม/มา-ลา/ร้อยละ, แถวล่าง = คะแนนรายข้อ 28-42 ข้อ)
  - พิสูจน์: pytest 5 เคสใหม่ (`test_compare.py`: บังคับเลือก 2-5 ใบ, โหมด ข (คนเดียวข้ามเวลา) คะแนนตรงตามที่บันทึก, โหมด ก (สองคนรอบเดียวกัน) แสดงครบ, **บังคับสิทธิ์ 404 ถ้าเปิดใบนอกสาย**, มี audit log จริงในตาราง) — pytest 81/81 + browser จริง (login HR เลือก 2 ใบของพนักงานคนละคน → เปรียบเทียบ → เห็นตาราง 28 แถวตรงกับคะแนนที่ให้ไว้ 4 กับ 3, คะแนนรวม 112/140 (62.22%) กับ 84/140 (46.67%) ถูกต้อง)

- **ยืนยัน+เอกสาร: audit log ครอบคลุมการเปลี่ยนแปลงข้อมูลทั้งโปรแกรม (ไม่ใช่แค่ฟีเจอร์เดียว)** →
  - **แก้ไขความเข้าใจผิดในเอกสารรอบก่อน** ที่เขียนราวกับว่า audit log เป็นสิ่งที่เพิ่งเพิ่มเฉพาะหน้าเปรียบเทียบ — จริง ๆ แล้ว `write_audit()` (`services/audit.py`) ถูกเรียกจากทุก mutation endpoint ในระบบมาตั้งแต่ Phase 1 ตามกติกาใน CLAUDE.md ("Audit ทุกการเปลี่ยนข้อมูลสำคัญ") และ `docs/LOGGING_AND_AUDIT.md`
  - **รายการ action ที่มี audit log ครบทุกจุด mutation ในระบบปัจจุบัน** (ตรวจสอบด้วย `grep -rn write_audit app/`):
    - Tenant/provisioning: `tenant_created`, `tenant_status_changed`, `user_invited` (ทั้ง super_admin invite และ hr_admin self-invite ใช้ฟังก์ชันเดียวกัน)
    - Employee/branch: `create`/`update` (employees), `create`/`update` (branches), `employees_imported` (bulk CSV)
    - Evaluation lifecycle: `evaluation_created`, `score_saved`, `evaluation_submitted`, `evaluation_approved`, `evaluation_returned`, `evaluation_finalized`
    - Attendance: `attendance_updated`, `attendance_imported`, `attendance_formula_updated`
    - Export/เปรียบเทียบ (sensitive read ไม่ใช่ mutation แต่ audit ไว้เพราะเป็นการเข้าถึงข้อมูลจำนวนมากพร้อมกัน): `evaluation_exported` (PDF), `evaluations_exported` (Excel), `evaluations_compared`
  - แต่ละแถวบันทึก `company_id, actor_profile_id, action, entity_type, entity_id, before/after (jsonb), created_at` — append-only (RLS ไม่มี policy UPDATE/DELETE), tenant-scoped, อยู่ใน transaction เดียวกับการเปลี่ยนแปลงจริง (สำเร็จ = มี audit, ล้มเหลว = rollback ทั้งคู่) ตรวจสอบย้อนหลังได้ว่าใครทำอะไรกับข้อมูลไหนเมื่อไร
  - **ยังไม่ครอบ** (ตัดสินใจรอ ดูหัวข้อ "ทำต่อ"): การเปิดดูข้อมูลทีละรายการแบบ read-only ธรรมดา (`GET /api/evaluations/{id}`, `GET /api/employees/{id}`) — ยังไม่ใช่ mutation จึงยังไม่มี audit log ต้องตัดสินใจร่วมกันก่อนว่าต้องการระดับละเอียดแค่ไหน

- **อัปเกรด Python 3.9 → 3.11 + ปิดช่องโหว่ dependency ทั้งหมด เสร็จ+พิสูจน์** →
  - **สาเหตุ**: `pip-audit` เคยขึ้น 35 รายการที่ "no-fix-available" (starlette/urllib3/python-multipart ฯลฯ) — ตรวจแล้วพบว่าเวอร์ชันที่แก้ไขจริง ๆ **มีอยู่แล้ว** แต่ต้องการ Python ≥3.10 ทั้งหมด (`pip install --dry-run` ยืนยัน `Requires-Python >=3.10`) ส่วนโปรเจกต์ตรึงไว้ที่ 3.9 มาตั้งแต่ Phase 1 เพราะตอนนั้น greenlet ไม่มี wheel สำหรับ cp39 บนเครื่องที่ไม่มี MSVC
  - ผู้ใช้ติดตั้ง Python 3.11.9 เพิ่มในเครื่อง (ไม่กระทบ Python 3.9 เดิม) แล้วสร้าง venv ใหม่จากนั้น — เลือก 3.11 แทนที่จะกระโดดไป 3.14 (เวอร์ชันเดียวที่มีอยู่ก่อนหน้า) เพราะ 3.14 ใหม่เกินไป เสี่ยงที่ C extension อย่าง greenlet/asyncpg จะยังไม่มี wheel รองรับ
  - **ผลพลอยได้ที่สำคัญกว่าที่ตั้งใจ**: ระหว่างไล่ดู dependency พบว่า `python-jose[cryptography]` ที่อยู่ใน `requirements.txt` มาตั้งแต่ Phase 1 **ไม่ได้ถูก import ใช้งานที่ไหนเลย** (โค้ดจริงใช้ `pyjwt[crypto]` ตัวเดียวสำหรับ verify JWT ผ่าน JWKS/ES256 ใน `core/security.py`) — `python-jose` ดึง `ecdsa` มาเป็น transitive dependency ซึ่งเป็นตัวที่เหลืออยู่ตัวเดียวใน pip-audit หลังอัปเกรด (ไม่มี fix version เพราะเป็นช่องโหว่เชิง timing-attack ที่ maintainer ประกาศจะไม่แก้ในเวอร์ชัน pure-Python) **ลบ `python-jose` ออกทำให้ `ecdsa` หายไปทั้งเส้น** ไม่ต้อง "ยอมรับความเสี่ยง" ไว้เฉย ๆ
  - อัปเดต `setuptools` ในตัว venv เป็น `>=83.0.0` ด้วย (เป็น dev-tooling ไม่ใช่ runtime แต่แก้ง่าย ไม่มีเหตุผลจะปล่อยค้าง)
  - ผลลัพธ์: `pip-audit` จาก 35 รายการ → **0 known vulnerabilities**
  - พิสูจน์: สร้าง venv ใหม่จาก `requirements.txt` ที่แก้แล้ว รันเซิร์ฟเวอร์จริงขึ้นสำเร็จ (`/docs` 200), รัน pytest เต็มชุด **81/81 ผ่าน** ทั้งบน venv ใหม่ก่อน rename และหลัง rename เป็น `.venv` (กันกรณี path-dependent อะไรพลาด), `npm run build` ฝั่ง frontend ผ่าน (ไม่กระทบเพราะเป็นคนละ stack), ลบ venv เก่า (Python 3.9) ทิ้งหลังยืนยันว่าไม่ต้องใช้แล้ว

- **Pilot deployment ขึ้น production จริง (Supabase Cloud + Render + Vercel) เสร็จ+พิสูจน์** — รายละเอียดครบใน [DEPLOYMENT_PILOT.md](DEPLOYMENT_PILOT.md) รวมปัญหาที่เจอจริงระหว่างทำ (Render ไม่มี field `pythonVersion` ต้องใช้ env var แทน, direct DB connection เป็น IPv6-only ต้องเปลี่ยนไปใช้ Supavisor pooler, username ของ pooler ต้องมี project ref ต่อท้าย) →
  - Production URLs: backend `https://e-appraisal-api.onrender.com`, frontend `https://app-evaluation-system.vercel.app`, Supabase project ref `avznzakoxpjsgmrxjjgs`
  - สร้าง super_admin คนแรกของระบบจริงแล้ว (bootstrap ผ่าน SQL ตรง ๆ เพราะยังไม่มี super_admin คนไหนให้เรียก endpoint ปกติ — วิธีเดียวกับที่ `tests/conftest.py` ทำในเทส) — เก็บ credential ไว้กับผู้ใช้แล้ว ไม่บันทึกในเอกสารนี้
  - **สร้างบริษัททดลอง "บริษัท ทดลอง จำกัด" (`demo-co`) พร้อมข้อมูลตัวอย่างเต็มสาย** ผ่าน API จริง (ไม่ใช่ยัด DB ตรง ๆ) ไว้ demo/ทดสอบ: สายบังคับบัญชา 4 ระดับ (ผจก.แผนก → หัวหน้างาน → พนักงาน 2 คน) มีบัญชีล็อกอินครบทุก role (HR/dept_manager/manager/md), ใบประเมินตัวอย่าง 2 ใบคนละสถานะ (annual ที่ submit แล้วรอผจก.แผนกอนุมัติ, probation checkpoint 30 วันที่ยังเป็นร่างพร้อมให้คะแนนสด) — credential อยู่กับผู้ใช้ ไม่บันทึกในเอกสารนี้เช่นกัน

- **การรับทราบของพนักงานแบบกระดาษ (employee acknowledgement) — schema + PDF + endpoint + UI ครบวงจร เสร็จ+พิสูจน์** (ระบบอีเมล/electronic เลื่อนเป็นเฟสถัดไปตามที่ตกลงกับผู้ใช้) →
  - **ช่องว่างที่พบ**: ใบกระดาษเดิม (FMHR07) มีช่องลงนาม 5 ระดับ (พนักงาน→หัวหน้างาน→ผจก.แผนก→HR→MD) แต่ระบบเดิมทำแค่ 4 ช่องท้าย (สายอนุมัติ) — **ไม่มีการบันทึกว่าพนักงานเจ้าของใบเคยรับทราบผลเลย** ถือเป็นการถดถอยจากกระดาษเดิม ไม่ใช่แค่ฟีเจอร์ที่ยังไม่ทำ
  - **`0018_employee_acknowledgement.sql`**: เพิ่ม `employees.email` (unique partial index ต่อ tenant กันอีเมลซ้ำระหว่างพนักงาน 2 คน — เตรียมไว้สำหรับเฟสอีเมลถัดไป) + ตาราง `evaluation_acknowledgements` (append-only เหมือน `evaluation_approvals`/`audit_logs` — select+insert เท่านั้น ไม่มี policy update/delete)
  - **หลักการออกแบบสำคัญ — "รับทราบ" ≠ "เห็นด้วย"**: มี `decision` แยก 3 แบบ (`acknowledged`, `acknowledged_disagreed`, `refused`) และช่อง `comment` ให้พนักงานเขียนความเห็นแย้งได้โดยยังนับว่ารับทราบ — ตรงกับที่ใบกระดาษเดิมมีช่องความเห็นของผู้ถูกประเมินแยกจากช่องลงนาม (เหตุผล: ถ้าออกแบบให้ต้อง "เห็นด้วย" เท่านั้นถึงจะกดผ่านได้ จะมีปัญหาทันทีถ้าต้องใช้เป็นหลักฐานชั้นศาลแรงงาน)
  - รองรับ 2 วิธี (`method`) ในระดับ schema: **`electronic`** (สงวนไว้สำหรับเฟสอีเมล — ยังไม่มี endpoint ใช้งาน) และ **`paper`** (ใช้งานจริงตอนนี้: HR บันทึกแทนหลังเก็บลายเซ็นจริง มี `witness_name`/`attachment_path` สำหรับแนบสแกน) — `check` constraint กัน `decision='refused'` ผ่านทาง electronic (ปฏิเสธลงนามต้องมีพยานบันทึกแบบกระดาษเท่านั้น)
  - **`0019_acknowledgement_storage.sql`**: bucket ส่วนตัว `acknowledgement-scans` เก็บไฟล์สแกนลายเซ็น เส้นทางไฟล์ `{company_id}/{evaluation_id}.{ext}` ใช้ pattern เดียวกับตารางอื่น (`storage.foldername(name))[1] = company_id`) ใน RLS ของ `storage.objects` — append-only เช่นกัน (select+insert เท่านั้น)
  - **`services/storage.py`** ใหม่: เรียก Supabase Storage REST API ตรง ๆ ด้วย `service_role` key (pattern เดียวกับ `auth_admin.py` ที่มีอยู่แล้ว ไม่ใช้ supabase-py SDK) — `x-upsert: false` กันเขียนทับไฟล์เดิมโดยไม่ตั้งใจ (ไฟล์แนบคือหลักฐาน ห้ามแก้/ลบผ่าน API)
  - **`services/acknowledgement.py`** ใหม่: `record_paper_acknowledgement` (validate decision, บังคับ witness_name ถ้า `refused`, จำกัดไฟล์แนบ 15MB, บล็อกถ้ายังไม่ `finalized` (409), บล็อกบันทึกซ้ำ (409 — unique constraint), audit log) + `get_attachment` (ดาวน์โหลดไฟล์แนบ ผ่าน visibility check เดียวกับ `view_detail`)
  - Routes: `POST /api/evaluations/{id}/acknowledge-paper` (multipart form, hr_admin only), `GET /api/evaluations/{id}/acknowledgement-attachment` (สตรีมไฟล์กลับ)
  - **`pdf.py`**: เพิ่มตารางลายเซ็น 5 แถวตามลำดับกระดาษเดิมเป๊ะ (พนักงาน→หัวหน้างาน→ผจก.แผนก→ผจก.แผนกบุคคล→กรรมการผู้จัดการ) ดึงชื่อจริงจาก `evaluation_approvals`/`evaluation_acknowledgements` — ช่องที่ยังไม่มีบันทึกเว้นว่าง (ไม่ใช่ "—") เพื่อให้พิมพ์แล้วเซ็นสดได้ทันที, ถ้ารับทราบแล้วพิมพ์ "ลงนามในเอกสาร เมื่อ [วันที่]" + ความเห็นแย้ง (ถ้ามี) ต่อท้าย, ถ้าปฏิเสธลงนามพิมพ์ข้อความ + ชื่อพยาน
  - **`services/evaluations.list_all`**: เพิ่ม `acknowledgement_decision`/`acknowledgement_signed_at` (LEFT JOIN) — ทำให้หน้ารายการใบประเมินกลายเป็น "รายงานใครยังไม่รับทราบ" ได้ฟรี ไม่ต้องสร้าง endpoint/หน้าใหม่แยก
  - Frontend: `EvaluationDetail.tsx` เพิ่ม section "การรับทราบของพนักงาน" — ฟอร์มบันทึก (เลือกผล/วันที่/พยาน/ไฟล์แนบ/ความเห็นแย้ง) ถ้ายังไม่มีบันทึก, ทุกคนเห็นผลลัพธ์ถ้ามีแล้ว. `Evaluations.tsx` เพิ่มคอลัมน์ "การรับทราบ" ในตารางรายการ (รอรับทราบ/รับทราบแล้ว/รับทราบแล้ว (มีความเห็นแย้ง))
  - **ตัดสินใจกับผู้ใช้แล้ว**: ทำกระดาษก่อน อีเมล magic link ผ่าน Gmail (แยกบัญชีจากที่ส่งสลิปเงินเดือน) เป็นเฟสถัดไป — ดู "ทำต่อ" ด้านบน
  - พิสูจน์: pytest 9 เคสแรก (`test_acknowledgement.py`) + ดู bullet ถัดไปสำหรับเวอร์ชันที่ปรับจุดของ gate ในสายอนุมัติแล้ว + browser จริง (login HR → เลือก "รับทราบ (มีความเห็นแย้ง)" + กรอกความเห็น → บันทึก → เห็นผลอัปเดตทั้งในหน้ารายละเอียดและหน้ารายการใบประเมิน)

- **ย้ายจุดรับทราบของพนักงานเข้าไปในสายอนุมัติ (ตามคำขอผู้ใช้) เสร็จ+พิสูจน์** — เปลี่ยนจาก "รับทราบหลังปิดใบ (finalized)" เป็น **"ผจก.แผนกอนุมัติ → พนักงานเซ็นรับทราบ → GM/MD อนุมัติ → HR ปิดใบ"** ใกล้เคียงลำดับกระดาษเดิมมากขึ้น (MD เซ็นหลังสุด หลังทุกคนรวมถึงพนักงานเซ็นแล้ว) →
  - **`0020_acknowledgement_in_workflow.sql`**: เพิ่ม `superseded_at` ใน `evaluation_acknowledgements`, เปลี่ยน unique constraint จาก `unique(evaluation_id)` เป็น partial unique index `where superseded_at is null` (1 รายการ active ต่อใบ ประวัติเก่าเก็บไว้ได้หลายแถว), เพิ่มฟังก์ชัน `app.supersede_acknowledgement(eval_id, company_id)` (SECURITY DEFINER) — เป็นทางเดียวที่ "แก้" แถวได้ เพราะตารางยังคง append-only ตามดีไซน์เดิม (select+insert เท่านั้น ไม่มี update policy ทั่วไป)
  - **`services/evaluations.approve()`**: ขั้น GM/MD (`dept_approved` → `md_approved`) เพิ่มเช็ค `_has_active_acknowledgement()` ก่อนอนุมัติได้ — ไม่มีบันทึกรับทราบ = 409 (ปฏิเสธลงนามที่มีพยานก็นับว่า "มีบันทึก" แล้ว กันพนักงานไม่ยอมเซ็นทำให้ใบค้างตลอดกาล)
  - **`services/evaluations.return_to_draft()`**: ตีกลับจากสถานะไหนก็ตามจะเรียก `app.supersede_acknowledgement` เสมอ — คะแนนที่พนักงานเซ็นรับทราบไปกำลังจะถูกแก้ ลายเซ็นเดิมจึงหยุดมีผล (ไม่ลบทิ้ง เป็นหลักฐานของสิ่งที่เกิดขึ้น ณ ตอนนั้น) ต้องเก็บลายเซ็นใหม่หลัง resubmit
  - **`services/acknowledgement.py`**: เปลี่ยนเงื่อนไขสถานะจาก `finalized` เป็น `dept_approved`, เพิ่ม `_require_can_record()` — ผู้บันทึกได้คือ **หัวหน้างานผู้ประเมิน + ผจก.แผนกของพนักงานคนนั้น + HR** (ไม่ใช่ HR อย่างเดียวแล้ว กันคอขวด) แต่ **ไม่ใช่ GM/MD** (แยกมือผู้บันทึกกับผู้อนุมัติขั้นถัดไปออกจากกัน) และไม่ใช่ตัวพนักงานเอง — attachment path เติม uuid ต่อท้ายกันชนกันตอนเซ็นรอบสอง (`{company_id}/{eval_id}-{uuid8}.{ext}`)
  - Frontend: ปุ่ม "อนุมัติ" ของ GM/MD ที่สถานะ `dept_approved` เป็น `disabled` พร้อม tooltip ถ้ายังไม่มีการรับทราบ (กันกด 409 เสียเปล่า), ข้อความสถานะรอ ("รอพนักงานลงนามรับทราบ ก่อนส่งให้ GM/MD อนุมัติ"), section รับทราบย้ายมาโชว์ตั้งแต่ `dept_approved` เป็นต้นไป (ไม่ใช่แค่ `finalized`)
  - **ขอบเขต**: มีผลเฉพาะใบที่สร้างใหม่หลังจากนี้ตามที่ผู้ใช้ยืนยัน (ใบเก่า/ตัวอย่างที่มีอยู่ไม่ต้อง migrate ย้อนหลัง)
  - พิสูจน์: เขียน `test_acknowledgement.py` ใหม่ทั้งหมด (13 เคส: บันทึกได้เฉพาะช่วง `dept_approved`, ปฏิเสธ+พยานยังปลดล็อก MD ได้, MD ติด 409 ถ้ายังไม่รับทราบแล้วปลดล็อกหลังบันทึก, หัวหน้างาน/ผจก.แผนกบันทึกได้, GM/MD/ตัวพนักงานบันทึกไม่ได้ (403), ตีกลับแล้ว supersede ถูกต้อง+ประวัติเก่ายังอยู่ในตารางแค่ไม่ active, บันทึกรอบสองหลัง resubmit ได้, ไฟล์แนบ/list เดิมยังผ่าน) + แก้ helper `_acknowledge()` ใช้ร่วมใน `test_evaluation_lifecycle.py`/`test_attendance.py` ทุกจุดที่เดินผ่านขั้น MD — **pytest 94/94** + browser จริงครบ flow (dept อนุมัติ → login MD เห็นปุ่ม "อนุมัติ" เป็นสีจางกดไม่ได้พร้อม tooltip → login HR บันทึกรับทราบ → กลับไป login MD ปุ่มกดได้แล้ว กดอนุมัติสำเร็จ สถานะเปลี่ยนเป็น "MD อนุมัติ (รอ HR)") — **deploy ขึ้น production แล้ว** ยืนยันด้วย gate จริง (409→200) บน production เอง

- **ถอด role เดียวออก (revoke) จากบัญชี login — เสร็จ+พิสูจน์ (2026-08-28)**, มาจากคำถามผู้ใช้ผ่าน `app_leave_approve`: "โยกย้าย/ลาออกจัดการสิทธิ์ยังไง" → เจอว่ามีแค่ "ปิดใช้งานทั้งบัญชี" (`set_user_status`, ครอบคลุมลาออก) แต่ไม่มีทางถอด role เดียวโดยไม่ปิดทั้งบัญชี (ต้องใช้ตอนโยกย้ายแผนก/เปลี่ยนบทบาท) →
  - **`services/tenant_admin.py::revoke_role()`**: `delete from user_roles where profile_id=... and company_id=... and role_id=(select id from roles where code=...)` — ไม่แตะ login/profile/role อื่นเลย (contrast กับ `set_user_status` ที่ ban ทั้ง login ผ่าน GoTrue) ตรวจ role_code ต้องอยู่ใน `INVITABLE_ROLES` เดียวกับ invite/grant (กัน `super_admin` หลุดมาทางนี้เด็ดขาด — mint/revoke ไม่ได้ผ่าน tenant-scoped API นี้เลย) + กันถอด role ตัวเอง (guard เดียวกับ self-deactivate ใน `set_user_status`, กันล็อกตัวเองออกโดยไม่ตั้งใจ) + audit `role_revoked`
  - Route: `DELETE /api/users/{profile_id}/roles/{role_code}` (hr_admin self-service ในตาราง `routes.py`, ใช้ `_resolve_company` pattern เดียวกับ `set_user_status`/`link_user_employee` — hr_admin จัดการเฉพาะบริษัทตัวเอง, super_admin ผ่าน `?company_id=` ได้ทุกบริษัท)
  - Frontend: `People.tsx` แท็บ "ผู้ใช้ระบบ" — แต่ละ role แสดงเป็น chip พร้อมปุ่ม "×" กดถอดได้ทันที ไม่มี confirm() dialog (ตั้งใจ ให้เหมือน `toggleUserStatus` เดิมที่ก็ไม่มี confirm — ย้อนกลับได้ง่ายแค่ grant ใหม่)
  - pytest +7 เคส (`test_tenant_admin.py`): revoke สำเร็จ+login ยังใช้ได้ (ผ่าน `app.list_company_users` แหล่งความจริง สด — ตัด JWT roles claim ทิ้งเพราะ refresh แค่ตอน login/token-refresh ใหม่), non-hr_admin โดน 403, role_code ผิด/เป็น `super_admin` โดน 400, ถอด role ที่ไม่มีอยู่โดน 404, ถอด role ตัวเองโดน 400, tenant isolation, super_admin ถอดผ่าน `company_id` ได้ — รวม **131/131**
  - พิสูจน์จริงผ่าน browser (login demo-leave/hr_admin จริงที่ `app_Evaluation_System` — บริษัท "Platform" ที่ใช้ร่วมกับข้อมูลทดสอบของ `app_leave_approve`): ถอด `dept_manager` ออกจาก demo-mgr เหลือแค่ `hr_admin` จริง → คืนค่าเดิมกลับหลังพิสูจน์เสร็จ (ไม่ทิ้งผลข้างเคียงกับข้อมูลทดสอบที่ใช้ร่วมกัน)
  - **ไม่ทำในรอบนี้ตามที่ผู้ใช้ขอ ("เพิ่มปุ่มถอด role อย่างเดียวก่อน")**: ยังไม่มีปุ่ม "เปลี่ยน role" (ถอด+grant ในคลิกเดียว), ยังไม่มี guard กัน "ถอดจนบริษัทไม่เหลือ hr_admin เลย" (ไม่มี convention เดิมรองรับ, ไม่ใช่ scope ที่ขอ)
  - **Deploy ขึ้น production แล้ว (2026-08-28)**: `git push origin master` (commit `e873540`) → Render (backend) + Vercel (frontend) auto-deploy ผ่าน GitHub integration ตามที่ตั้งไว้ใน DEPLOYMENT_PILOT.md — ยืนยันหลัง push: `GET /openapi.json` มี path `/api/users/{profile_id}/roles/{role_code}` จริง, ยิง `DELETE` ตรงไปที่ endpoint จริงบน `https://e-appraisal-api.onrender.com` ได้ 401 (ต้อง auth ตามคาด ไม่ใช่ 404) → build เสร็จและ deploy จริงแล้ว, ไม่ได้ทดสอบ end-to-end เต็มรูปแบบบน production (ไม่มี credential จริง) — ทดสอบเต็มรูปแบบทำแล้วเฉพาะ local

- **เพิ่มช่องกรอกอีเมลในฟอร์มพนักงาน (2026-08-29)** — มาจากปัญหาจริงตอนพี่ทดสอบ `app_leave_approve`'s P5 บน
  production: `employees.email` (คอลัมน์เดิมจาก migration `0018_employee_acknowledgement.sql`) **ไม่มี UI
  ให้กรอกได้เลยสักที่** (ฟอร์มเดี่ยวไม่มีช่องนี้, CSV import ก็ไม่มีคอลัมน์นี้) ทำให้ path ขอรหัสผูกบัญชี LINE
  ทางอีเมลใช้งานจริงไม่ได้เลยแม้ตั้ง SMTP ถูกแล้ว เพราะไม่มีทางตั้งอีเมลให้พนักงานได้ตั้งแต่แรก →
  - `EmployeeCreate`/`EmployeeUpdate`/`EmployeeOut` เพิ่ม `email: Optional[str]` (plain `str` ไม่ใช้
    `EmailStr` ให้ตรง convention เดิมของ field email อื่นในโค้ดนี้ เช่น `InviteUserIn`)
  - `services/employees.py`: `_LIST_SQL` เพิ่ม `e.email`, `create_employee` insert คอลัมน์นี้เพิ่ม,
    `update_employee`'s dynamic column whitelist เพิ่ม `"email"` เข้าไป
  - `services/employee_import.py`: CSV `HEADERS` เพิ่มคอลัมน์ "อีเมล" (อยู่ถัดจาก "ตำแหน่ง") ทั้ง template
    และ upsert logic — bulk import ตอน onboard พนักงานจำนวนมากตั้งอีเมลพร้อมกันได้เลยไม่ต้องแก้ทีละคน
  - Frontend: `People.tsx` ฟอร์ม "เพิ่มพนักงาน"/"แก้ไขพนักงาน" เพิ่มช่อง "อีเมล (รับสลิป/ยืนยันตัวตน)"
  - pytest: แก้ `test_employee_import.py` ทุกเคสให้ตรง header ใหม่ (เพิ่มคอลัมน์กลาง CSV กระทบทุก row string)
    + เพิ่ม assertion ยืนยันว่า import ตั้ง/อัปเดตอีเมลถูกต้องจริง — รวม **131/131**
  - พิสูจน์สดผ่าน browser จริง: login HR → แก้ไข DEMO001 → กรอกอีเมล → บันทึก → เช็ค DB ตรงว่าค่าอัปเดตจริง
    (ลบข้อมูลทดสอบออกหลังพิสูจน์เสร็จ)
  - ไม่ใช่ schema/migration ใหม่ (คอลัมน์มีอยู่แล้ว) แค่เปิดช่องให้ตั้งค่าได้จาก UI/CSV เป็นครั้งแรก

## 🖥️ วิธีรัน local (สำหรับ session ถัดไป)
```
npx supabase start          # Postgres @54322, API @54321, Studio @54323
# รัน RLS test (DB layer):
cat supabase/tests/rls_negative_test.sql | docker exec -i supabase_db_app_Evaluation_System psql -U postgres -d postgres -v ON_ERROR_STOP=1
# รัน backend API:
cd backend && cp .env.example .env   # (ค่า local ใช้ได้เลย; SUPABASE_URL=http://localhost:54321)
py -3.11 -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # 3.9 ใช้ได้เช่นกัน (ดู requirements.txt) แต่ 3.11+ ทำให้ patch ความปลอดภัยของ starlette/urllib3/python-multipart ใช้ได้ (ต้อง >=3.10)
.venv/Scripts/python -m uvicorn app.main:app --port 8000
# รัน API test 7/7 (อีก terminal): bash backend/tests/test_api.sh
npx supabase stop           # ตอนเลิกงาน
```

- **ลืมรหัสผ่าน + แจ้งเตือนเปลี่ยนรหัสผ่าน + โครง SMTP เสร็จ+พิสูจน์+deploy ขึ้น production แล้ว** →
  - **ใช้กลไก password recovery ของ Supabase Auth ตรง ๆ ไม่สร้างเอง** — ปลอดภัยกว่าและตรง NIST SP 800-63B/OWASP ASVS โดยดีไซน์อยู่แล้ว (token ใช้ครั้งเดียว, ไม่รั่วว่าอีเมลมีอยู่จริงไหม) แค่ปรับค่าตั้งต้นที่หลวมเกินไป
  - **`supabase/config.toml`**: `secure_password_change = true` (บังคับ reauth/session ใหม่ก่อนเปลี่ยนรหัส), `max_frequency = "60s"` (เดิม 1s แทบไม่จำกัดอัตราเลย — กัน spam/enumeration), `otp_expiry = 1800` (เดิม 1 ชม. → 30 นาที ลดเวลาที่ลิงก์ค้างในอีเมลเป็นความเสี่ยง), เพิ่ม `additional_redirect_urls` ให้ครอบ `/reset-password` ของ frontend dev — **เจอ bug จริงระหว่างทดสอบ**: ไม่เพิ่ม redirect URL ตรงนี้ ลิงก์ในอีเมลจะเด้งไปหน้า default (`site_url`) แทนหน้า reset-password ของเรา ต้องแก้ config ฝั่งนี้เสมอเวลาย้ายโดเมน (local→cloud ก็ต้องทำซ้ำใน dashboard)
  - **`services/email.py`** ใหม่: ส่งอีเมลของเราเอง (ไม่ใช่อีเมล recovery ที่ Supabase ส่งเอง) ผ่าน SMTP ตรง ๆ (`smtplib`, รันใน thread แยกกันบล็อก event loop) — ถ้ายังไม่ตั้งค่า SMTP (`SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` ว่าง) จะ log warning แล้วข้ามเงียบ ๆ **ไม่ทำให้ request ที่เรียกมาพัง** (การเปลี่ยนรหัสผ่านสำเร็จไปแล้วที่ฝั่ง Supabase ก่อนจะถึงจุดนี้ ไม่ควรให้เมลแจ้งเตือนที่ยังไม่พร้อมมาบล็อกผู้ใช้)
  - **`POST /api/auth/password-changed`**: frontend เรียกทันทีหลัง `supabase.auth.updateUser({password})` สำเร็จ — เขียน audit log (`password_changed`, เข้าระบบ audit เดียวกับทุก action สำคัญ) + ส่งอีเมล "รหัสผ่านของคุณถูกเปลี่ยนแล้ว หากไม่ใช่คุณให้ติดต่อ HR ทันที" ไปที่อีเมลเดิม (มาตรการ PDPA: เจ้าของบัญชีต้องรับรู้เมื่อข้อมูลสำคัญของตัวเองถูกแก้ไข แม้ตัวเองเป็นคนกดเอง)
  - Frontend: `ForgotPassword.tsx` (กรอกอีเมล → ข้อความเดียวกันเสมอไม่ว่าอีเมลมีจริงหรือไม่ — กัน enumeration ที่ฝั่ง UI ด้วย ไม่ใช่แค่ backend), `ResetPassword.tsx` (ตั้งรหัสใหม่ + ยืนยัน, เช็ค session ที่ Supabase ฝังมาจากลิงก์อีเมลก่อนให้กรอกฟอร์ม), ลิงก์ "ลืมรหัสผ่าน?" ใน `Login.tsx`
  - **ขอบเขต**: ใช้ได้กับ HR/หัวหน้างาน/ผจก.แผนก/GM-MD/super_admin เท่านั้น เพราะพนักงานทั่วไปยังไม่มีบัญชีล็อกอินตามการตัดสินใจ Phase 1 เดิม
  - พิสูจน์: pytest 3 เคสใหม่ (`test_password_reset.py`: endpoint ต้อง auth, เขียน audit log ถูก tenant) — pytest 96/96 + **เดินสด end-to-end จริงผ่าน browser**: ขอลิงก์ → เจอในกล่องเมลจริงของ local stack (Mailpit) → ตามลิงก์ → เจอ bug redirect URL ผิด (แก้แล้วตามข้างบน) → ตั้งรหัสใหม่ → auto-login เข้า dashboard → ยืนยันด้วย curl ว่ารหัสเก่าใช้ไม่ได้แล้ว (400) รหัสใหม่ใช้ได้ (200) → เช็ค log backend เห็น `smtp_not_configured` warning ตามคาด (ไม่ error, ไม่บล็อก request)
  - **Deploy ขึ้น production แล้ว** (Gmail App Password + Render env vars + Supabase Cloud dashboard redirect URL/auth settings ตั้งครบ) — ยืนยันด้วยการส่งอีเมล recovery จริงไปที่กล่องเมลจริงของผู้ใช้ ได้รับแล้ว

- **แก้บั๊ก `POST /api/users/invite` (และ provisioning) 500 บน production เป็นระยะ ๆ** → root cause: `auth_admin.create_auth_user` เรียก GoTrue admin API ครั้งแรกหลัง Render container เพิ่งตื่นจาก sleep (free tier) บางครั้งเชื่อมต่อไม่ติดรอบแรก (DNS/TLS ยังไม่ warm) — เพิ่ม retry 1 ครั้งเมื่อเจอ `httpx.RequestError` ระดับ connection (ไม่ใช่ retry ทุก error) + log รายละเอียด exception จริงไว้ (`auth_admin_connect_failed`/`auth_admin_create_user_failed`) เผื่อเกิดซ้ำจะวินิจฉัยได้เร็วขึ้น — pytest 96/96 ผ่าน, deploy แล้ว

- **แก้บั๊ก frontend "คุณไม่มีสิทธิ์เข้าถึงหน้านี้" / รายการว่างเปล่า สลับกันไปมาแบบสุ่ม บน production** (ผู้ใช้ report: login ด้วย super_admin แล้วบางครั้งหน้า Tenants ขึ้น "ไม่มีสิทธิ์" บางครั้งขึ้นแต่รายชื่อบริษัทว่างเปล่าทั้งที่สร้างไปแล้ว) → root cause เดียวกับบั๊ก invite ด้านบน (Render cold start ทำให้ `fetch` จากฝั่งเบราว์เซอร์ throw `TypeError: Failed to fetch` ตรง ๆ ไม่ใช่ HTTP error) แต่เป็นคนละจุด (ฝั่ง frontend เรียก backend โดยตรง ไม่ใช่ backend เรียก GoTrue) และมี**บั๊กจริงซ้อนอยู่**: `AuthContext.loadMe()` เดิม catch error แล้ว set `me = null` เฉย ๆ ไม่แยกแยะ "โหลดไม่สำเร็จเพราะเน็ตมีปัญหา" ออกจาก "ไม่มีสิทธิ์จริง ๆ" ทำให้ `RequireRole` เข้าใจผิดว่าไม่มีสิทธิ์ทั้งที่จริงแค่ /api/me ล้มเหลว —
  - `frontend/src/lib/api.ts`: เพิ่ม `fetchWithRetry` (retry 2 ครั้ง, delay 3s/6s) ครอบทุกฟังก์ชันเรียก API (`apiGet`/`apiSend`/`apiUpload`/`apiSendForm`/`apiDownload`) — retry เฉพาะตอน fetch throw ระดับ connection เท่านั้น ไม่ retry เมื่อ server ตอบ HTTP error จริง (คำตอบจริงจาก server ที่ยัง live ไม่ควรถูกยิงซ้ำ)
  - `frontend/src/context/AuthContext.tsx`: เพิ่ม `meError` state แยกจาก `me` — เก็บ error message เมื่อ `/api/me` โหลดไม่สำเร็จ
  - `frontend/src/components/RequireRole.tsx`: เช็ค `meError` ก่อน — ถ้าเป็น error จากการโหลดไม่สำเร็จ ขึ้น "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ลองใหม่อีกครั้ง" + ปุ่มลองใหม่ แทนที่ "คุณไม่มีสิทธิ์เข้าถึงหน้านี้" (ข้อความหลังสงวนไว้เฉพาะกรณีมี `me` แต่ role ไม่พอจริง ๆ)
  - พิสูจน์: tsc ผ่าน (ไม่มี type error), จำลอง cold-start จริงในเครื่อง local (stop backend process → reload หน้า Tenants → เห็นข้อความ "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้" ตามคาดหลัง retry ครบ ~9s แทนที่ "ไม่มีสิทธิ์" แบบเดิม → start backend กลับ → กดปุ่ม "ลองใหม่" → โหลดข้อมูลกลับมาปกติ)
  - deploy ขึ้น production แล้ว (push master → Vercel auto-deploy)

- **แก้บั๊ก super_admin เห็นพนักงาน/user ของทุกบริษัทปนกันในหน้า "พนักงาน & สาขา" ไม่มีทางแยก** (ผู้ใช้ report: สร้าง 2 บริษัทแล้ว แต่หน้านี้แยกไม่ออกว่าข้อมูลเป็นของบริษัทไหน) → root cause: `list_employees`/`list_branches`/`list_users` พึ่ง RLS กรอง company ให้โดยนัยเท่านั้น ซึ่งใช้ไม่ได้กับ super_admin เพราะ `is_super_admin()` bypass RLS ทั้งหมดตามดีไซน์ → ผลคือดึงทุกบริษัทมารวมกัน ดู [SECURITY.md](SECURITY.md) หัวข้อ "super_admin ดูข้อมูลพนักงาน/สาขา/user แยกตามบริษัท" —
  - เพิ่ม explicit `company_id` query param (super_admin เท่านั้น, non-super_admin ส่งมา → 403 ทันที ไม่ว่าจะเป็นบริษัทตัวเองหรือไม่ก็ตาม) ให้ `GET/POST/PATCH /api/employees*`, `/api/branches*`, `GET /api/users`, `POST /api/users/invite`
  - เอาเมนู "พนักงาน & สาขา" ออกจาก nav ของ super_admin แล้ว — เข้าถึงต่อบริษัทผ่านปุ่มใหม่ "จัดการพนักงาน & สาขาของบริษัทนี้" ใน `TenantDetail.tsx` เท่านั้น (ส่ง `company_id` มาใน URL เสมอ)
  - **ขอบเขตที่ตั้งใจไม่ทำรอบนี้**: import พนักงาน/attendance CSV + ตั้งสูตรคะแนนการมา-ลา ยังไม่รองรับ `company_id` explicit — ซ่อนส่วนนี้ไว้เมื่อ super_admin เข้าผ่านบริษัทที่เลือก (ต้องให้ hr_admin ของบริษัทนั้น login ทำเอง) กันไม่ให้เขียนข้อมูลเข้าบริษัท Platform ของ super_admin โดยไม่ตั้งใจ
  - พิสูจน์: pytest ใหม่ 6 เคส (`test_super_admin_company_scoping.py`, มี negative test ครบทั้ง "hr_admin ส่ง company_id ของบริษัทอื่น" และ "hr_admin ส่ง company_id ของตัวเอง" — ทั้งคู่ต้อง 403) รวม pytest ทั้งชุด 108/108 ผ่าน, ทดสอบจริงผ่าน browser (สร้าง 2 บริษัทคนละพนักงาน → เข้าดูแยกกันถูกต้อง, เชิญ user ผ่านหน้า Company A → ยืนยันด้วย SQL ว่าลงบริษัท A ไม่ใช่ platform tenant)
  - deploy ขึ้น production แล้ว (push master → Vercel + Render auto-deploy)

- **เพิ่มฟีเจอร์ปิดใช้งานบัญชี login รายคน** (ผู้ใช้ถาม: "หาก user ลาออก...จะมีวิธีลบ หรือ inactive user อย่างไร" → ตรวจแล้วพบว่ายังไม่มีเลย มีแต่ระงับทั้งบริษัท) → ดูรายละเอียดที่ [SECURITY.md](SECURITY.md) หัวข้อ "ปิดใช้งานบัญชี login" —
  - migration `0022_user_account_status.sql`: `app.list_company_users()` (SECURITY DEFINER, อ่าน `auth.users.banned_until` ที่ session ปกติอ่านไม่ได้ — เหตุผลเดียวกับ `find_profile_by_email`)
  - `auth_admin.set_user_ban()` — ban/unban ผ่าน GoTrue admin API (`ban_duration`) ไม่แตะ profile/user_roles → ใบประเมินเก่าที่คนนั้นเกี่ยวข้องยังอ้างอิงถึงได้ครบ
  - `PATCH /api/users/{id}/status` — hr_admin ปิดได้เฉพาะบริษัทตัวเอง, super_admin ระบุ `company_id` ได้ (ใช้ `_resolve_company()` เดียวกับข้อบนนี้), กันปิดบัญชีตัวเอง (400), กัน user ข้ามบริษัท (404)
  - UI: คอลัมน์ "สถานะ" + ปุ่ม "ปิดใช้งาน/เปิดใช้งาน" ในตาราง user ทั้งหน้า "พนักงาน & สาขา" (hr_admin) และ `TenantDetail.tsx` (super_admin)
  - พิสูจน์: pytest ใหม่ 4 เคส (`test_user_account_status.py`, ทดสอบ login จริงหลัง ban/unban ผ่าน GoTrue จริง) รวมทั้งชุด 112/112 ผ่าน + ยืนยัน manual E2E ผ่าน curl (invite → deactivate → login 400 → reactivate → login 200)
  - deploy ขึ้น production แล้ว (push master → Vercel + Render auto-deploy)

- **แก้ปัญหา "ลืมรหัสผ่านไม่มีเมลมา"** → root cause คนละเรื่องกับบั๊กด้านบน: **Supabase Cloud free tier auto-pause โปรเจกต์เมื่อไม่มี API activity นานพอ** — ตอน pause อยู่ GoTrue (Auth) จะไม่ทำงาน ส่งอีเมล recovery ไม่ได้เลย (ไม่ error ให้เห็นฝั่ง UI ด้วย เพราะ UI ตั้งใจให้ขึ้นข้อความเดียวกันเสมอกันเดา enumeration) — แก้โดยเข้า Supabase dashboard กด **Resume/Restore project** แล้วอีเมล recovery ส่งได้ปกติ **ไม่ต้องแก้โค้ด** — จดไว้เป็นความรู้สำหรับ pilot ที่ยังไม่มี traffic สม่ำเสมอ: ถ้าเจออาการคล้ายกัน (ไม่ใช่แค่ reset password — login/ทุกอย่างที่พึ่ง Supabase Auth จะพังหมดถ้า pause) ให้เช็คสถานะโปรเจกต์ใน dashboard ก่อนเป็นอันดับแรก

- **แก้ backend cold start จริงจัง ด้วย keep-alive ping ภายนอก** (ผู้ใช้ถามทำไมโหลดช้า) → root cause: Render free tier sleep หลัง idle 15 นาที ที่แก้ไปก่อนหน้า (retry ฝั่ง frontend) แค่ทำให้ error message ถูกต้องขึ้น **ไม่ได้แก้ที่ต้นเหตุความช้า** — แนะนำ + ผู้ใช้ตั้งเอง: UptimeRobot ping `https://e-appraisal-api.onrender.com/health` ทุก 10 นาที (ก่อน 15 นาทีที่ Render จะ sleep) — พิสูจน์: รอ 18 นาทีไม่มี request อื่นแทรก แล้วยิง `/health` ได้ 0.17s (ไม่ cold start) เทียบกับ 20-50s ตอนยังไม่ตั้ง — ไม่ใช่การแก้โค้ด เป็น infra workaround ของ free tier

- **แก้ label "ระดับ" กำกวม → "ประเภทแบบประเมิน"** (ผู้ใช้สับสนตอนเพิ่ม ผจก.แผนก ไม่รู้ว่า "ระดับ" คือเลือกฟอร์ม 28/42 ข้อ ไม่ใช่ตำแหน่ง) →
  - `frontend/src/types.ts` (`LEVEL_LABEL`), `People.tsx` (label ฟอร์ม + หัวตาราง), `Dashboard.tsx` (หัวตาราง + แก้บั๊กเดิมที่โชว์ค่าดิบ `operational`/`supervisor` แทนคำแปลไทย) — เปลี่ยนแค่ข้อความแสดงผล ไม่แตะค่าที่เก็บใน DB (`operational`/`supervisor` เหมือนเดิม)
  - พิสูจน์: tsc ผ่าน + เช็คจริงผ่าน browser ทั้งหน้า People และ Dashboard
  - deploy ขึ้น production แล้ว

- **แก้ AppHeader ล้นจอมือถือ (เสร็จ+พิสูจน์+deploy)** (ผู้ใช้ขอให้เช็ค responsive ตอนแก้ตารางพนักงาน) → ตรวจแล้วพบว่าปัญหาจริงไม่ใช่แค่ตาราง แต่เป็น**แถวบนของ `AppHeader` เอง** (โลโก้ + ตัวสลับบริษัท + `CurrentUserBadge` + ปุ่มออกจากระบบ) ไม่มี `flex-wrap` และ `CurrentUserBadge` บังคับ `whitespace-nowrap` บนข้อความที่ยาวได้ (อีเมล · บทบาท · บริษัท · สาขา) → ดันทั้งหน้าล้นจอแนวนอนทุกหน้า (header ใช้ร่วมกันทุกหน้า ไม่ใช่แค่ People) —
  - แก้ `AppHeader.tsx` ให้แถวบนตัดขึ้นบรรทัดใหม่ได้ (`flex-wrap`) แทนล้นจอ, เอา `whitespace-nowrap` ออกจาก `CurrentUserBadge.tsx`
  - พิสูจน์: เช็คจริงผ่าน browser ที่ 375px (มือถือ) และ 768px (แท็บเล็ต) ด้วย `document.body.scrollWidth` เทียบ `window.innerWidth` — ไม่มีการล้นจอเหลืออีก ทั้งหน้า People และ Dashboard, ตารางพนักงานยัง scroll ในกรอบตัวเองได้ตามปกติ (ตั้งใจให้เป็นแบบนั้น)

- **สร้างใบประเมิน: แก้บั๊ก dropdown ซ้ำ + company_id ผิด (เสร็จ+พิสูจน์)** (ผู้ใช้ถาม "ทำไมมีเมนูให้เลือกซ้ำๆ กัน" ที่ dropdown "แบบฟอร์ม" หน้าใบประเมินผล) → ดูรายละเอียดที่ [SECURITY.md](SECURITY.md) หัวข้อ "สร้างใบประเมิน: template ต้องเป็นของบริษัทเดียวกับพนักงาน" — ไล่โค้ดจริงเจอบั๊ก 2 ชั้น ไม่ใช่แค่ UI ซ้ำ:
  - `GET /api/templates` ไม่กรอง company (RLS bypass สำหรับ super_admin เหมือนบั๊กพนักงาน/user ก่อนหน้า) + โชว์ master template (ต้นแบบสำหรับ clone เท่านั้น) ปนกับสำเนาแต่ละบริษัท → แก้โดยตัด master ออกจากลิสต์เสมอ (ทุก role)
  - **บั๊กที่ร้ายแรงกว่าที่เจอตามมา**: `evaluations.company_id` เดิมตั้งจาก `user.company_id` (ผู้กระทำ) แทนที่จะเป็นบริษัทของพนักงานที่ถูกประเมิน — ถ้า super_admin สร้างใบประเมินให้พนักงานบริษัทจริง ใบจะลงใต้ platform tenant แทน กลายเป็นใบที่บริษัทเจ้าของพนักงานตัวจริงมองไม่เห็นเลย — เช็คแล้วบน production **ยังไม่มีข้อมูลเสียหายจริง** (0 แถว) แต่พร้อมเกิดถ้าใช้ต่อ
  - แก้: `target_company = emp["company_id"]` (ไม่ใช่ผู้กระทำ) ใช้ทั้ง insert evaluation + audit log, เพิ่มตรวจ `template.company_id == target_company` เป๊ะ ไม่งั้น 400
  - พิสูจน์: negative test ใหม่ 2 เคส (`test_create_rejects_template_from_another_company`, `test_create_rejects_master_template_directly`) + แก้ fixture เดิม (`test_evaluation_lifecycle.py`'s `org`) ให้ clone template เป็นของ tenant ตัวเองแทนใช้ master ตรงๆ (ตรงกับพฤติกรรมจริงหลังแก้) — pytest ทั้งชุด **114/114** ผ่าน
  - deploy ขึ้น production แล้ว (push master → Vercel + Render auto-deploy)

- **แก้วรรณยุกต์ซ้อนสระเพี้ยนใน PDF ผลการประเมิน (เสร็จ+พิสูจน์+deploy)** (ผู้ใช้แนบ PDF จริง: "รวมทั้งสิ้น" อ่านไม่ออก) →
  - root cause: **ReportLab ไม่มี text-shaping engine แบบ OpenType** เลย ไม่อ่าน GPOS mark-to-mark ของ font (Sarabun มีข้อมูลนี้ถูกต้องอยู่แล้ว แต่ ReportLab ไม่ไปใช้) — วรรณยุกต์เดี่ยว ๆ เรนเดอร์ถูกทุกที่ในเอกสาร แต่พอมี **2 เครื่องหมายซ้อนกัน** (สระบน เช่น ั/ิ + วรรณยุกต์ เช่น ้) ทั้งคู่จะถูกวาดทับตำแหน่งเดียวกันแทนที่จะดันวรรณยุกต์ขึ้น — ยืนยันด้วยการ render PDF จริงเป็นภาพซูม (pymupdf ชั่วคราว ไม่ได้เพิ่มเป็น dependency ถาวร) เห็นปัญหาชัดเจนที่ "ทั้ง"/"สิ้น"
  - **แก้แบบเฉพาะจุด** (ตามที่คุยกับผู้ใช้แล้วเลือกไม่ swap ทั้ง pipeline ไปใช้ text-shaping engine อย่าง HarfBuzz เพราะใหญ่/เสี่ยงเกินความจำเป็น): `backend/app/services/pdf.py` เพิ่ม `_fix_thai_stacking()` — regex จับคู่ "สระบน + วรรณยุกต์" (`([ัิีึื])([่้๊๋์])`) แล้วห่อวรรณยุกต์ด้วย `<super rise="Xpt" size="Ypt">` (ReportLab เฉพาะ `<super>`/`<sub>` เท่านั้นที่รับ attribute `rise` ได้ — `<font>`/`<span>` ไม่รับ ลองผิดมาก่อนเจอ error `invalid attribute name rise`; ต้องกำหนด `size` กำกับด้วยเพราะ `<super>` auto ย่อขนาดฟอนต์เป็นค่าเริ่มต้น ไม่ต้องการผลนั้น)
  - **เจอบั๊กที่ซ่อนอยู่ระหว่างแก้**: ไม่มีการ escape XML เลยก่อนส่งข้อความ (ชื่อพนักงาน/ตำแหน่ง/ความเห็น) เข้า `Paragraph` ทั้งที่ `Paragraph` แปลข้อความเป็น markup — ชื่อที่มี `&`/`<`/`>` จะพัง PDF ได้ → รวม fix เข้าด้วยกันเป็น helper เดียว `_p(text, style)` แทนที่ทุกจุดที่เรียก `Paragraph(...)` ตรง ๆ (50 จุด) ให้ escape ก่อนเสมอแล้วค่อยแก้ stacking
  - พิสูจน์: unit test ใหม่ 4 เคส (`test_pdf_thai_rendering.py`) + pytest ทั้งชุด **118/118** ผ่าน + ตรวจภาพจริงด้วย pymupdf ก่อน/หลังแก้ (ก่อน: ตัวอักษรทับกันอ่านไม่ออก, หลัง: อ่านออกชัดเจน)

- **นำทาง (nav bar) เดียวทุกหน้า + badge ผู้ใช้ปัจจุบัน/บริษัท/สาขา เสร็จ+พิสูจน์+deploy** → เดิมแต่ละหน้ามี `<header>` ของตัวเอง ลิงก์ย้อนกลับไม่เหมือนกัน ("← แดชบอร์ด"/"← ใบประเมินผล"/"← กลับ") และไม่เห็นเมนูหลักทั้งหมดพร้อมกัน (ผู้ใช้แจ้งว่าสับสน) →
  - `frontend/src/components/AppHeader.tsx` ใหม่ — nav เดียวใช้ร่วมทุกหน้า แสดงเมนูตามสิทธิ์ผู้ใช้ (`NAV_ITEMS` + `show()`), ไฮไลต์หน้าปัจจุบันด้วยเส้นใต้ (`isActive()`), ปุ่ม "ออกจากระบบ" อยู่จุดเดียวกดได้ทุกหน้า — แทนที่ `<header>` เดิมใน `Dashboard/Evaluations/Inbox/People/Tenants/TenantDetail/Compare/EvaluationDetail.tsx` ทั้งหมด
  - `frontend/src/components/CurrentUserBadge.tsx` ใหม่ — โชว์ email/role/บริษัท/สาขา มุมขวาบนทุกหน้า
  - `GET /api/me` เพิ่ม `company_name`/`branch_name` (join `companies`/`employees`/`branches` แทนที่จะโชว์ UUID ดิบ) — Dashboard การ์ด "ผู้ใช้ปัจจุบัน" ก็อัปเดตตาม
  - พิสูจน์: tsc + `npm run build` ผ่าน, pytest ผ่าน, เช็ค console error ผ่าน browser preview

- **Multi-company account switching เสร็จ+พิสูจน์+deploy** (ผู้ใช้ดูแลหลายบริษัทจริง อยากสลับได้โดยไม่ต้องแยกอีเมล) → ดูแผนเต็มที่ `docs/SECURITY.md` หัวข้อ "Multi-company account switching" (map OWASP A01) —
  - **`0021_multi_company_access.sql`**: (1) **แก้ primary key ของ `user_roles`** จาก `(profile_id, role_id)` เป็น `(profile_id, role_id, company_id)` — ค้นพบระหว่างเขียน test จริง ไม่ใช่จาก static review: PK เดิมทำให้ profile เดียวถือ role code เดิม (เช่น hr_admin) ซ้ำในสองบริษัทไม่ได้เลย เป็น blocker ตัวจริงของทั้งฟีเจอร์; (2) **แก้บั๊ก auth hook** — `roles` claim เดิมรวม role ข้ามบริษัททั้งหมดของ profile ไม่ scope ตาม company_id ที่ active (มีผลจริงทันทีที่ profile มี role มากกว่า 1 บริษัท) แก้เป็น filter `ur.company_id = v_company_id`; (3) ฟังก์ชัน `SECURITY DEFINER` ใหม่: `app.list_my_companies()`, `app.switch_active_company(uuid)` (self-validate จาก `user_roles` ก่อน update `profiles.company_id`), `app.find_profile_by_email(text)` (หา profile เดิมจาก email เพื่อมอบสิทธิ์ ไม่ต้องผ่าน GoTrue admin API อีกเส้นทาง)
  - **Backend**: `services/company_access.py` ใหม่ (list/switch, audit ที่ company **ขาออก** เพราะ audit_logs RLS ยังอิง JWT เดิมก่อน refresh), `tenant_admin.grant_company_access` ใหม่ (super_admin เท่านั้น — กัน hr_admin ให้สิทธิ์ตัวเองข้ามบริษัทโดยที่บริษัทปลายทางไม่ยินยอม), routes: `GET /api/me/companies`, `POST /api/me/active-company`, `POST /api/admin/tenants/{id}/users/grant`
  - **Frontend**: `AuthContext.switchCompany()` (เรียก endpoint → `supabase.auth.refreshSession()` เพื่อให้ auth hook รันใหม่ได้ claim ที่ถูกต้อง → reload หน้า), `components/CompanySwitcher.tsx` (dropdown ใน `AppHeader`, ไม่โชว์ถ้ามีบริษัทเดียว), ฟอร์ม "ให้สิทธิ์ผู้ใช้เดิมเข้าบริษัทนี้" ใน `TenantDetail.tsx`
  - **ขอบเขตที่ตัดออกโดยตั้งใจ** (คุยกับผู้ใช้แล้ว): branch-level switching ไม่ทำ (ไม่มี concept นี้ในระบบเลย — ดู "ทำต่อ"), มอบสิทธิ์ข้ามบริษัทได้เฉพาะ super_admin, `profiles.employee_id` ไม่สลับตามบริษัท (จำกัดเฉพาะ role ที่ไม่อิงตัวตนพนักงาน เช่น hr_admin — บทบาทที่ต้องอิงสายบังคับบัญชาอย่าง manager/dept_manager ยังทำข้ามบริษัทเดียวกันไม่ได้เต็มรูปแบบ)
  - พิสูจน์: pytest 6 เคสใหม่ (`test_multi_company_access.py`: switch สำเร็จ+`/api/me/companies` ครบ, **switch ไปบริษัทที่ไม่มีสิทธิ์ต้อง 403 และ company_id ไม่เปลี่ยน**, RLS หลัง switch เห็นเฉพาะบริษัทใหม่จริง, **roles claim ต้อง scope ตามบริษัท active ไม่ leak ข้ามบริษัท**, grant ต้อง super_admin เท่านั้น, grant ต้องมีบัญชีเดิมอยู่ก่อน) — pytest **102/102** + ทดสอบจริงผ่าน browser local (สร้างบัญชีทดสอบถือ hr_admin 2 บริษัท → สลับ dropdown → หน้ารีโหลด → "บริษัท" ในการ์ดผู้ใช้ปัจจุบันเปลี่ยนถูกต้อง ไม่มี console error) — ยืนยันเชิงประจักษ์แล้วว่า `refreshSession()` ทำให้ auth hook รันใหม่จริง (ไม่ต้อง fallback ไป sign-out ตามที่กังวลไว้ตอนวางแผน)

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
- สูตรคะแนน attendance มีค่าเริ่มต้นแล้ว (40/4/1/0.5/1) และ HR ปรับเองได้ที่หน้า `/people` — แต่ยังไม่มีใครยืนยันว่าค่าเริ่มต้นนี้ตรงนโยบายบริษัทจริง
- BARS anchors (desc_1..5) ยังเป็น placeholder — ส่ง `exports/evaluation-criteria-bars.docx` ให้ HR ตรวจแล้ว รอผลตรวจกลับมา
- การรับทราบแบบกระดาษใช้งานได้แล้ว (local — ยังไม่ deploy production) เมื่อจะทำเฟสอีเมลต่อ ต้องแยกบัญชี Gmail สำหรับส่งอีเมลออกจากบัญชีที่ส่งสลิปเงินเดือน — ห้ามใช้ร่วมกันเด็ดขาด
- ยืนยันว่า "500 คน" เป็นต่อ tenant หรือรวมทุก tenant (กระทบ capacity planning)
