# Phase 2 Plan — Evaluation feature (BARS scoring + multi-level approval)

> ออกแบบ: `docs/EVALUATION_DESIGN.md` — ทุกตาราง tenant-scoped + RLS + audit
> ขอบเขต: annual + probation, หัวหน้าให้คะแนน, workflow หลายชั้น (สายบังคับบัญชา), คะแนนเท่ากันทุกข้อ

## Step 1 — Roles + schema migrations
- [ ] `0010_evaluation_roles.sql` — เพิ่ม role `dept_manager`, `md` (idempotent)
- [ ] `0011_evaluations.sql` — evaluation_cycles, evaluations, evaluation_items (snapshot),
      evaluation_scores (CHECK 1–5 step .5), evaluation_comments, evaluation_attendance
      + FK + index (นำด้วย company_id) + trigger updated_at + **RLS ทุกตาราง**
- [ ] `0012_evaluation_workflow.sql` — evaluation_approvals (append-only) + RLS
- [ ] `0013_evaluation_functions.sql` — `app.snapshot_evaluation_items(eval_id)` (clone criteria→snapshot),
      `app.recompute_evaluation_totals(eval_id)` (equal-weight sum → %)
- **DoD:** `supabase db reset` ผ่าน; RLS ทดสอบข้าม tenant ไม่ได้

## Step 2 — Backend: evaluation lifecycle API
- [ ] สร้างใบ (annual/probation): resolve evaluator=supervisor_id, snapshot items, ตรวจ prereq สายบังคับบัญชา
- [ ] บันทึกคะแนนราย item + comment ระดับหมวด + attendance (เฉพาะสถานะ draft/returned)
- [ ] submit (หัวหน้า) → คำนวณคะแนน, เปลี่ยนสถานะ
- [ ] approve/return ราย step (dept_manager→md ตาม hierarchy/role) + hr finalize
- [ ] ทุก transition → audit; authorization ตาม routing (403 ถ้าไม่ใช่ผู้อนุมัติชั้นนั้น)
- **DoD:** pytest ครอบ lifecycle + isolation + RBAC ผ่าน

## Step 3 — Frontend
- [ ] หน้าให้คะแนน (ฟอร์ม BARS ราย item + comment + attendance)
- [ ] กล่องงานอนุมัติ (approval inbox) ตามบทบาท + ปุ่ม approve/return
- [ ] หน้าสรุปผล/สถานะใบประเมิน
- **DoD:** เดินครบ flow ใน browser จริง

## Step 4 — Reporting (Phase 3 prep)
- [ ] export ใบประเมิน PDF (ReportLab/WeasyPrint) — เลื่อนไป Phase 3

## Open (รอ HR)
- สูตร attendance_score (เต็ม 40) · เนื้อหา BARS `desc_1..5` · ความต่างเกณฑ์ probation ต่อ checkpoint
