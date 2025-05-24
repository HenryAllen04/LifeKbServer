-- Fix migration for embedding_stats view
-- Purpose: Properly create the embedding_stats view without RLS policy conflicts

-- Create the embedding statistics view 
-- Views automatically inherit RLS policies from their underlying tables
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
