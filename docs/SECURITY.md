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

### super_admin ดูข้อมูลพนักงาน/สาขา/user แยกตามบริษัท (`/api/employees`, `/api/branches`, `/api/users`, `/api/users/invite`)
`is_super_admin()` bypass RLS ทั้งหมดตามดีไซน์ — endpoint พวกนี้เดิมพึ่ง RLS กรอง company ให้โดยนัย (ใช้ได้กับ hr_admin เพราะ company_id ของตัวเองคือ tenant ที่ดูแลอยู่แล้ว) แต่สำหรับ super_admin กลายเป็นดึงข้อมูล**ทุกบริษัทมารวมกันในลิสต์เดียวไม่มีทางแยก** — พบจากการทดสอบจริงของผู้ใช้ (หน้า "พนักงาน & สาขา" ปนพนักงาน/user จากหลายบริษัทไม่มีคอลัมน์บอกบริษัท)
- **แก้โดย explicit `company_id` query param** (pattern เดียวกับ `tenant_admin.py` ที่ใช้กับ super_admin cross-tenant มาก่อนแล้ว) — `_resolve_company()` ใน `routes.py`: ถ้ามี `company_id` แต่ผู้เรียกไม่ใช่ super_admin → 403 ทันที (กัน hr_admin ใช้ param นี้สอดแนมบริษัทอื่น); ถ้าไม่ส่งมาเลย พฤติกรรมเดิมไม่เปลี่ยน (hr_admin ยังพึ่ง RLS implicit ตามเดิม)
- **UI**: nav "พนักงาน & สาขา" เอาออกจาก super_admin แล้ว (เหลือ hr_admin เท่านั้น) — super_admin เข้าถึงต่อบริษัทผ่านปุ่ม "จัดการพนักงาน & สาขาของบริษัทนี้" ใน `TenantDetail.tsx` เท่านั้น ส่ง `company_id` มาใน URL เสมอ ไม่มีทางเข้าแบบไม่ระบุบริษัท
- **ขอบเขตที่ตั้งใจไม่ครอบคลุม**: import พนักงาน/attendance CSV และตั้งสูตรคะแนนการมา-ลา ยังไม่รับ `company_id` explicit — ซ่อน UI ส่วนนี้ไว้เมื่อ super_admin เข้าผ่าน `?company_id=` (ต้องให้ hr_admin ของบริษัทนั้น login เองทำแทน) กันไม่ให้เขียนข้อมูลเข้าบริษัท Platform ของ super_admin โดยไม่ตั้งใจ
- พิสูจน์: pytest 102/102 ผ่าน (ไม่มี regression), ทดสอบจริงผ่าน browser (สร้าง 2 บริษัท คนละพนักงาน → เข้าดูแยกกันถูกต้อง, เชิญ user ผ่านหน้า Company A → ยืนยันด้วย SQL ว่า `profiles.company_id` ตรงกับ Company A ไม่ใช่ platform tenant), ทดสอบ negative ผ่าน curl (hr_admin ส่ง `?company_id=` ของบริษัทอื่น → 403 ตามคาด)

