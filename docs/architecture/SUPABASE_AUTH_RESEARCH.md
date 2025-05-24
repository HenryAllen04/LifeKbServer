# Supabase Authentication Research - Key Findings

## Problem Statement
Initial attempt to create demo users by directly inserting into a custom `public.users` table failed with foreign key constraint errors. Research revealed fundamental misunderstanding of Supabase Auth architecture.

## Key Research Findings

### 1. Supabase Auth System Architecture

**Supabase manages `auth.users` automatically:**
- **`auth.users`** - Core user table managed by Supabase Auth service
- **NOT accessible via REST API** for security reasons
- Users created via authentication flows (signUp, signIn), not direct inserts
- Contains: id, email, phone, encrypted_password, email_confirmed_at, etc.

**Custom user data goes in `public.profiles`:**
```sql
create table public.profiles (
  id uuid not null references auth.users on delete cascade,
  first_name text,
  last_name text,
  primary key (id)
);
alter table public.profiles enable row level security;
```

### 2. Correct vs Incorrect Approaches

❌ **WRONG - What we tried initially:**
```sql
-- Don't do this
CREATE TABLE public.users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL
);

-- This fails because public.users doesn't integrate with Supabase Auth
```

✅ **CORRECT - Proper Supabase pattern:**
```sql
-- journal_entries should reference auth.users directly
CREATE TABLE journal_entries (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3. User Creation Process

**Proper user creation:**
```javascript
// Via Supabase Auth API
const { data, error } = await supabase.auth.signUp({
  email: 'demo@example.com',
  password: 'demo123',
  options: {
    data: {
      first_name: 'Demo',
      last_name: 'User'
    }
  }
})
```

**What happens automatically:**
1. User created in `auth.users` with UUID
2. JWT tokens issued for authentication
3. RLS policies can reference `auth.uid()` 

### 4. Current System Status

**Working Components:**
- ✅ Demo user exists in `auth.users` (login works)
- ✅ JWT authentication system functional
- ✅ Entries endpoint reads work (returns empty array)
- ✅ User ID: `53cf98a2-c29f-44a3-ac37-69f3975c78cf`

**Broken Component:**
- ❌ Foreign key constraint: `journal_entries.user_id` → `public.users` (doesn't exist)
- ❌ Should be: `journal_entries.user_id` → `auth.users.id`

**Error Message:**
```
"Key (user_id)=(53cf98a2-c29f-44a3-ac37-69f3975c78cf) is not present in table \"users\""
```

### 5. Database Schema Fix Required

```sql
-- Remove incorrect foreign key constraint
ALTER TABLE journal_entries DROP CONSTRAINT journal_entries_user_id_fkey;

-- Add correct foreign key constraint  
ALTER TABLE journal_entries 
ADD CONSTRAINT journal_entries_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- Ensure RLS is enabled
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;

-- Create proper RLS policy
CREATE POLICY "Users can only access their own entries" 
ON journal_entries FOR ALL 
USING (auth.uid() = user_id);
```

## Next Steps

1. **Fix Database Schema** - Update foreign key constraint to point to `auth.users`
2. **Test Entry Creation** - Verify entries can be created with existing demo user
3. **Complete Setup Flow** - Populate demo data for testing embeddings
4. **Document Patterns** - Create examples for future reference

## Key Takeaways

1. **Never create custom users tables** - Use Supabase Auth exclusively
2. **Reference auth.users directly** - Foreign keys should point to `auth.users.id`
3. **Use RLS with auth.uid()** - Built-in function for user identification
4. **Test authentication flow first** - Verify users exist before creating related data

## Resources

- [Supabase User Management Docs](https://supabase.com/docs/guides/auth/managing-user-data)
- [Supabase Auth Architecture](https://supabase.com/docs/guides/auth/overview)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security) 