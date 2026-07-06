# คู่มือสำหรับ AI Assistant / นักพัฒนา (Session Handoff Guide)

> **อ่านไฟล์นี้ + [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) ก่อนเริ่มงานทุกครั้ง**

## โปรเจกต์นี้คืออะไร
E-Appraisal — ระบบประเมินผลพนักงานแบบ **SaaS Multi-Tenant** แทนใบประเมินกระดาษ FMHR07
Stack: FastAPI + Supabase (Postgres/Auth/RLS) + React/Tailwind

## กติกาที่ต้องยึด (Non-negotiable)
1. **Multi-tenant isolation มาก่อนเสมอ** — ทุกตาราง tenant-scoped ต้องมี `company_id` + RLS policy
   ห้าม merge/deploy โค้ดที่ query ข้อมูลข้าม tenant ได้
2. **Security by design (OWASP)** — ทำตาม [docs/SECURITY.md](docs/SECURITY.md) ทุก endpoint/ตาราง
   ต้อง map ว่าแต่ละฟีเจอร์คุ้มครอง A01–A10 อย่างไร
3. **Audit ทุกการเปลี่ยนข้อมูลสำคัญ** — ตาม [docs/LOGGING_AND_AUDIT.md](docs/LOGGING_AND_AUDIT.md)
4. **เกณฑ์ประเมินไม่ hardcode** — เป็น template ปรับได้ (BARS)
5. **Phase 1 ไม่ทำ approval workflow** — เลื่อนไป Phase 2
6. **ห้าม commit secrets** — ใช้ `.env` (อยู่ใน .gitignore) มี `.env.example` เป็นแม่แบบ

## ขั้นตอนเวลาเริ่มงานใหม่ (session ใหม่)
1. อ่าน `docs/PROJECT_STATUS.md` → ดูว่าทำถึงไหน / ทำอะไรต่อ
2. `git log --oneline -10` → ดูงานล่าสุด
3. ทำงานตาม [docs/PHASE_1_PLAN.md](docs/PHASE_1_PLAN.md) ทีละสเต็ป
4. **จบงานทุกครั้ง:** อัปเดต `docs/PROJECT_STATUS.md` (ทำอะไรไป / เหลืออะไร / ติดอะไร) แล้ว commit

## Git convention
- Branch จาก main เสมอ (อย่า commit ตรง main สำหรับงานใหญ่)
- Commit message: `<type>: <สรุปสั้น>` เช่น `feat: add companies table + RLS`
- ทุก commit ที่แตะ schema/security ต้องอัปเดตเอกสาร docs/ ที่เกี่ยวข้องในคอมมิตเดียวกัน

## Definition of Done (ต่อ 1 หน่วยงาน)
- [ ] มี `company_id` + RLS (ถ้าเป็นตาราง tenant-scoped)
- [ ] มี audit logging (ถ้าเป็นการเขียน/แก้/ลบข้อมูล)
- [ ] Input ผ่าน validation (Pydantic / zod)
- [ ] มี negative test: user tenant A เข้าถึงข้อมูล tenant B ไม่ได้
- [ ] อัปเดตเอกสาร docs/ ที่เกี่ยวข้อง
