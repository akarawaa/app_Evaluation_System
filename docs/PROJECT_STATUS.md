# Project Status — E-Appraisal  *(อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง)*

> เอกสารมีชีวิต (living doc) — **อัปเดตทุกครั้งที่จบงาน** เพื่อส่งต่อ session ถัดไป

**อัปเดตล่าสุด:** 2026-07-06
**Phase ปัจจุบัน:** Phase 1 — Foundation
**สเต็ปที่กำลังทำ:** Step 1–3 เสร็จ + พิสูจน์จริงบน local (RLS + Auth Hook) → ถัดไป Step 5 (FastAPI)

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

## 🔜 ทำต่อ (ถัดไป)
1. Step 5 — ต่อ FastAPI: verify JWT (secret จาก Supabase) + tenant guard + repository ตั้ง `request.jwt.claims` ต่อ session ให้ RLS ทำงาน + request_id/logging middleware + audit helper + security headers
2. Step 6/7 — provisioning/RBAC API (super_admin สร้าง tenant + hr_admin + clone template) + React skeleton (login flow)
3. Step 8 (เพิ่ม) — ครอบ negative test ทุก endpoint ตอนมี API

## 🖥️ วิธีรัน local (สำหรับ session ถัดไป)
```
npx supabase start          # Postgres @54322, API @54321, Studio @54323
# รัน RLS test:
cat supabase/tests/rls_negative_test.sql | docker exec -i supabase_db_app_Evaluation_System psql -U postgres -d postgres -v ON_ERROR_STOP=1
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
