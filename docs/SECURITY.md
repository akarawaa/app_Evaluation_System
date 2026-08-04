# Security by Design — OWASP Top 10 (2021) Mapping

> เอกสารนี้ผูกแต่ละความเสี่ยง OWASP กับ **มาตรการที่ออกแบบไว้ในระบบ** ใช้เป็น checklist ตอนรีวิวทุกฟีเจอร์
> หลักการรวม: **Deny by default, Defense in depth, Least privilege, ไม่เชื่อ input จาก client**

## A01 — Broken Access Control  *(ความเสี่ยงสูงสุดของระบบ multi-tenant)*
- **Tenant isolation:** RLS ทุกตาราง (`company_id = auth.jwt()->>'company_id'`) — ชั้นบังคับที่ DB
- **RBAC:** ตรวจ role ที่ service layer ก่อนทุก action; deny เป็น default
- **ไม่รับ `company_id`/`user_id` จาก request body** — ดึงจาก JWT ที่ตรวจแล้วเท่านั้น
- **IDOR ป้องกัน:** เข้าถึง resource by id ต้องผ่าน RLS + ตรวจความเป็นเจ้าของ/สายบังคับบัญชา
- `super_admin` ข้าม tenant ได้เฉพาะผ่าน security-definer function ที่ตรวจ role ชัดเจน
- **Test บังคับ:** negative test — user tenant A เรียก resource tenant B ต้องได้ 404/403

### Multi-company account switching (`0021_multi_company_access.sql`)
1 login ผูกได้หลายบริษัท (`user_roles.company_id` ต่อ role) — `profiles.company_id` คือ "บริษัทที่ active อยู่ตอนนี้" ไม่ใช่บริษัทตายตัว
- **สลับได้เฉพาะบริษัทที่มี role อยู่แล้วเท่านั้น:** `app.switch_active_company()` เป็น `SECURITY DEFINER`, ตรวจ `user_roles` ของ `sub` claim (จาก JWT ที่ตรวจลายเซ็นแล้วเท่านั้น ไม่รับ client-supplied id ใด ๆ) ก่อน update — สลับไปบริษัทที่ไม่มีสิทธิ์ → คืน `false` → route ตอบ 403 เสมอ ไม่มี path ที่ bypass การเช็คนี้ได้
- **`roles` claim ต้อง scope ตามบริษัท active เท่านั้น:** เดิม auth hook (`0007`) รวม role code ข้ามบริษัททั้งหมดของ profile — แก้แล้วให้ filter `ur.company_id = v_company_id` ไม่งั้น role ของบริษัทที่ไม่ได้ active อยู่จะหลุดเข้า JWT ได้ (มี negative test คุมไว้ที่ `test_roles_claim_is_scoped_to_active_company`)
- **มอบสิทธิ์บริษัทที่สองได้เฉพาะ `super_admin`:** ป้องกัน hr_admin ของบริษัท A ให้สิทธิ์ตัวเองเข้าบริษัท B โดยที่ B ไม่ยินยอม (privilege escalation) — endpoint `/api/admin/tenants/{id}/users/grant` gate ด้วย `require_roles()` (super_admin only) เหมือน endpoint admin อื่น ๆ
- **audit_logs ยึด company ขาออกเสมอ** (ไม่ใช่ปลายทาง) เพราะ RLS ของ audit_logs เอง (`company_id = current_company_id()`) ยังอ้างอิง JWT เดิมก่อน refresh — ป้องกันไม่ให้เขียน audit log ข้าม company ที่ยังไม่มีสิทธิ์จริงในเซสชันนั้น

## A02 — Cryptographic Failures
- **In transit:** HTTPS/TLS ทุก endpoint (บังคับ), HSTS
- **At rest:** Supabase Postgres เข้ารหัส disk; ข้อมูลอ่อนไหว (PDPA) ไม่เก็บเกินจำเป็น
- **Passwords:** จัดการโดย Supabase Auth (bcrypt) — เราไม่เก็บ/เห็น password เอง
- **Secrets:** อยู่ใน env vars เท่านั้น, ไม่ commit (ดู .gitignore), หมุน key ได้
- **JWT:** เซ็นด้วย secret ของ Supabase; ฝั่งเราตรวจลายเซ็นเสมอ ไม่ decode แบบไม่ verify

## A03 — Injection
- **SQL:** ใช้ parameterized queries / query builder เท่านั้น ห้าม string concat SQL
- **Input validation:** Pydantic (backend) + zod (frontend) ทุก payload
- **Output:** React escape by default; ระวัง `dangerouslySetInnerHTML`
- PDF/Report (Phase 3): sanitize ข้อมูลก่อน render

