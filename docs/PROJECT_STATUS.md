# Project Status — E-Appraisal  *(อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง)*

> เอกสารมีชีวิต (living doc) — **อัปเดตทุกครั้งที่จบงาน** เพื่อส่งต่อ session ถัดไป

**อัปเดตล่าสุด:** 2026-07-06
**Phase ปัจจุบัน:** Phase 1 — Foundation
**สเต็ปที่กำลังทำ:** Phase 1 + Phase 2 (Step 1–3) + **Phase 3 (PDF export)** เสร็จ+พิสูจน์ (pytest 19/19 · browser · PDF ไทยเรนเดอร์ถูก) → เหลือ polish UI + รอ HR (สูตร attendance, BARS anchors)

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

## 🔜 ทำต่อ (ถัดไป)
1. Polish frontend: approval inbox (กรองใบที่รอเราอนุมัติ), หน้าจัดการ employee/branch/tenant, แสดงปุ่มตาม role จริง (ตอนนี้อิงสถานะ + backend 403)
2. bundle ฟอนต์ OFL สำหรับ PDF (deploy Linux) + review pip-audit runtime advisories เมื่อมี fix
3. รอ HR: สูตร attendance (เต็ม 40), เนื้อหา `desc_1..5`, เกณฑ์ probation ต่อ checkpoint

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
