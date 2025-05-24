-- Comprehensive fix for production database foreign key constraint
-- Run this manually via Supabase dashboard SQL editor

-- First, check ALL foreign key constraints on journal_entries
SELECT 
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_name = 'journal_entries';

-- Drop ALL foreign key constraints on user_id column (there might be multiple)
DO $$ 
DECLARE
    constraint_rec RECORD;
BEGIN
    FOR constraint_rec IN 
        SELECT tc.constraint_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' 
          AND tc.table_name = 'journal_entries'
          AND kcu.column_name = 'user_id'
    LOOP
        EXECUTE 'ALTER TABLE journal_entries DROP CONSTRAINT ' || constraint_rec.constraint_name;
        RAISE NOTICE 'Dropped constraint: %', constraint_rec.constraint_name;
    END LOOP;
END $$;

-- Add the correct constraint pointing to auth.users
ALTER TABLE journal_entries 
ADD CONSTRAINT journal_entries_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- Ensure RLS is enabled and policy exists
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists and recreate
DROP POLICY IF EXISTS "Users can access own entries" ON journal_entries;
CREATE POLICY "Users can access own entries" ON journal_entries
FOR ALL USING (auth.uid() = user_id);

-- Verify the fix by checking constraints again
SELECT 
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_name = 'journal_entries'
  AND kcu.column_name = 'user_id';

-- Also check if auth.users table exists and has the current user
SELECT count(*) as auth_users_count FROM auth.users;
SELECT id, email FROM auth.users WHERE email = 'demo@example.com' LIMIT 1; 