# Frontend (React + Tailwind + Vite)

Scaffolded in Step 7 (see ../docs/archive/PHASE_1_PLAN.md). Package manager: **npm**.

## Setup (later, when coding Step 7)
```
npm install
copy .env.example .env.local   # then fill values
npm run dev
```

## Notes
- Client receives the Supabase **anon key** only (never service_role).
- Auth via @supabase/supabase-js; protected routes + role-based layout.
- Validate inputs with zod (OWASP A03).
