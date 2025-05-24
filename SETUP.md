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
Use this generated JWT secret key:
```env
JWT_SECRET_KEY=hlGuCEgOxXKUEJvWxZbyiRLIHr0jPnjRIjQOnn5V-z8
```

### 4. CORS Origins
For development and production:
```env
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000", "https://your-vercel-domain.vercel.app"]
```

## Quick Setup Commands

```bash
# 1. Copy environment template
cp env.example .env

# 2. Edit .env with your actual values
# Replace the placeholder values with your real credentials

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up database (run the SQL script in Supabase)
# Copy contents of scripts/setup_database.sql to Supabase SQL Editor

# 5. Test locally
vercel dev
```

## Important Notes

- **Never commit your `.env` file** - it contains secrets
- The JWT secret key above is already generated and secure
- Update CORS origins to match your actual domains
- For production, set `ENVIRONMENT=production` and `DEBUG=false` 