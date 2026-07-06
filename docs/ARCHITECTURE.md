# Architecture — E-Appraisal

## 1. ภาพรวมระบบ

```
                         ┌─────────────────────────┐
                         │   React + Tailwind (SPA) │
                         │  - Auth (Supabase JS)    │
                         │  - Role-based UI         │
                         └───────────┬─────────────┘
                                     │ HTTPS (JWT Bearer)
                         ┌───────────▼─────────────┐
                         │      FastAPI (API)       │
                         │  - Verify Supabase JWT   │
                         │  - Tenant guard          │
                         │  - RBAC / business logic │
                         │  - Structured logging    │
                         └───────────┬─────────────┘
                                     │ Postgres wire (RLS-enforced)
                         ┌───────────▼─────────────┐
                         │        Supabase          │
                         │  - Auth (auth.users)     │
                         │  - PostgreSQL + RLS      │
                         │  - Audit tables          │
                         └──────────────────────────┘
```

## 2. Multi-Tenancy Model
- **รูปแบบ:** Shared database, shared schema, แยกด้วย `company_id` (tenant discriminator)
- **เหตุผล:** เหมาะกับสเกล ~500 คน/บริษัท และหลาย tenant, ต้นทุนต่ำ, ดูแลง่ายกว่า schema-per-tenant
- **กำแพงกันข้อมูลข้าม tenant (ป้องกันซ้อนชั้น / defense in depth):**
  1. **RLS (ชั้นล่างสุด, สำคัญที่สุด):** ทุกตาราง tenant-scoped มี policy `company_id = auth.jwt() ->> 'company_id'`
  2. **App layer:** FastAPI dependency ตรวจ tenant ทุก request (ไม่พึ่ง client ส่ง company_id มา)
  3. **JWT claim:** `company_id` ถูกฝังใน JWT ผ่าน Supabase Auth Hook (custom claims) → ปลอมจากฝั่ง client ไม่ได้เพราะ JWT เซ็นด้วย secret ของ Supabase

## 3. Identity & Access
- **Authentication:** Supabase Auth (email/password, ขยายเป็น OAuth/MFA ได้)
- **Bridge:** `auth.users.id` (uuid) ↔ `profiles.id` ↔ `employees`
- **Authorization (RBAC):**
  - Platform role: `super_admin` (จัดการ tenant, ข้าม company ได้ผ่าน security-definer)
  - Tenant roles: `hr_admin`, `manager`, `employee` (ต่อเติม `dept_manager`, `md` ตอนทำ workflow)
  - เก็บใน `roles` + `user_roles` (many-to-many, รองรับหลาย role ต่อคน)

## 4. Tenant Provisioning Flow (SaaS)
1. `super_admin` สร้าง `company` (tenant)
2. สร้าง `hr_admin` คนแรกของ tenant นั้น
3. ระบบ clone `criteria_template` จาก master default → เป็นของ tenant
4. `hr_admin` จัดการ branches / employees / users ต่อ

## 5. Backend layering (FastAPI)
```
api/          → routers (thin, ต่อ HTTP)
services/     → business logic
repositories/ → data access (Supabase/Postgres)
schemas/      → Pydantic (validation, DTO)
core/         → config, security, logging, deps
```
กติกา: router ห้ามคุย DB ตรง ต้องผ่าน service → repository (ง่ายต่อการ test และคุม security จุดเดียว)

## 6. Environments
- `local` (dev), `staging`, `production` — แยก Supabase project / env vars
- Debug mode / verbose error = เปิดเฉพาะ local เท่านั้น (ดู SECURITY A05)

## 7. สิ่งที่ยังไม่ตัดสิน (Open items)
- กลยุทธ์ JWT claim: Auth Hook (แนะนำ) vs security-definer lookup — จะสรุปตอนลงมือ
- สูตรแปลงคะแนน attendance (max 40) — รอ HR (Phase 2)
- ที่เก็บ log ระยะยาว / SIEM — Phase หลัง
