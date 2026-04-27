-- Alternative for a private backend-only table.
-- Prefer using a Supabase secret/service_role key with RLS enabled, but this is
-- useful for quick local testing.
alter table public.atm_data disable row level security;
