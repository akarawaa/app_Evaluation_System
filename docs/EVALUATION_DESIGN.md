# Evaluation Domain Design — Phase 2

> อ้างอิงใบ FMHR07 (`docs/evaluation-form-analysis.md`) + การตัดสินใจ Phase 2
> ทุกตารางยัง **tenant-scoped (`company_id`) + RLS + audit** ตามกติกาเดิม (ดู SECURITY / LOGGING_AND_AUDIT)

## การตัดสินใจที่ล็อก (Phase 2)
| หัวข้อ | ค่าที่เลือก |
|---|---|
| ชนิดใบประเมิน | **annual** (ประจำปี) + **probation** (ทดลองงาน: checkpoint 30/60/90/119 วัน) |
| ผู้ให้คะแนน | หัวหน้างานให้คะแนน (ไม่มี self-assessment) |
| Workflow | หลายชั้น: พนักงาน → หัวหน้า → ผจก.แผนก → MD → HR (สรุป/ปิดใบ) |
| การคิดคะแนน | เท่ากันทุกข้อ (sum) → eval 140/210 + attendance 40 → % |
| Snapshot เกณฑ์ | **snapshot ตอนสร้างใบ** — แก้ template ภายหลังไม่กระทบใบเก่า |

## Entities (ระดับ concept)

### evaluation_cycles *(สำหรับ annual — จัดรอบเป็นชุด)*
`id, company_id, name, year, period_start, period_end, default_template_id, status(open|closed)`
> probation ไม่ต้องผูก cycle (ผูกกับ checkpoint ของพนักงานตรง ๆ)

### evaluations *(หัวใบ)*
`id, company_id, cycle_id(null), employee_id, evaluator_id, template_id,`
`kind('annual'|'probation'), probation_checkpoint(null|'30'|'60'|'90'|'119'),`
`period_start, period_end,`
`status('draft'|'submitted'|'dept_approved'|'md_approved'|'finalized'|'returned'),`
`eval_score, eval_max, attendance_score, total_score, percentage,`
`probation_decision(null|'hire'|'not_hire'|'extend'|'other'), probation_extend_days, decision_note,`
`snapshot_at, submitted_at, finalized_at, created_at, updated_at`
- UNIQUE(company_id, employee_id, cycle_id) เมื่อ annual; UNIQUE(company_id, employee_id, kind, probation_checkpoint) เมื่อ probation
- CHECK: evaluator_id ≠ employee_id

### evaluation_items *(snapshot ของ criteria ตอนสร้างใบ)*
`id, evaluation_id, company_id, category_order, category_name, item_order, item_name, weight, source_item_id`
> คัดลอกจาก criteria ของ template ณ เวลาสร้าง → คะแนนอ้างอิง snapshot นี้ ไม่ใช่ template สด

### evaluation_scores
`id, evaluation_id, company_id, evaluation_item_id, score`
- CHECK `score >= 1 and score <= 5 and (score*2)=trunc(score*2)` (step 0.5)
- UNIQUE(evaluation_id, evaluation_item_id)

### evaluation_comments *(ระดับหมวด — "ข้อคิดเห็นเพิ่มเติม")*
`id, evaluation_id, company_id, category_order, comment`

### evaluation_attendance
`evaluation_id(PK), company_id, sick_days, personal_days, late_count, late_minutes, absent_days, attendance_score`
> **สูตรแปลงข้อมูลมา-ลา → attendance_score (เต็ม 40) ยังไม่รู้ — รอ HR** (ทำเป็น config ได้)

### Workflow
Chain คงที่ใน Phase 2 (config table เลื่อนเป็น enhancement):
`supervisor_submit → dept_manager_approve → md_approve → hr_finalize` (+ return)

**evaluation_approvals** *(บันทึกการอนุมัติแต่ละชั้น — append-only)*
`id, company_id, evaluation_id, step('dept_manager'|'md'|'hr'), actor_id, decision('approved'|'returned'), comment, decided_at`
> `evaluations.status` เดินตามความคืบหน้าของ approvals

