# DEVELOPMENT_PLAN — app_Evaluation_System (E-Appraisal)

> แผนพัฒนาแบบแบ่งเฟส — **map** ระดับเฟส. รายละเอียดรายสเต็ป + บั๊กที่เจอจริง → [PROJECT_STATUS.md](PROJECT_STATUS.md)
> แผนเก่ารายสเต็ป (Phase 1/2 ตอนเริ่ม) เก็บไว้ที่ [`archive/`](archive/)
> กติกา suite → [`../../platform-core/docs/CONVENTIONS.md`](../../platform-core/docs/CONVENTIONS.md)

**สถานะรวม:** live บน production (`e-appraisal-api`), P1–P7 + P9 เสร็จ. เหลือเป็นงานเลือก/รอ HR (ดูท้ายไฟล์)

---

## เฟส

| เฟส | เป้าหมาย | ส่งมอบหลัก | สถานะ |
|---|---|---|---|
| **P1 · Foundation** | โครง + multi-tenant auth | schema (`companies`/`branches`/`employees`/`profiles`/`roles` + criteria BARS), RLS ทุกตาราง, Supabase Auth (JWKS/ES256 verify) + custom access token hook (claims), RBAC, provisioning (super_admin → tenant + clone template + hr_admin), `audit_logs` append-only, OWASP baseline, React shell | ✅ |
| **P2 · Evaluation feature** | ให้คะแนน + สายอนุมัติ | `evaluation_cycles`/`evaluations`/`evaluation_items` (snapshot)/`evaluation_scores` (1–5 step .5)/`comments`/`attendance`; workflow หลายชั้น routed ตามสายจริง (supervisor→dept_manager→gm/md→hr finalize); `evaluation_approvals` append-only; BARS anchors ใน snapshot; approval inbox; role-based UI (ปุ่มตามสถานะ×สิทธิ์); read-visibility policy | ✅ |
| **P3 · Reporting** | export ผลประเมิน | PDF (ReportLab + bundled Sarabun OFL font + Thai-stacking fix + XML escape); Excel 2 sheet (สรุป + รายละเอียด) + filter สถานะ/ช่วงวันที่; หน้าเปรียบเทียบ 2–5 ใบ (pivot, บังคับสิทธิ์เท่าเปิดใบเดี่ยว) | ✅ |
| **P4 · Admin tooling** | HR/super_admin จัดการเองได้ | tenant mgmt (create/**suspend มี enforcement จริง**/invite); employee & branch mgmt + CSV import (two-pass, idempotent, per-row SAVEPOINT); self-service invite (hr_admin); user account status (ban/unban ผ่าน GoTrue); ถอด role เดียว (revoke); **multi-company account switching** (`0021`, PK `user_roles` +company_id, auth hook scope ตามบริษัท active); super_admin per-company scoping; `employees.email` field (`0018`) + UI/CSV | ✅ |
| **P5 · Attendance scoring** | คะแนนมา-ลาเข้าใบประเมิน | HR เป็นเจ้าของข้อมูล (หัวหน้า read-only), auto-calc + HR override (อยู่รอดการแก้ข้อมูลดิบ), bulk CSV import (เคารพ override), **สูตรปรับได้ต่อ tenant** (`company_attendance_formula`, `0017`) | ✅ |
| **P6 · Employee acknowledgement (paper)** | บันทึกว่าพนักงานรับทราบผล | `evaluation_acknowledgements` append-only (`0018`), decision 3 แบบ (acknowledged / acknowledged_disagreed / refused) — "รับทราบ" ≠ "เห็นด้วย"; paper mode (HR บันทึกแทน + สแกนลายเซ็นใน private bucket `0019`); **ย้ายเข้าสายอนุมัติ** (`0020`: dept_approved → พนักงานเซ็น → gm/md → hr finalize; supersede เมื่อ return-to-draft) | ✅ (electronic/magic-link = deferred) |
| **P7 · Ops & hardening** | ทน production | forgot-password (Supabase recovery + config เข้มขึ้น) + password-changed notice; transactional email = **Brevo HTTP API** (เดิม SMTP — Render บล็อก); daily digest email; **Python 3.9→3.11** (pip-audit 35→0, ลบ `python-jose` ที่ไม่ใช้); unified nav bar + user/company/branch badge; frontend cold-start retry + `meError`; mobile responsive fixes; PDF Thai rendering fix; keep-alive ping (UptimeRobot); pilot deploy (Render + Vercel + Supabase Cloud) | ✅ (ต่อเนื่อง) |
| **P9 · Shared platform library** | ลดโค้ดซ้ำข้าม suite | `email` + `auth_admin` (`create_auth_user`/`set_user_ban`) → shim เหนือ `hr_platform_core` ([platform-core §12](../../platform-core/docs/PLATFORM_ARCHITECTURE.md)) | ✅ |

---

## Cross-cutting (DoD ทุก PR — ดู [CONVENTIONS §10](../../platform-core/docs/CONVENTIONS.md))
RLS + tenant isolation + negative cross-tenant test · audit ทุก mutation (ใน transaction) · input validation · security review · อัปเดต `PROJECT_STATUS.md`

---

## ยังไม่ทำ / เลือกทำต่อ
| งาน | หมายเหตุ |
|---|---|
| **Electronic acknowledgement (magic-link email)** | เคาะไว้แล้ว: แยกบัญชี Gmail/Brevo จากที่ส่งสลิปเงินเดือน — ยังไม่เริ่ม |
| **Branch-level access control** | ตอนนี้ "สาขา" เป็น descriptive ไม่ใช่ขอบเขตสิทธิ์ — ทำจริงต้อง RLS ระดับสาขา (ฟีเจอร์แยก) |
| **Sensitive-read audit expansion** | `GET /api/evaluations/{id}` / `GET /api/employees/{id}` ยังไม่ log (จะเพิ่ม write ทุก GET — คุยทีมก่อน) |
| **evaluation_cycles UI** | ตาราง cycle มีแล้ว แต่ยังไม่มี UI สร้าง/เลือก cycle |
| **รอ HR** | ยืนยันสูตรคะแนน attendance (default 40/4/1/0.5/1), ตรวจถ้อยคำ BARS anchors (`exports/evaluation-criteria-bars.docx`) |

## 🔒 การตัดสินใจที่ล็อกแล้ว (อย่าเปลี่ยนโดยไม่คุย)
| หัวข้อ | ค่า |
|---|---|
| Tenant model | SaaS multi-tenant, tenant = `companies`, isolate ด้วย company_id + RLS |
| Criteria | BARS template-driven; master default + clone ต่อ tenant; ไม่ hardcode |
| Roles | super_admin, hr_admin, gm, md, dept_manager, manager(supervisor), employee |
| Login scope | HR/Admin + หัวหน้า มีบัญชี; พนักงานทั่วไปเป็น record (ยังไม่มี login) |
| "รับทราบ" ≠ "เห็นด้วย" | acknowledgement มี decision 3 แบบ + ช่องความเห็นแย้ง (หลักฐานชั้นศาลแรงงาน) |
| DB access | SQLAlchemy + asyncpg (async); `hr_platform_core` เฉพาะ GoTrue admin + email |
