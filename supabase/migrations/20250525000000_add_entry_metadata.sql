-- Add Entry Metadata Migration
-- Purpose: Add tags, categories, and mood tracking to journal entries

-- Add metadata columns to journal_entries table
ALTER TABLE journal_entries 
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS category VARCHAR(50),
ADD COLUMN IF NOT EXISTS mood INTEGER CHECK (mood >= 1 AND mood <= 10),
ADD COLUMN IF NOT EXISTS location VARCHAR(255),
ADD COLUMN IF NOT EXISTS weather VARCHAR(50);

-- Add indexes for efficient querying of metadata
CREATE INDEX IF NOT EXISTS idx_journal_entries_tags ON journal_entries USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_journal_entries_category ON journal_entries(category);
CREATE INDEX IF NOT EXISTS idx_journal_entries_mood ON journal_entries(mood);
CREATE INDEX IF NOT EXISTS idx_journal_entries_location ON journal_entries(location);

-- Create enum type for predefined categories (optional)
DO $$ BEGIN
    CREATE TYPE entry_category AS ENUM (
        'personal',
        'work',
        'travel',
        'health',
        'relationships',
        'goals',
        'gratitude',
        'reflection',
        'learning',
        'creativity',
        'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create function to search entries by metadata
CREATE OR REPLACE FUNCTION search_entries_with_metadata(
    query_embedding vector(1536),
    target_user_id UUID,
    similarity_threshold FLOAT DEFAULT 0.1,
    limit_count INT DEFAULT 10,
    filter_tags TEXT[] DEFAULT NULL,
    filter_category VARCHAR(50) DEFAULT NULL,
    min_mood INTEGER DEFAULT NULL,
    max_mood INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    text TEXT,
    tags TEXT[],
    category VARCHAR(50),
    mood INTEGER,
    location VARCHAR(255),
    weather VARCHAR(50),
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
        je.tags,
        je.category,
        je.mood,
        je.location,
        je.weather,
        je.created_at,
        1 - (je.embedding <=> query_embedding) as similarity
    FROM journal_entries je
    WHERE je.user_id = target_user_id 
        AND je.embedding IS NOT NULL
        AND (1 - (je.embedding <=> query_embedding)) > similarity_threshold
        AND (filter_tags IS NULL OR je.tags && filter_tags)  -- Array overlap operator
        AND (filter_category IS NULL OR je.category = filter_category)
        AND (min_mood IS NULL OR je.mood >= min_mood)
        AND (max_mood IS NULL OR je.mood <= max_mood)
    ORDER BY je.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$;

-- Grant access to the new function
GRANT EXECUTE ON FUNCTION search_entries_with_metadata TO authenticated;

-- Drop and recreate the embedding_stats view to include metadata statistics
DROP VIEW IF EXISTS embedding_stats;
CREATE VIEW embedding_stats AS
SELECT 
    user_id,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN embedding_status = 'pending' THEN 1 END) as pending_embeddings,
    COUNT(CASE WHEN embedding_status = 'completed' THEN 1 END) as completed_embeddings,
    COUNT(CASE WHEN embedding_status = 'failed' THEN 1 END) as failed_embeddings,
    COUNT(CASE WHEN tags IS NOT NULL AND array_length(tags, 1) > 0 THEN 1 END) as entries_with_tags,
    COUNT(CASE WHEN category IS NOT NULL THEN 1 END) as entries_with_category,
    COUNT(CASE WHEN mood IS NOT NULL THEN 1 END) as entries_with_mood,
    AVG(mood)::FLOAT as average_mood,
    MAX(updated_at) as last_updated
FROM journal_entries
GROUP BY user_id;

-- Create view for user tags statistics
CREATE VIEW user_tags_stats AS
SELECT 
    user_id,
    unnest(tags) as tag,
    COUNT(*) as tag_usage_count
FROM journal_entries 
WHERE tags IS NOT NULL AND array_length(tags, 1) > 0
GROUP BY user_id, unnest(tags);

-- Create view for user categories statistics
CREATE VIEW user_categories_stats AS
SELECT 
    user_id,
    category,
    COUNT(*) as category_usage_count
FROM journal_entries 
WHERE category IS NOT NULL
GROUP BY user_id, category;

-- Grant access to the views
GRANT SELECT ON embedding_stats TO authenticated;
GRANT SELECT ON user_tags_stats TO authenticated;
GRANT SELECT ON user_categories_stats TO authenticated; 