-- LifeKB Initial Schema Migration
-- Purpose: Set up database tables, functions, and security policies for the journaling backend

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create journal entries table
CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    embedding vector(1536), -- OpenAI text-embedding-3-small dimensions
    embedding_status TEXT DEFAULT 'pending' CHECK (embedding_status IN ('pending', 'completed', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can access own entries" ON journal_entries
    FOR ALL USING (auth.uid() = user_id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_journal_entries_user_id ON journal_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_created_at ON journal_entries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_journal_entries_embedding_status ON journal_entries(embedding_status);

-- Create vector index for similarity search (using ivfflat)
CREATE INDEX IF NOT EXISTS idx_journal_entries_embedding ON journal_entries 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create function for semantic search
CREATE OR REPLACE FUNCTION search_entries(
    query_embedding vector(1536),
    target_user_id UUID,
    similarity_threshold FLOAT DEFAULT 0.1,
    limit_count INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    text TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    similarity FLOAT
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        je.id,
        je.text,
        je.created_at,
        1 - (je.embedding <=> query_embedding) as similarity
    FROM journal_entries je
    WHERE je.user_id = target_user_id 
        AND je.embedding IS NOT NULL
        AND (1 - (je.embedding <=> query_embedding)) > similarity_threshold
    ORDER BY je.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$;

-- Create function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_journal_entries_updated_at 
    BEFORE UPDATE ON journal_entries 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON TABLE journal_entries TO authenticated;
GRANT EXECUTE ON FUNCTION search_entries TO authenticated;

-- Create a view for embedding statistics
-- Note: Views inherit RLS policies from underlying tables, no separate RLS policy needed
CREATE OR REPLACE VIEW embedding_stats AS
SELECT 
    user_id,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN embedding_status = 'pending' THEN 1 END) as pending_embeddings,
    COUNT(CASE WHEN embedding_status = 'completed' THEN 1 END) as completed_embeddings,
    COUNT(CASE WHEN embedding_status = 'failed' THEN 1 END) as failed_embeddings,
    MAX(updated_at) as last_updated
FROM journal_entries
GROUP BY user_id;

-- Grant access to the view
GRANT SELECT ON embedding_stats TO authenticated;