### สร้างใบประเมิน: template ต้องเป็นของบริษัทเดียวกับพนักงาน ไม่ใช่ของผู้กระทำ (`services/evaluations.create`)
พบระหว่างไล่ดูสาเหตุจริงของบั๊ก "เมนูแบบฟอร์มซ้ำๆ กัน" ที่ผู้ใช้ report (หน้า "ใบประเมินผล" → สร้างใบประเมิน) — ตอนแรกดูเหมือนแค่ dropdown ซ้ำ แต่ไล่โค้ดจริงเจอบั๊กที่ลึกกว่านั้น 2 ชั้น:
1. **`GET /api/templates` ไม่กรอง company เลย** เหมือนบั๊กพนักงาน/user ก่อนหน้านี้ (RLS bypass ทั้งหมดสำหรับ super_admin) — แถมยังโชว์ master template (`company_id is null`, มีไว้เป็นต้นแบบสำหรับ clone ตอน provisioning เท่านั้น) ปนกับสำเนาของแต่ละบริษัทด้วย ทำให้ super_admin เห็นชื่อซ้ำกัน N+1 ครั้ง (N = จำนวนบริษัท) — **แก้โดยตัด master ออกจากลิสต์ที่เลือกได้เสมอ** (ทุก role ไม่ใช่แค่ super_admin เพราะ hr_admin ปกติก็เห็น master ปนกับของตัวเองมาตลอดเป็น 2 ตัวเลือกซ้ำที่ไม่มีใครควรกดเลือก master โดยตรง)
2. **บั๊กที่ร้ายแรงกว่า: `evaluations.company_id` เดิมตั้งจาก `user.company_id` (ผู้กระทำ) ไม่ใช่จากพนักงานที่ถูกประเมิน** — สำหรับ hr_admin/supervisor ทั่วไปสองค่านี้เท่ากันเสมออยู่แล้ว (RLS ไม่ให้เลือกพนักงานข้ามบริษัทได้ตั้งแต่แรก) แต่สำหรับ **super_admin ผู้กระทำ = platform tenant เสมอ** — ถ้า super_admin สร้างใบประเมินให้พนักงานบริษัทจริง ใบนั้นจะถูกบันทึกลง company_id ของ platform tenant แทน **กลายเป็นใบที่บริษัทเจ้าของพนักงานตัวจริงมองไม่เห็นเลย** (RLS ของบริษัทนั้นกรองไม่เจอ) — เช็คแล้วบน production **ยังไม่มีข้อมูลเสียหายจริง** (`select count(*) from evaluations where company_id = platform_id` = 0) แต่เป็นบั๊กจริงที่พร้อมเกิดถ้าใช้ฟีเจอร์นี้ต่อไป
   - **แก้:** `target_company = emp["company_id"]` (ดึงจากพนักงานที่เลือก ไม่ใช่ผู้กระทำ) ใช้ทั้งตอน insert `evaluations.company_id` และตอนเขียน audit log
   - **เพิ่มการตรวจสอบใหม่:** `template_id` ที่ส่งมาต้อง `criteria_templates.company_id = target_company` เป๊ะ (ไม่ null, ไม่ใช่บริษัทอื่น) ไม่งั้น 400 — กันไม่ให้ผสมพนักงานบริษัท A เข้ากับเกณฑ์ประเมิน (BARS ที่ปรับแต่งได้ต่อบริษัท) ของบริษัท B
- พิสูจน์: negative test ใหม่ 2 เคส (`test_create_rejects_template_from_another_company`, `test_create_rejects_master_template_directly`) + pytest ทั้งชุด 114/114 ผ่าน

### ปิดใช้งานบัญชี login (`0022_user_account_status.sql`, `PATCH /api/users/{id}/status`)
คนลาออกแล้วต้อง revoke การเข้าระบบได้ทันที — เดิมไม่มีทางทำเลย มีแต่ "ระงับทั้งบริษัท" ซึ่งกระทบทุกคน
- **Ban ที่ระดับ Supabase Auth** (`auth_admin.set_user_ban`, `ban_duration` ผ่าน GoTrue admin API) ไม่ใช่แค่ถอด `user_roles` — เพราะแค่ถอด role ยังไม่บล็อกไม่ให้เห็นข้อมูลพื้นฐานของบริษัท (RLS กันแค่ข้ามบริษัท ไม่ได้เช็ค role ทุก endpoint) ต้อง block ที่ชั้น authentication เองถึงจะเชื่อถือได้จริง — **ไม่ลบ profile/user_roles** เพื่อให้ใบประเมินเก่าที่คนนั้นเคยให้คะแนน/อนุมัติ/ถูกประเมิน ยังอ้างอิงถึงได้ครบ (audit trail ไม่ขาด)
- **กันตัวเองปิดบัญชีตัวเอง:** `set_user_status` เช็ค `profile_id == actor_id` → 400 ทันที (กันล็อกตัวเองออกจากระบบโดยไม่ตั้งใจ)
- **ตรวจว่า user เป็นของบริษัทที่กำลังจัดการอยู่จริง** ก่อน ban ทุกครั้ง (`where id = :pid and company_id = :cid`) — ใช้ company scoping pattern เดียวกับ `_resolve_company()` ด้านบน (hr_admin ปิดได้เฉพาะบริษัทตัวเอง, super_admin ระบุ `company_id` ได้)
- **`auth.users.banned_until` อ่านผ่าน SECURITY DEFINER เท่านั้น** (`app.list_company_users`) เพราะ session ปกติอ่าน `auth.users` ตรงไม่ได้ (เหตุผลเดียวกับ `find_profile_by_email` ใน `0021`) — self-guard: `is_super_admin() or p_company_id = current_company_id()`
- พิสูจน์: pytest ใหม่ 4 เคส (`test_user_account_status.py`) ทดสอบ login จริงหลัง ban/unban ผ่าน GoTrue จริง (ไม่ mock) + ยืนยันซ้ำด้วย manual E2E ผ่าน curl (invite → deactivate → login ได้ 400 → reactivate → login ได้ 200) รวม pytest ทั้งชุด 112/112

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
