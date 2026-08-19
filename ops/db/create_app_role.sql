-- Create the application DB role that the backend connects as.
--
-- WHY THIS MATTERS: PostgreSQL RLS is IGNORED for superusers and for any role
-- with the BYPASSRLS attribute. The current default `postgres` user is a
-- superuser, so tenant isolation is INERT until the app connects as a normal
-- role like the one below. Run this once (as a superuser), then set:
--     POSTGRES_USER=wa_app
--     POSTGRES_PASSWORD=<the password you set below>
-- in the backend .env.
--
-- Run:  psql -d wa_saas -f ops/db/create_app_role.sql

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'wa_app') THEN
    CREATE ROLE wa_app LOGIN PASSWORD 'change_me_in_prod' NOSUPERUSER NOBYPASSRLS;
  END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO wa_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO wa_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO wa_app;

-- Future tables/sequences created by migrations should also be usable.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO wa_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO wa_app;

-- Sanity: wa_app must NOT bypass RLS.
-- SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'wa_app';