## Workflow state machine (ค่าเริ่มต้น)
```
draft ──(หัวหน้า submit)──► submitted
submitted ──(ผจก.แผนก approve)──► dept_approved ──(MD approve)──► md_approved
md_approved ──(HR สรุป/ปิด)──► finalized
[ทุกชั้น] ──(return)──► returned ──(หัวหน้าแก้)──► draft
```
- คะแนนแก้ได้เฉพาะสถานะ `draft`/`returned` (หลัง submitted ล็อก — enforce ที่ service + ตรวจสถานะ)
- HR = ผู้สรุป/ปิดใบ (ขั้นสุดท้าย) ไม่ใช่ผู้อนุมัติกลางสาย

## Roles ที่ต้องเพิ่ม (seed)
เดิม: `super_admin, hr_admin, manager, employee`
เพิ่ม: **`dept_manager`** (ผจก.แผนก), **`md`** (กรรมการผู้จัดการ)

## Approval routing = ตามสายบังคับบัญชาจริง (hybrid)
resolve ผู้อนุมัติแต่ละชั้นจากตัวพนักงานที่ถูกประเมิน:
| ชั้น | ผู้กระทำ | resolve จาก |
|---|---|---|
| ให้คะแนน (หัวหน้า) | `employee.supervisor_id` | สายตรง |
| อนุมัติ ผจก.แผนก | `employee.manager_id` | สายตรง |
| อนุมัติ MD | ผู้ถือ role `md` ใน tenant | role-based (มักมีคนเดียว) |
| สรุป/ปิด (HR) | ผู้ถือ role `hr_admin` | role-based (HR ไม่อยู่ในสายงาน) |
| รับทราบ (พนักงาน) | `evaluation.employee_id` เอง | — |

**Authorization การอนุมัติ:** ผู้กระทำต้องเป็น "บุคคลที่ resolve ได้" (line levels: `profiles.employee_id` == ผู้อนุมัติที่ resolve) หรือถือ role ของชั้นนั้น (MD/HR) — ตรวจที่ service + 403 ถ้าไม่ตรง
**Prereq:** พนักงานต้องมี `supervisor_id`/`manager_id` ครบ และผู้อนุมัติต้องมี profile ผูก `employee_id`; ถ้าขาด → สร้างใบไม่ได้/แจ้ง error ชัดเจน
> evaluator_id ของใบ = `employee.supervisor_id` ณ เวลาสร้าง

## การคิดคะแนน (equal weight)
- `eval_score = Σ score` (ทุก item), `eval_max = item_count × 5` (140 หรือ 210)
- `total_score = eval_score + attendance_score`, `percentage = total_score / (eval_max + 40) × 100`
- คำนวณตอน submit และ recompute ตอน finalize

## Security / Audit
- RLS ทุกตาราง `company_id = current` (+ super_admin) เหมือน Phase 1
- audit: `evaluation_created, score_saved, evaluation_submitted, evaluation_approved, evaluation_returned, evaluation_finalized` — เขียนใน tx เดียวกับการเปลี่ยนข้อมูล
- `evaluation_approvals` append-only (ไม่มี update/delete policy)
- negative test: ข้าม tenant ไม่ได้ + คนไม่ตรง role อนุมัติชั้นนั้นไม่ได้ (403)

## ✅ สมมุติฐานที่ยืนยันแล้ว
1. **Approval routing = ตามสายบังคับบัญชาจริง** (ดูตารางด้านบน) — line levels ตาม supervisor_id/manager_id, MD/HR ตาม role
2. ขั้น "พนักงาน" = การรับทราบ/ลงนามหลังหัวหน้าให้คะแนน (ไม่ได้ให้คะแนนเอง)
3. attendance_score กรอกมือไปก่อน (สูตรจาก HR ทีหลัง)

## Open items (รอ HR)
- สูตรคะแนน attendance (เต็ม 40)
- เนื้อหา BARS `desc_1..5` จริงต่อ item
- probation checkpoint ต่างกันในเกณฑ์/สูตรหรือไม่
