-- ============================================================
-- AI RESEARCH PAPER AGENT - SUPABASE DATABASE SCHEMA
-- ============================================================

-- ============================================================
-- 1. VECTOR EXTENSION
-- ============================================================

create extension if not exists vector;


-- ============================================================
-- 2. PAPERS TABLE
-- ============================================================

create table if not exists papers (
    id bigserial primary key,

    paper_id text unique not null,

    title text not null,

    abstract text,

    authors text,

    published_at timestamptz,

    arxiv_url text not null,

    pdf_url text,

    category text,

    created_at timestamptz default now()
);


-- ============================================================
-- 3. PAPER CHUNKS TABLE
-- ============================================================

create table if not exists paper_chunks (
    id bigserial primary key,

    paper_id text not null
        references papers(paper_id)
        on delete cascade,

    chunk_index integer not null,

    section text,

    subsection text,

    page_start integer,

    page_end integer,

    chunk_text text not null,

    -- BGE-small-en-v1.5 produces 384-dimensional embeddings
    embedding vector(384),

    created_at timestamptz default now(),

    unique(paper_id, chunk_index)
);


-- ============================================================
-- 4. PAPER CHUNKS INDEX
-- ============================================================

create index if not exists paper_chunks_paper_id_idx
on paper_chunks(paper_id);


-- ============================================================
-- 5. VECTOR INDEX
-- ============================================================

create index if not exists paper_chunks_embedding_idx
on paper_chunks
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);


-- ============================================================
-- 6. VECTOR SEARCH FUNCTION
-- ============================================================

create or replace function match_paper_chunks(
    query_embedding vector(384),
    match_count integer,
    target_paper_id text
)

returns table(
    id bigint,
    paper_id text,
    chunk_index integer,
    section text,
    subsection text,
    page_start integer,
    page_end integer,
    chunk_text text,
    similarity float
)

language sql
as $$

    select
        pc.id,
        pc.paper_id,
        pc.chunk_index,
        pc.section,
        pc.subsection,
        pc.page_start,
        pc.page_end,
        pc.chunk_text,

        1 - (pc.embedding <=> query_embedding) as similarity

    from paper_chunks pc

    where pc.paper_id = target_paper_id

      and pc.embedding is not null

    order by pc.embedding <=> query_embedding

    limit match_count;

$$;


-- ============================================================
-- 7. LEXICAL / KEYWORD SEARCH FUNCTION
-- ============================================================

create or replace function search_paper_chunks_lexical(
    search_query text,
    match_count integer,
    target_paper_id text
)

returns table(
    id bigint,
    paper_id text,
    chunk_index integer,
    section text,
    subsection text,
    page_start integer,
    page_end integer,
    chunk_text text,
    lexical_score real
)

language sql
as $$

    select
        pc.id,
        pc.paper_id,
        pc.chunk_index,
        pc.section,
        pc.subsection,
        pc.page_start,
        pc.page_end,
        pc.chunk_text,

        ts_rank_cd(
            to_tsvector('english', pc.chunk_text),
            plainto_tsquery('english', search_query)
        )::real as lexical_score

    from paper_chunks pc

    where pc.paper_id = target_paper_id

      and to_tsvector('english', pc.chunk_text)
          @@ plainto_tsquery('english', search_query)

    order by
        ts_rank_cd(
            to_tsvector('english', pc.chunk_text),
            plainto_tsquery('english', search_query)
        ) desc

    limit match_count;

$$;


-- ============================================================
-- 8. TELEGRAM SUBSCRIBERS
-- ============================================================

create table if not exists telegram_subscribers (
    chat_id bigint primary key,

    username text,

    active boolean default true,

    created_at timestamptz default now()
);


-- ============================================================
-- 9. TELEGRAM SESSION
-- ============================================================
-- Stores which paper the user is currently asking questions about.
-- This prevents the active paper from being lost when the bot restarts.

create table if not exists telegram_sessions (
    chat_id bigint primary key,

    paper_id text
        references papers(paper_id)
        on delete set null,

    updated_at timestamptz default now()
);


-- ============================================================
-- 10. ENABLE ROW LEVEL SECURITY
-- ============================================================

alter table papers enable row level security;

alter table paper_chunks enable row level security;

alter table telegram_subscribers enable row level security;

alter table telegram_sessions enable row level security;


-- ============================================================
-- 11. PAPERS POLICIES
-- ============================================================

drop policy if exists "dev papers select"
on papers;

create policy "dev papers select"
on papers

for select
to anon, authenticated

using (true);


drop policy if exists "dev papers insert"
on papers;

create policy "dev papers insert"
on papers

for insert
to anon, authenticated

with check (true);


drop policy if exists "dev papers update"
on papers;

create policy "dev papers update"
on papers

for update
to anon, authenticated

using (true)

with check (true);


-- ============================================================
-- 12. PAPER CHUNKS POLICIES
-- ============================================================

drop policy if exists "dev chunks select"
on paper_chunks;

create policy "dev chunks select"
on paper_chunks

for select
to anon, authenticated

using (true);


drop policy if exists "dev chunks insert"
on paper_chunks;

create policy "dev chunks insert"
on paper_chunks

for insert
to anon, authenticated

with check (true);


drop policy if exists "dev chunks update"
on paper_chunks;

create policy "dev chunks update"
on paper_chunks

for update
to anon, authenticated

using (true)

with check (true);


drop policy if exists "dev chunks delete"
on paper_chunks;

create policy "dev chunks delete"
on paper_chunks

for delete
to anon, authenticated

using (true);


-- ============================================================
-- 13. TELEGRAM SUBSCRIBER POLICIES
-- ============================================================

drop policy if exists "dev subscribers select"
on telegram_subscribers;

create policy "dev subscribers select"
on telegram_subscribers

for select
to anon, authenticated

using (true);


drop policy if exists "dev subscribers insert"
on telegram_subscribers;

create policy "dev subscribers insert"
on telegram_subscribers

for insert
to anon, authenticated

with check (true);


drop policy if exists "dev subscribers update"
on telegram_subscribers;

create policy "dev subscribers update"
on telegram_subscribers

for update
to anon, authenticated

using (true)

with check (true);


-- ============================================================
-- 14. TELEGRAM SESSION POLICIES
-- ============================================================

drop policy if exists "dev sessions select"
on telegram_sessions;

create policy "dev sessions select"
on telegram_sessions

for select
to anon, authenticated

using (true);


drop policy if exists "dev sessions insert"
on telegram_sessions;

create policy "dev sessions insert"
on telegram_sessions

for insert
to anon, authenticated

with check (true);


drop policy if exists "dev sessions update"
on telegram_sessions;

create policy "dev sessions update"
on telegram_sessions

for update
to anon, authenticated

using (true)

with check (true);


drop policy if exists "dev sessions delete"
on telegram_sessions;

create policy "dev sessions delete"
on telegram_sessions

for delete
to anon, authenticated

using (true);


-- ============================================================
-- SCHEMA COMPLETE
-- ============================================================