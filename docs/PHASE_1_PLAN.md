# Phase 1 Plan — Foundation (Database + Multi-Tenant Auth + RBAC + Criteria)

> **ขอบเขต Phase 1:** DB schema + multi-tenant auth + RBAC + โครงสร้าง criteria/template + OWASP baseline + logging/audit
> **ไม่รวม:** การกรอกใบประเมิน, การให้คะแนน, approval workflow (→ Phase 2)

แต่ละสเต็ปมี Definition of Done (DoD) ชัดเจน ทำเสร็จแล้ว **อัปเดต PROJECT_STATUS.md + commit**

---

## Step 0 — Project & Repo Setup  ✅ (กำลังทำ)
- [x] `git init`
- [x] เอกสารควบคุมงาน (README, CLAUDE.md, docs/*)
- [ ] โครงโฟลเดอร์ backend/ + frontend/
- [ ] `.env.example` (ไม่มี secret จริง)
- **DoD:** repo มีโครงสร้าง + เอกสาร, commit แรกเรียบร้อย

## Step 1 — Supabase Project & Migration Baseline
- [ ] สร้าง Supabase project (local dev ผ่าน Supabase CLI แนะนำ)
- [ ] ตั้งระบบ migration (โฟลเดอร์ `supabase/migrations/`)
- [ ] เปิด `pgcrypto`/`gen_random_uuid`
- **DoD:** รัน migration ว่างผ่าน, เชื่อมต่อ DB ได้

## Step 2 — Tenant & Identity Schema + RLS
- [ ] ตาราง: `companies`, `branches`, `profiles`, `employees`, `roles`, `user_roles`
- [ ] FK + CHECK + Index ตาม DATABASE_SCHEMA.md
- [ ] **เปิด RLS ทุกตาราง** + policy `company_id = auth.jwt()->>'company_id'`
- [ ] security-definer function สำหรับ `super_admin`
- [ ] trigger `updated_at`
- **DoD:** RLS ทำงาน — ทดสอบด้วย 2 tenant แล้วมองข้ามกันไม่ได้ (negative test ผ่าน)

## Step 3 — Auth Hook (ฝัง company_id ใน JWT)
- [ ] ตั้ง Custom Access Token Hook ให้ใส่ `company_id` + roles ลง JWT claims
- [ ] เทสต์ว่า claim ออกมาถูกต้องหลัง login
- **DoD:** JWT ของ user มี `company_id`/roles ตรงกับ profile

## Step 4 — Seed Master Criteria Template (FMHR07 → BARS)
- [ ] seed `criteria_templates` (master, company_id NULL): operational (11 หมวด/28 ข้อ), supervisor (16 หมวด/42 ข้อ)
- [ ] ใส่ categories + items ตาม docs/evaluation-form-analysis.md
- [ ] เว้น `desc_1..desc_5` เป็น placeholder (ให้ HR เติม BARS จริงภายหลัง)
- **DoD:** query master template ได้ครบตามใบ FMHR07

## Step 5 — Backend Skeleton (FastAPI)
- [ ] โครง `app/` (api/services/repositories/schemas/core) ตาม ARCHITECTURE.md
- [ ] config (pydantic-settings) + Supabase client
- [ ] dependency: `get_current_user` (verify JWT) + `tenant_guard`
- [ ] middleware: request_id + structured logging
- [ ] audit helper (service layer)
- [ ] security headers + CORS allowlist
- [ ] health endpoint
- **DoD:** เรียก endpoint ที่ต้อง auth ได้เมื่อมี JWT ถูกต้อง, ถูกปฏิเสธเมื่อไม่มี/ผิด tenant

## Step 6 — RBAC & Tenant Provisioning API (พื้นฐาน)
- [ ] endpoint: super_admin สร้าง company + hr_admin แรก + clone template
- [ ] endpoint: hr_admin จัดการ branches / employees / invite users / grant roles
- [ ] ทุก mutation → audit log
- **DoD:** สร้าง tenant + user + role ได้ครบ flow, มี audit ครบ, RBAC บังคับจริง

## Step 7 — Frontend Skeleton (React + Tailwind)
- [ ] Vite + React + Tailwind + Supabase JS
- [ ] Auth flow (login/logout), เก็บ session
- [ ] Protected routes + role-based layout
- [ ] หน้า admin เบื้องต้น: จัดการ company/branch/employee/user
- **DoD:** login → เห็นเฉพาะข้อมูล tenant ตัวเอง, UI ปรับตาม role

## Step 8 — Security & Isolation Testing
- [ ] Negative tests: cross-tenant access ถูก block ทุก endpoint/ตาราง
- [ ] ตรวจ RLS เปิดครบทุกตาราง
- [ ] `pip-audit` / `npm audit`
- [ ] ทวน SECURITY.md checklist
- **DoD:** ผ่าน checklist A01–A10 เท่าที่เกี่ยวกับ Phase 1

---

## ลำดับความสำคัญ / เส้นทางวิกฤต
`Step 1 → 2 → 3` คือหัวใจความปลอดภัย multi-tenant ต้องแน่นก่อนขึ้น Step อื่น
Step 4 (seed) ทำคู่ขนานได้ | Step 5–7 ตามลำดับ | Step 8 ทำต่อเนื่องทุก step (ไม่ใช่แค่ตอนจบ)

## สิ่งที่ต้องถาม/ยืนยันก่อนเริ่มโค้ดจริงบางสเต็ป
- Supabase: ใช้ cloud project หรือ local (CLI/Docker)? → กระทบ Step 1
- ORM/DB access: SQLAlchemy+asyncpg หรือ supabase-py? → กระทบ Step 5
- Package manager frontend: npm / pnpm? → กระทบ Step 7
