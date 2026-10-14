-- Opportunities table: stores scraped/RSS items for durable list + detail lookups.
-- Run once in the Supabase SQL editor (or via supabase db push).
-- Backend uses the service role key (bypasses RLS). Anon has no access.

create table if not exists public.opportunities (
  id text primary key,
  title text not null default '',
  link text,
  description text,
  content text,
  pub_date text,
  deadline text,
  author text,
  categories jsonb not null default '[]'::jsonb,
  source_id text,
  source_name text,
  source_url text,
  image text,
  -- Fields that vary by source (attachments, country, opportunity_type, etc.)
  extra jsonb not null default '{}'::jsonb,
  scraped_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists opportunities_pub_date_idx
  on public.opportunities (pub_date desc nulls last);

create index if not exists opportunities_scraped_at_idx
  on public.opportunities (scraped_at desc);

create index if not exists opportunities_source_id_idx
  on public.opportunities (source_id);

-- Keep updated_at fresh on every upsert/update
create or replace function public.set_opportunities_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists opportunities_set_updated_at on public.opportunities;
create trigger opportunities_set_updated_at
  before update on public.opportunities
  for each row
  execute function public.set_opportunities_updated_at();

-- RLS: only service role (backend) can read/write. Anon/authenticated get nothing.
alter table public.opportunities enable row level security;

drop policy if exists "opportunities_no_anon_select" on public.opportunities;
drop policy if exists "opportunities_no_anon_insert" on public.opportunities;
drop policy if exists "opportunities_no_anon_update" on public.opportunities;
drop policy if exists "opportunities_no_anon_delete" on public.opportunities;

-- No policies for anon/authenticated => denied by default when RLS is on.
-- Service role bypasses RLS, so the FastAPI backend can still upsert/list/get.
