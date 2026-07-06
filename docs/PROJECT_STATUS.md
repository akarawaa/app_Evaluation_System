# Project Status — E-Appraisal  *(อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง)*

> เอกสารมีชีวิต (living doc) — **อัปเดตทุกครั้งที่จบงาน** เพื่อส่งต่อ session ถัดไป

**อัปเดตล่าสุด:** 2026-07-06
**Phase ปัจจุบัน:** Phase 1 — Foundation
**สเต็ปที่กำลังทำ:** Step 2 เสร็จ (schema+RLS เขียนแล้ว, ยังไม่รันจริง) → ถัดไป Step 1 รัน migration + Step 3

---

## ✅ ทำไปแล้ว
- อ่าน/วิเคราะห์ใบประเมินเดิม FMHR07 → `docs/evaluation-form-analysis.md`
- วิเคราะห์ช่องโหว่ PROJECT_PLAN.md (multi-tenant) → สะท้อนใน SECURITY.md
- ตัดสินใจสถาปัตยกรรมหลัก + tooling (ดู "การตัดสินใจที่ล็อกแล้ว")
- `git init` + commit แรก (เอกสารควบคุมงานครบ)
- **โครงโฟลเดอร์:** `backend/` (FastAPI: app/core/api/services/repositories/schemas + config + main + requirements + .env.example), `frontend/` (package.json + .env.example), `supabase/`
- **SQL migrations (เขียนแล้ว ยังไม่รัน):** `supabase/migrations/0001–0006` — extensions, auth helpers (JWT claim readers), tenant+identity schema (FK/CHECK/index), criteria (BARS), audit_logs, **RLS policies ครบทุกตาราง**
- **Seed:** `supabase/seed.sql` — role catalog + master template FMHR07 (operational 28 ข้อ, supervisor 42 ข้อ; desc_1..5 เว้นให้ HR เติม)

## 🔜 ทำต่อ (ถัดไป)
1. **รัน migration จริง** — `supabase init` → `supabase start` → `supabase db reset` (ยังไม่ได้ทดสอบว่ารันผ่าน ต้องมี Docker/Supabase CLI ในเครื่อง)
2. Step 3 — Custom Access Token Hook ฝัง `company_id`/`is_super_admin`/`roles` ลง JWT
3. Step 5 — ต่อ FastAPI: JWT verify + tenant guard + request_id/logging middleware + audit helper + security headers
4. Step 8 — negative test ข้าม tenant (สำคัญ: ต้องพิสูจน์ว่า RLS กันจริง)

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
