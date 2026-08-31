# E-Appraisal — Performance Evaluation System

ระบบประเมินผลการปฏิบัติงานพนักงานแบบ SaaS Multi-Tenant (หลายบริษัท) แทนใบประเมินกระดาษ FMHR07
ส่วนหนึ่งของ **HR Suite** — ดู [`../platform-core/docs/PLATFORM_ARCHITECTURE.md`](../platform-core/docs/PLATFORM_ARCHITECTURE.md)

**Stack:** FastAPI + Supabase (Postgres/Auth/RLS/Storage) + React/Tailwind + ReportLab (PDF)
**Production:** `https://e-appraisal-api.onrender.com` · `https://app-evaluation-system.vercel.app`

## เริ่มต้นที่นี่
| ไฟล์ | เนื้อหา |
|---|---|
| [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | **สถานะล่าสุด + จุดส่งต่องาน — อ่านก่อนเสมอ** |
| [CLAUDE.md](CLAUDE.md) | คู่มือ session (identity + non-negotiable เฉพาะแอป) |
| [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) | แผนพัฒนา (เฟส P1–P9) |
| [`../platform-core/docs/CONVENTIONS.md`](../platform-core/docs/CONVENTIONS.md) | กติกา suite (single source) |

## เอกสารอ้างอิง (`docs/`)
| ไฟล์ | เนื้อหา |
|---|---|
| [ANALYSIS.md](docs/ANALYSIS.md) | วิเคราะห์ใบประเมินเดิม (FMHR07) |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | สถาปัตยกรรมแอป, tenancy model |
| [DATA_MODEL.md](docs/DATA_MODEL.md) | โครงสร้างฐานข้อมูล + ความสัมพันธ์ |
| [EVALUATION_DESIGN.md](docs/EVALUATION_DESIGN.md) | ดีไซน์ฟีเจอร์ประเมิน (BARS + workflow) |
| [SECURITY.md](docs/SECURITY.md) | OWASP Top 10 by design + threat model |
| [LOGGING_AND_AUDIT.md](docs/LOGGING_AND_AUDIT.md) | ระบบ log & audit trail |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | ขั้นตอน deploy (+ [suite runbook](../platform-core/docs/DEPLOYMENT.md)) |
| [USER_GUIDE.md](docs/USER_GUIDE.md) · [UX_REVIEW.md](docs/UX_REVIEW.md) | คู่มือผู้ใช้ · ทบทวน UX |
| [archive/](docs/archive/) | แผนเก่าที่ถูกแทนที่ |
