# Project: Performance Evaluation System (E-Appraisal)

## Objective
Build a Responsive Web App for employee performance evaluation across multiple companies and branches (approx. 500 employees).

## Tech Stack
- Backend: Python (FastAPI)
- Database: PostgreSQL (via Supabase or local instance)
- Frontend: React + Tailwind CSS (Responsive)
- Reporting: ReportLab or WeasyPrint (PDF Generation)

## Database Schema (Multi-Tenant)
1. Companies: id, name
2. Branches: id, company_id, name
3. Employees: id, branch_id, role,supervisor_id, manager_id
4. Evaluations: id, employee_id, evaluator_id, criteria_id, score, comment
5. Criteria (BARS): id, category, desc_5, desc_4, desc_3, desc_2, desc_1

## Phases
1. Phase 1: Database Setup & User Auth (Multi-Tenant).
2. Phase 2: Evaluation UI (BARS-based scoring).
3. Phase 3: Reporting & PDF Export (Modern visual style).

## Constraints
- Must handle 500+ users.
- Role-based access (Managers see only their subordinates).
- Data integrity & Audit log for evaluations.