## A04 — Insecure Design
- Threat modeling ต่อฟีเจอร์ (ดูตาราง threat ด้านล่าง)
- แยก environment, least privilege ตั้งแต่ออกแบบ schema
- เอกสารชุดนี้เอง = ส่วนหนึ่งของ secure SDLC

## A05 — Security Misconfiguration
- `DEBUG=false` และซ่อน stack trace ใน staging/production
- **CORS allowlist** เฉพาะ origin ของ frontend เรา (ไม่ `*`)
- **Security headers:** HSTS, X-Content-Type-Options, X-Frame-Options/CSP, Referrer-Policy
- **RLS บังคับเปิด** ทุกตาราง (ตรวจว่าไม่มีตารางไหนลืมเปิด = ช่องโหว่)
- ปิด default/แอดมินเริ่มต้นที่ไม่ใช้; error message ไม่รั่วรายละเอียดภายใน

## A06 — Vulnerable & Outdated Components
- Pin dependency (`requirements.txt` / lockfile) + `pip-audit`, `npm audit` ใน CI
- Dependabot/renovate อัปเดตความปลอดภัย
- ใช้เฉพาะ dependency ที่จำเป็น

## A07 — Identification & Authentication Failures
- Supabase Auth: session/JWT มี expiry + refresh token rotation
- **Rate limiting** ที่ login/API (กัน brute force / credential stuffing)
- รองรับ MFA (เปิดผ่าน Supabase) — แนะนำบังคับสำหรับ `hr_admin`/`super_admin`
- Password policy ตาม Supabase; ล็อก/แจ้งเตือนเมื่อ login ล้มเหลวหลายครั้ง (ดู A09)

## A08 — Software & Data Integrity Failures
- **JWT verify signature** เสมอ (ไม่รับ token ที่ไม่ผ่านการตรวจ)
- Lockfile + ตรวจ integrity ของ dependency; CI ที่เชื่อถือได้
- **Audit log แบบ append-only** (ไม่มี UPDATE/DELETE) → ข้อมูลตรวจสอบไม่ถูกแก้ย้อน (option: hash chaining)

## A09 — Security Logging & Monitoring Failures
- ระบบ log/audit เต็มรูปแบบ → ดู [LOGGING_AND_AUDIT.md](LOGGING_AND_AUDIT.md)
- บันทึก: login สำเร็จ/ล้มเหลว, การเข้าถึงข้อมูลอ่อนไหว, การแก้/ลบข้อมูล, admin actions
- **ไม่ log ข้อมูลลับ** (password, token, PII เต็ม) — PDPA
- แจ้งเตือนเหตุผิดปกติ (login ล้มเหลวถี่, การเข้าถึงข้าม tenant ที่ถูก block)

## A10 — Server-Side Request Forgery (SSRF)
- ระบบไม่ควรยิง request ไป URL ตาม input ผู้ใช้; ถ้าจำเป็น (เช่น webhook Phase หลัง) ใช้ allowlist
- PDF generation ใช้ข้อมูลภายใน ไม่ fetch external URL ตาม input

---

## Threat Model (ย่อ) — Phase 1
| Threat | Asset | มาตรการ |
|---|---|---|
| ผู้ใช้บริษัท A เห็นข้อมูลบริษัท B | คะแนนประเมิน, ข้อมูลพนักงาน | RLS + tenant guard + negative test (A01) |
| ปลอม `company_id` เพื่อข้าม tenant | tenant boundary | company_id มาจาก JWT เซ็นแล้ว ไม่รับจาก client (A01/A08) |
| ยึด account (brute force) | บัญชีผู้ใช้ | rate limit + MFA + lockout + log (A07/A09) |
| แก้คะแนนย้อนหลังแบบลบร่องรอย | ความน่าเชื่อถือผลประเมิน | audit append-only (A08/A09) |
| SQL injection ผ่านฟอร์ม | ทั้งฐานข้อมูล | parameterized + validation (A03) |
| Secret รั่วผ่าน git | คีย์ระบบ | .gitignore + .env.example + secret scanning (A02) |

## PDPA (พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล — ไทย)
- ข้อมูลผลงาน/การจ้างงาน = ข้อมูลส่วนบุคคลอ่อนไหว
- เก็บเท่าที่จำเป็น (data minimization), กำหนด retention, รองรับสิทธิ์เจ้าของข้อมูล
- Audit การเข้าถึงข้อมูลอ่อนไหว

## Security checklist (ใช้ตอน PR review)
- [ ] ตาราง/endpoint ใหม่มี tenant isolation (RLS + guard)?
- [ ] Authorization ตรวจ role ก่อน action?
- [ ] Input ผ่าน validation?
- [ ] ไม่มี secret ใน diff?
- [ ] มี audit log สำหรับการเขียน/แก้/ลบ?
- [ ] มี negative test ข้าม tenant?
- [ ] Error ไม่รั่วข้อมูลภายใน?
