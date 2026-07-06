# Data-access layer (SQLAlchemy async). Sets request.jwt.claims per session
# so Postgres RLS is enforced. Routers must NOT touch the DB directly.
