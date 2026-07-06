# Project Status — E-Appraisal  *(อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง)*

> เอกสารมีชีวิต (living doc) — **อัปเดตทุกครั้งที่จบงาน** เพื่อส่งต่อ session ถัดไป

**อัปเดตล่าสุด:** 2026-07-06
**Phase ปัจจุบัน:** Phase 1 — Foundation
**สเต็ปที่กำลังทำ:** Step 0 (Project & Repo Setup)

---

## ✅ ทำไปแล้ว
- อ่าน/วิเคราะห์ใบประเมินเดิม FMHR07 → `docs/evaluation-form-analysis.md`
- วิเคราะห์ช่องโหว่ PROJECT_PLAN.md (multi-tenant) — สรุปในบทสนทนาและสะท้อนใน SECURITY.md
- ตัดสินใจสถาปัตยกรรมหลัก (ดู "การตัดสินใจที่ล็อกแล้ว")
- `git init`
- สร้างเอกสารควบคุมงาน: README, CLAUDE.md, ARCHITECTURE, DATABASE_SCHEMA, SECURITY (OWASP), LOGGING_AND_AUDIT, PHASE_1_PLAN, PROJECT_STATUS
- สร้าง .gitignore

## 🔜 ทำต่อ (ถัดไป)
1. ตอบคำถามค้าง (ด้านล่าง) — Supabase local/cloud, DB access lib, package manager
2. สร้างโครงโฟลเดอร์ `backend/` + `frontend/` + `.env.example`
3. Commit แรก
4. เริ่ม Step 1–2 (Supabase + tenant schema + RLS) ตาม `docs/PHASE_1_PLAN.md`

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

## ❓ คำถามค้าง (รอผู้ใช้ยืนยัน — ไม่บล็อกงานเอกสาร)
- Supabase: cloud project หรือ local (CLI/Docker)?
- DB access: SQLAlchemy+asyncpg หรือ supabase-py?
- Frontend package manager: npm หรือ pnpm?
- Criteria scope ต่อ tenant, login scope, role set — เคยเสนอ default ไว้ ถ้าไม่ค้านจะใช้ตามนั้น

## 🧭 จุดอ้างอิงเร็ว
- แผนละเอียด: `docs/PHASE_1_PLAN.md`
- schema: `docs/DATABASE_SCHEMA.md`
- กติกา/DoD: `CLAUDE.md`

## 📌 ค้าง/ความเสี่ยงที่ต้องจำ
- สูตรคะแนน attendance (max 40) ยังไม่รู้ — ต้องถาม HR (Phase 2)
- BARS anchors (desc_1..5) ยังเป็น placeholder — HR ต้องเติมเนื้อหาจริง
- ยืนยันว่า "500 คน" เป็นต่อ tenant หรือรวมทุก tenant (กระทบ capacity planning)
