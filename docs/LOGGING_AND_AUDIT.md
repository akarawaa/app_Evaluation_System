# Logging & Audit — E-Appraisal

> ระบบบันทึกมี **2 ชั้นแยกกันชัดเจน** อย่าปนกัน:
> 1. **Application / System Log** — เชิงเทคนิค (debug, error, performance) → ไฟล์/stdout, ไม่เก็บถาวรในฐานข้อมูลธุรกิจ
> 2. **Audit Log** — เชิงธุรกิจ/ความปลอดภัย (ใคร ทำอะไร กับข้อมูลไหน เมื่อไร) → ตาราง `audit_logs` แบบ append-only

รองรับ OWASP **A09 (Security Logging & Monitoring)** และ **A08 (Data Integrity)**

---

## 1. Application / System Log
- **รูปแบบ:** Structured JSON (1 บรรทัด/1 event) — ค้น/ส่งเข้า SIEM ได้ง่าย
- **ฟิลด์มาตรฐาน:** `timestamp, level, logger, message, request_id, method, path, status_code, latency_ms, user_id(masked), company_id`
- **Request ID / Correlation ID:** สร้างต่อ request (middleware) แนบทุก log ของ request นั้น → ไล่ trace ได้
- **Level:** DEBUG (local only), INFO, WARNING, ERROR, CRITICAL
- **ปลายทาง:** stdout (dev), รวมศูนย์ log ระยะยาว = Phase หลัง
- **ห้าม log:** password, JWT/token, ข้อมูล PII เต็ม (เบอร์/บัตร ปชช.) — mask เช่น `user_id=***a1b2`

## 2. Audit Log (ตาราง `audit_logs`)

### เหตุการณ์ที่ต้องบันทึก (Phase 1)
| หมวด | ตัวอย่าง action |
|---|---|
| **Auth** | `login_success`, `login_failed`, `logout`, `password_reset` |
| **Access control** | `access_denied`, `cross_tenant_blocked` |
| **Data mutation** | `create` / `update` / `delete` บน employees, branches, criteria_*, user_roles |
| **Sensitive read** | `view_employee`, `export_data` (การเข้าถึงข้อมูลอ่อนไหว) |
| **Admin / Platform** | `tenant_created`, `role_granted`, `role_revoked`, `user_invited` |

> Phase 2 เพิ่ม: `evaluation_submitted`, `score_changed`, `evaluation_approved` ฯลฯ

### โครงสร้าง (สรุป — รายละเอียดใน DATA_MODEL.md)
`id, company_id, actor_profile_id, action, entity_type, entity_id, before(jsonb), after(jsonb), ip, user_agent, created_at`

### กติกาความสมบูรณ์ (Integrity)
- **Append-only:** RLS ให้ SELECT/INSERT เท่านั้น — **ไม่มี** policy UPDATE/DELETE
- **Tenant-scoped:** อ่านได้เฉพาะ audit ของ company ตัวเอง (super_admin เห็นข้ามได้ผ่าน security-definer)
- **before/after:** เก็บเฉพาะ field ที่เปลี่ยน และ **ตัด field ลับออก** ก่อนเก็บ (allowlist ฟิลด์)
- **(Option) Hash chaining:** เก็บ `prev_hash` เพื่อพิสูจน์ว่าไม่มีการลบแถวกลางทาง — พิจารณา Phase หลัง

### ใครเขียน audit
- เขียนที่ **service layer** (จุดเดียว) ผ่าน helper `audit(action, entity, before, after)` — ไม่กระจายตาม router
- ต้องอยู่ใน transaction เดียวกับการแก้ข้อมูล (แก้สำเร็จ = ต้องมี audit, ล้มเหลว = rollback ทั้งคู่)

## 3. Monitoring & Alert (ออกแบบไว้ ทำจริง Phase หลัง)
- Alert เมื่อ: `login_failed` ถี่ผิดปกติต่อ user/IP, `cross_tenant_blocked` เกิดขึ้น, error rate สูง
- Metric: request latency, error count, auth failure rate

## 4. Retention (PDPA)
- Application log: ~30–90 วัน
- Audit log: เก็บยาวตามข้อกำหนด HR/กฎหมาย (เช่น ตามอายุการจ้างงาน) — กำหนดนโยบายร่วมกับลูกค้า/ฝ่ายกฎหมาย

## 5. Definition of Done (เรื่อง logging)
- [ ] ทุก mutation มี audit entry (ใน transaction เดียวกัน)
- [ ] ไม่มีข้อมูลลับใน log/audit
- [ ] audit อ่านข้าม tenant ไม่ได้
- [ ] audit แก้/ลบไม่ได้ (ทดสอบ)
- [ ] ทุก request มี request_id
