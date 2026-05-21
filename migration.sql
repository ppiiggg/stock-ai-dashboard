-- Run this in your Supabase SQL Editor:
-- https://supabase.com/dashboard/project/xifholssjvjobtwpkklq/sql/new

CREATE TABLE IF NOT EXISTS public.analyses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    symbol TEXT NOT NULL,
    price NUMERIC NOT NULL,
    change_percent TEXT NOT NULL,
    market TEXT,
    summary TEXT NOT NULL,
    sentiment TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable Row Level Security (recommended)
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

-- Allow public read/write (since this is a demo/dashboard)
CREATE POLICY "Allow all operations on analyses"
    ON public.analyses
    FOR ALL
    TO anon, authenticated
    USING (true)
    WITH CHECK (true);
