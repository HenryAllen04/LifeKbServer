-- Test Database Schema Script
-- Purpose: Verify journal_entries table and vector search functionality

-- Test 1: Check if journal_entries table exists and has correct structure
\d journal_entries;

-- Test 2: Check if pgvector extension is enabled
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Test 3: Check if indexes exist
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'journal_entries';

-- Test 4: Check if RLS is enabled
SELECT schemaname, tablename, rowsecurity, enablerls 
FROM pg_tables 
WHERE tablename = 'journal_entries';

-- Test 5: Check if search_entries function exists
\df search_entries

-- Test 6: Check if embedding_stats view exists
\d+ embedding_stats;

-- Test 7: Insert sample data (would need actual user authentication in real scenario)
-- Note: This is just to test the table structure, not actual data insertion with RLS
SELECT 'Database schema verification completed' as test_status; 