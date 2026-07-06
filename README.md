# E-Appraisal — Performance Evaluation System

ระบบประเมินผลการปฏิบัติงานพนักงานแบบ SaaS Multi-Tenant (รองรับหลายบริษัทลูกค้า) พัฒนาแทนใบประเมินกระดาษ FMHR07

## Tech Stack
- **Backend:** Python (FastAPI)
- **Database / Auth:** Supabase (PostgreSQL + Auth + Row-Level Security)
- **Frontend:** React + Tailwind CSS (Responsive)
- **Reporting:** ReportLab / WeasyPrint (PDF) — Phase 3

## หลักการออกแบบ
- **Multi-Tenant (SaaS):** แยกข้อมูลแต่ละบริษัทด้วย `company_id` + RLS ทุกตาราง
- **Security by Design:** ยึด OWASP Top 10 ตั้งแต่ออกแบบ → ดู [docs/SECURITY.md](docs/SECURITY.md)
- **Auditability:** ทุกการแก้ข้อมูลสำคัญถูกบันทึกใน audit log แบบ append-only → ดู [docs/LOGGING_AND_AUDIT.md](docs/LOGGING_AND_AUDIT.md)
- **BARS (template-driven):** เกณฑ์ประเมินเป็นเทมเพลตปรับได้ ไม่ hardcode

## เอกสารสำคัญ (อ่านก่อนเริ่มงาน)
| ไฟล์ | เนื้อหา |
|---|---|
| [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | **สถานะล่าสุด + จุดส่งต่องาน (อ่านไฟล์นี้ก่อนเสมอ)** |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | สถาปัตยกรรมระบบ, tenancy model |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | โครงสร้างฐานข้อมูล + ความสัมพันธ์ |
| [docs/SECURITY.md](docs/SECURITY.md) | OWASP Top 10 by design + threat model |
| [docs/LOGGING_AND_AUDIT.md](docs/LOGGING_AND_AUDIT.md) | ระบบ log & audit trail |
| [docs/PHASE_1_PLAN.md](docs/PHASE_1_PLAN.md) | แผน Phase 1 แบบทีละขั้น |
| [docs/evaluation-form-analysis.md](docs/evaluation-form-analysis.md) | วิเคราะห์ใบประเมินเดิม (FMHR07) |

## Phases
1. **Phase 1** — Database + Multi-Tenant Auth + RBAC + Criteria/Template foundation *(กำลังทำ)*
2. **Phase 2** — Evaluation UI (BARS scoring) + Approval Workflow
3. **Phase 3** — Reporting & PDF Export

## Status
🚧 Phase 1 — Planning & Foundation (ดู [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md))
