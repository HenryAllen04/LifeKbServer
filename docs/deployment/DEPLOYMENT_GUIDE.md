# LifeKB Deployment Guide
*Purpose: Complete guide for deploying LifeKB backend to production with enhanced data management features*

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Database Configuration](#database-configuration)
- [Vercel Deployment](#vercel-deployment)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Monitoring Setup](#monitoring-setup)
- [Security Configuration](#security-configuration)
- [Testing](#testing)

## Prerequisites

### Required Accounts
- [Vercel](https://vercel.com) account for hosting
- [Supabase](https://supabase.com) account for database
- [OpenAI](https://openai.com) account for embeddings (optional)

### Required Tools
- Node.js 18+ 
- Supabase CLI
- Vercel CLI
- Git

### Installation
```bash
# Install Supabase CLI
npm install -g supabase

# Install Vercel CLI
npm install -g vercel

# Login to services
supabase login
vercel login
```

## Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/lifekb-server.git
cd lifekb-server
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Create Environment File
```bash
cp .env.example .env.local
```

## Database Configuration

### 1. Create Supabase Project
```bash
# Initialize Supabase
supabase init

# Link to remote project
supabase link --project-ref <your-project-ref>

# Apply migrations
supabase db push
```

### 2. Enable Required Extensions
In your Supabase SQL Editor, run:
```sql
-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extensions
SELECT * FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp');
```

### 3. Configure Row Level Security (RLS)
```sql
-- Enable RLS for journal_entries
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;

-- Policy for users to only access their own entries
CREATE POLICY "Users can only access their own entries"
ON journal_entries
FOR ALL
USING (auth.uid() = user_id);

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
```

### 4. Verify Database Schema
```bash
# Check migration status
supabase db diff

# Test database connectivity
supabase db ping
```

## Vercel Deployment

### 1. Create vercel.json Configuration
```json
{
  "version": 2,
  "functions": {
    "api/**/*.py": {
      "runtime": "python3.9"
    }
  },
  "builds": [
    {
      "src": "api/**/*.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api/$1"
    }
  ],
  "env": {
    "PYTHONPATH": "/var/task"
  }
}
```

### 2. Deploy to Vercel
```bash
# Deploy
vercel --prod

# Set custom domain (optional)
vercel domains add yourdomain.com
```

### 3. Configure Function Settings
In Vercel dashboard:
- Set function timeout to 60 seconds
- Configure environment variables
- Enable Edge Runtime (optional)

## Environment Variables

### Production Environment Variables
Set these in Vercel dashboard or via CLI:

```bash
# Required - Supabase Configuration
vercel env add SUPABASE_URL production
vercel env add SUPABASE_SERVICE_KEY production

# Required - JWT Secret
vercel env add JWT_SECRET_KEY production

# Optional - OpenAI (for embeddings)
vercel env add OPENAI_API_KEY production

# Optional - Monitoring
vercel env add SENTRY_DSN production
vercel env add DATADOG_API_KEY production

# Optional - Rate Limiting
vercel env add REDIS_URL production
```

### Environment Values
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key

# OpenAI (Optional)
OPENAI_API_KEY=sk-your-openai-api-key

# Monitoring (Optional)
SENTRY_DSN=https://your-sentry-dsn.ingest.sentry.io
DATADOG_API_KEY=your-datadog-api-key

# Redis (Optional for enhanced rate limiting)
REDIS_URL=redis://localhost:6379
```

## Database Migrations

### Apply Migrations in Order
```bash
# Check current status
supabase db diff

# Apply all migrations
supabase db push

# Verify schema
supabase db ping
```

### Migration Files Applied
1. `20250524163946_journal_entries_schema.sql` - Base schema
2. `20250525000000_add_entry_metadata.sql` - Metadata features

### Verify Database Functions
```sql
-- Test the metadata search function
SELECT search_entries_with_metadata(
  '[0.1,0.2,0.3]'::vector,
  'user-uuid'::uuid,
  0.1,
  5,
  ARRAY['test'],
  'personal',
  7,
  10
);

-- Check views exist
SELECT * FROM embedding_stats LIMIT 1;
SELECT * FROM user_tags_stats LIMIT 1;
SELECT * FROM user_categories_stats LIMIT 1;
```

## Monitoring Setup

### 1. Performance Monitoring
The built-in monitoring system tracks:
- Request performance and timing
- Rate limiting violations
- Authentication failures
- Database query performance
- Error rates and patterns

### 2. Logging Configuration
Logs are automatically structured and include:
- Request IDs for tracing
- User context
- Performance metrics
- Security events

### 3. Health Checks
Configure health check endpoints:
- `/api/auth?health=true` - Authentication service
- Database connectivity verification
- Service status monitoring

### 4. External Monitoring (Optional)
```python
# Add to monitoring configuration
MONITORING_CONFIG = {
    "sentry": {
        "dsn": os.environ.get("SENTRY_DSN"),
        "environment": "production"
    },
    "datadog": {
        "api_key": os.environ.get("DATADOG_API_KEY"),
        "service_name": "lifekb-api"
    }
}
```

## Security Configuration

### 1. CORS Setup
```python
# Already configured in APIs
headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
}
```

### 2. Rate Limiting
Current limits:
- Authentication: 5 requests per 5 minutes
- Entry operations: 30-200 requests per minute
- Search operations: 50 requests per minute

### 3. Input Validation
- Text length limits (10,000 characters)
- Tag limits (20 tags max)
- Parameter validation
- SQL injection prevention

### 4. Authentication
- JWT-based authentication via Supabase
- Row Level Security (RLS) enabled
- Secure token validation

## Testing

### 1. Local Testing
```bash
# Start local development
vercel dev --listen 3000

# Test health endpoint
curl http://localhost:3000/api/auth?health=true

# Test with authentication
curl -X POST http://localhost:3000/api/auth \
  -H "Content-Type: application/json" \
  -d '{"action": "signup", "email": "test@example.com", "password": "test123"}'
```

### 2. Production Testing
```bash
# Test production deployment
curl https://your-app.vercel.app/api/auth?health=true

# Load testing (optional)
npm install -g artillery
artillery quick --count 10 --num 100 https://your-app.vercel.app/api/auth?health=true
```

### 3. Database Testing
```bash
# Test migrations
supabase db reset
supabase db push

# Test database functions
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres" \
  -c "SELECT COUNT(*) FROM journal_entries;"
```

## Post-Deployment Checklist

### ✅ Deployment Verification
- [ ] All API endpoints respond correctly
- [ ] Database connections are working
- [ ] Authentication flow works
- [ ] Rate limiting is active
- [ ] CORS headers are set correctly

### ✅ Security Verification
- [ ] Environment variables are secure
- [ ] RLS policies are active
- [ ] Input validation is working
- [ ] Rate limiting prevents abuse
- [ ] JWT tokens are validated

### ✅ Feature Verification
- [ ] Journal entry CRUD operations
- [ ] Metadata filtering works
- [ ] Semantic search functions
- [ ] Analytics endpoints respond
- [ ] Tag suggestions work

### ✅ Performance Verification
- [ ] Response times under 500ms
- [ ] Database queries are optimized
- [ ] Indexes are being used
- [ ] Memory usage is reasonable
- [ ] Error rates are low

### ✅ Monitoring Verification
- [ ] Logs are being generated
- [ ] Performance metrics available
- [ ] Health checks pass
- [ ] Error tracking works
- [ ] Security events logged

## Maintenance

### Regular Tasks
- Monitor database performance
- Review rate limiting metrics
- Update dependencies
- Backup database regularly
- Monitor API usage patterns

### Scaling Considerations
- Supabase automatically scales
- Vercel functions scale automatically
- Monitor rate limits and adjust as needed
- Consider caching for high-traffic endpoints

## Troubleshooting

### Common Issues
1. **Migration Failures**: Check SQL syntax and dependencies
2. **Auth Issues**: Verify Supabase keys and JWT secret
3. **Rate Limiting**: Adjust limits based on usage patterns
4. **Performance**: Check database indexes and query optimization

### Support
- Check logs in Vercel dashboard
- Monitor database metrics in Supabase
- Review error tracking in monitoring tools
- Use health check endpoints for diagnostics 