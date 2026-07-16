# Project Status — E-Appraisal  *(อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง)*

> เอกสารมีชีวิต (living doc) — **อัปเดตทุกครั้งที่จบงาน** เพื่อส่งต่อ session ถัดไป

**อัปเดตล่าสุด:** 2026-07-16
**Phase ปัจจุบัน:** Phase 1 — Foundation
**สเต็ปที่กำลังทำ:** Phase 1–3 + admin tooling + role-based UI + read-visibility + BARS anchors + ระบบ attendance + bundle ฟอนต์ OFL + export Excel + หน้า HR ปรับสูตร attendance + หน้าเปรียบเทียบผลประเมิน + **อัปเกรด Python 3.9→3.11 + ปิดช่องโหว่ dependency ทั้งหมด** เสร็จ+พิสูจน์ (pytest 81/81 · pip-audit 0 vulnerabilities) → เหลือรอ HR ตรวจ/ปรับถ้อยคำ BARS + ตั้งค่าสูตร attendance ตามนโยบายบริษัทจริง

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
0. **กำลังทำ: deploy pilot environment ฟรี** ให้หัวหน้างานทดลองใช้จริง (Supabase Cloud + Render + Vercel) — ดูขั้นตอนละเอียดที่ [docs/DEPLOYMENT_PILOT.md](DEPLOYMENT_PILOT.md), เตรียม `render.yaml` + `frontend/vercel.json` ไว้แล้ว รอผู้ใช้ทำขั้นที่ต้องสร้างบัญชี/กรอก secret เอง (Supabase project, GitHub repo, Render/Vercel signup)
1. รอ HR: **เข้าไปตั้งค่าสูตร attendance ที่หน้า `/people` ตามนโยบายบริษัทจริง** (ตอนนี้ยังเป็นค่าเริ่มต้น 40/4/1/0.5/1 จนกว่า HR จะปรับ), ตรวจ/ปรับถ้อยคำ BARS anchors, เกณฑ์ probation ต่อ checkpoint — ส่งไฟล์ `exports/evaluation-criteria-bars.docx` ให้ตรวจแล้ว
2. (ไอเดียถัดไป ยังไม่เริ่ม) ตัวกรอง export ตาม cycle_id ถ้าฟีเจอร์ evaluation_cycles เริ่มมีการใช้งานจริง (ตอนนี้ cycle_id ยังไม่มี UI สร้าง/เลือก cycle เลย)
3. **(ตัดสินใจรอ) ขยาย audit log ให้ครอบคลุม "sensitive read" กว้างขึ้น** — ตอนนี้ audit ครอบ mutation ทุกจุด + export (PDF/Excel) + compare แล้ว แต่ยังไม่ครอบการเปิดดูใบประเมิน/พนักงานแบบเจาะจงทีละรายการ (`GET /api/evaluations/{id}`, `GET /api/employees/{id}`) ตามที่ `docs/LOGGING_AND_AUDIT.md` ระบุไว้เป็นเป้าหมาย Phase 1 (`view_employee`) — ยังไม่ทำเพราะจะเพิ่มปริมาณ write เข้า audit_logs ทุก GET request อย่างมีนัยสำคัญ ควรคุยกับทีมก่อนว่าต้องการระดับละเอียดแค่ไหน (ทุกครั้งที่เปิดดู vs. เฉพาะการ export/เปรียบเทียบแบบที่ทำไปแล้ว)

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
