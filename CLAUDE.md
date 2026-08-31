# CLAUDE.md — app_Evaluation_System (session handoff)

> เริ่ม session: อ่าน **[docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)** + **[`../platform-core/docs/CONVENTIONS.md`](../platform-core/docs/CONVENTIONS.md)** ก่อนเสมอ

## แอปนี้คืออะไร
E-Appraisal — ประเมินผลพนักงาน SaaS multi-tenant แทนใบกระดาษ FMHR07. live production.
Stack: FastAPI + Supabase (Postgres/Auth/RLS/Storage) + React/Tailwind. ส่วนหนึ่งของ **HR Suite**
([`../platform-core/docs/PLATFORM_ARCHITECTURE.md`](../platform-core/docs/PLATFORM_ARCHITECTURE.md)) — Supabase project เดียวกับ leave/attendance

## Non-negotiable — เฉพาะแอปนี้
1. **เกณฑ์ประเมินไม่ hardcode** — เป็น BARS template ปรับได้ (master default + clone ต่อ tenant)
2. **"รับทราบ" ≠ "เห็นด้วย"** — acknowledgement มี decision 3 แบบ (acknowledged / acknowledged_disagreed / refused) + ช่องความเห็นแย้ง — ห้ามบังคับ "เห็นด้วย" ถึงจะผ่าน (หลักฐานชั้นศาลแรงงาน)
3. **`evaluations.company_id` = บริษัทของพนักงานที่ถูกประเมิน** ไม่ใช่ผู้กระทำ (super_admin สร้างใบให้บริษัทอื่นได้) — template ต้อง `company_id` ตรงกับพนักงาน
4. **super_admin bypass RLS** — ทุก list endpoint ที่ super_admin ใช้ได้ต้องรับ `company_id` param ชัดเจน (non-super_admin ส่งมา = 403)
5. **ตารางสร้างหลัง migration `0006`** ต้อง `grant select/insert/update/delete ... to authenticated` เอง (0006 grant ย้อนหลังไม่ครอบ)

> กติกา suite (tenant isolation, core FK-only, migration timeline, security/PDPA baseline, audit,
> bug classes: timezone/`window.confirm`/auth-after-transition/ruff-py39, git, DoD) → **CONVENTIONS.md**

## เอกสาร
| งาน | อ่าน |
|---|---|
| สถานะ / ทำอะไรต่อ | [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) |
| แผนเฟส | [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) |
| schema | [docs/DATA_MODEL.md](docs/DATA_MODEL.md) |
| ฟีเจอร์ประเมิน | [docs/EVALUATION_DESIGN.md](docs/EVALUATION_DESIGN.md) |
| security / audit | [docs/SECURITY.md](docs/SECURITY.md) · [docs/LOGGING_AND_AUDIT.md](docs/LOGGING_AND_AUDIT.md) |
| deploy | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |

## จบงานทุกครั้ง
อัปเดต [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) (ทำอะไร / เหลืออะไร / ติดอะไร) + commit
(`<type>: <สรุป>`, branch จาก master สำหรับงานใหญ่, อัปเดต docs ในคอมมิตเดียวกับ schema/security)
