# LifeKB Backend Setup Guide

## Environment Configuration

Copy the `env.example` file to `.env` and configure the following values:

### 1. Supabase Configuration
Replace these with your actual Supabase project values:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
SUPABASE_ANON_KEY=your-anon-key-here
```

### 2. OpenAI Configuration
Add your OpenAI API key:
```env
OPENAI_API_KEY=your-openai-api-key-here
```

### 3. Security Configuration
⚠️ **SECURITY WARNING**: Generate your own unique JWT secret key!
```env
JWT_SECRET_KEY=GENERATE_YOUR_OWN_SECRET_32_CHARS_MIN
```

**To generate a secure JWT secret:**
```python
import secrets
print(secrets.token_urlsafe(32))
```
**Never use example keys in production!**

### 4. CORS Origins
For development (add production domain after Vercel deployment):
```env
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

## Quick Setup Commands

```bash
# 1. Copy environment template
cp env.example .env

# 2. Edit .env with your actual credentials
# Replace the placeholder values with your real Supabase and OpenAI keys

# 3. Install dependencies
pip install -r requirements.txt

# 4. Link to your Supabase project
supabase link --project-ref your-project-ref

# 5. Push database schema to Supabase
supabase db push

# 6. Test locally with Supabase
supabase start  # Starts local Supabase (optional)
vercel dev      # Start the API server
```

## Database Setup (Supabase CLI Method)

Instead of manually running SQL scripts, we now use Supabase migrations:

### Option 1: Push to Remote Supabase (Recommended)
```bash
# Link to your Supabase project
supabase link --project-ref YOUR_PROJECT_REF

# Push the migration to your remote database
supabase db push
```

### Option 2: Local Development Database
```bash
# Start local Supabase stack
supabase start

# Your local database will be automatically set up with the migration
# Local Supabase runs on http://localhost:54323
```

### Migration Management
```bash
# Create new migration
supabase migration new migration_name

# Reset database (destructive)
supabase db reset

# View migration status
supabase migration list
```

## Project Structure

The Supabase CLI created:
- `supabase/migrations/` - Database migrations
- `supabase/config.toml` - Supabase project configuration
- Migration files are version-controlled and can be applied to any environment

## Important Notes

- **Never commit your `.env` file** - it contains secrets
- The JWT secret key above is already generated and secure
- Update CORS origins to match your actual domains after deployment
- For production, set `ENVIRONMENT=production` and `DEBUG=false`
- Database schema changes are now managed through migrations 