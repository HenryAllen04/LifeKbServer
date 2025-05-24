# LifeKB Production Deployment Plan
*Purpose: Step-by-step guide to deploy LifeKB backend to production with Supabase and Vercel*

## 🎯 Deployment Overview

**Current Status**: Complete backend with metadata features (73% complete)
**Goal**: Deploy to production with Supabase + Vercel
**Estimated Time**: 30-45 minutes

## 📋 Pre-Deployment Checklist

### ✅ What We Have
- [x] Complete backend API with metadata features
- [x] Database schema with migrations
- [x] Authentication system (Supabase)
- [x] Comprehensive documentation
- [x] Local testing completed
- [x] Rate limiting and security features

### 🔧 What We Need
- [ ] Production Supabase project
- [ ] Vercel production deployment
- [ ] Environment variables configured
- [ ] Database migrations applied to production
- [ ] Production testing

## 🚀 Step-by-Step Deployment Process

### Step 1: Set Up Production Supabase Project

#### 1.1 Create New Supabase Project
```bash
# Go to https://supabase.com/dashboard
# Click "New project"
# Choose your organization
# Project name: "lifekb-production" (or your preferred name)
# Database password: Generate a strong password
# Region: Choose closest to your users (e.g., us-east-1)
# Pricing plan: Free tier is fine for now
```

#### 1.2 Configure Supabase CLI for Production
```bash
# Link to production project
supabase login
supabase link --project-ref YOUR_PRODUCTION_PROJECT_REF

# Verify connection
supabase db ping
```

#### 1.3 Apply Database Migrations to Production
```bash
# Apply all migrations to production
supabase db push

# Verify schema
supabase db diff
```

#### 1.4 Enable Required Extensions
```sql
-- Run in Supabase SQL Editor (Production)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

#### 1.5 Configure Row Level Security (RLS)
```sql
-- Run in Supabase SQL Editor (Production)
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access their own entries"
ON journal_entries
FOR ALL
USING (auth.uid() = user_id);

-- Grant permissions
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
```

### Step 2: Prepare Vercel Deployment

#### 2.1 Create Vercel Configuration
```json
{
  "version": 2,
  "functions": {
    "api/**/*.py": {
      "runtime": "python3.9",
      "maxDuration": 60
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
    },
    {
      "src": "/(.*)",
      "dest": "/api/$1"
    }
  ],
  "env": {
    "PYTHONPATH": "/var/task"
  },
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        {
          "key": "Access-Control-Allow-Origin",
          "value": "*"
        },
        {
          "key": "Access-Control-Allow-Methods",
          "value": "GET, POST, PUT, DELETE, OPTIONS"
        },
        {
          "key": "Access-Control-Allow-Headers",
          "value": "Content-Type, Authorization"
        }
      ]
    }
  ]
}
```

#### 2.2 Create Production Requirements
```txt
# Production-optimized requirements.txt
fastapi==0.104.1
python-multipart==0.0.6
supabase==2.0.2
openai==1.3.8
pydantic==2.5.0
python-jose[cryptography]==3.3.0
python-dateutil==2.8.2
requests==2.31.0
```

### Step 3: Deploy to Vercel

#### 3.1 Install and Setup Vercel CLI
```bash
# Install Vercel CLI (if not already installed)
npm install -g vercel

# Login to Vercel
vercel login
```

#### 3.2 Deploy to Production
```bash
# Deploy to production
vercel --prod

# Follow prompts:
# - Set up and deploy? Yes
# - Which scope? Your personal account
# - Link to existing project? No
# - Project name: lifekb-server (or your preference)
# - Directory: ./ (current directory)
# - Settings correct? Yes
```

### Step 4: Configure Environment Variables

#### 4.1 Set Production Environment Variables
```bash
# Required - Supabase Configuration
vercel env add SUPABASE_URL production
# Value: https://YOUR_PROJECT_REF.supabase.co

vercel env add SUPABASE_SERVICE_KEY production
# Value: Your service role key from Supabase dashboard

vercel env add SUPABASE_ANON_KEY production
# Value: Your anon public key from Supabase dashboard

# Required - JWT Secret
vercel env add JWT_SECRET_KEY production
# Value: Generate a strong secret (32+ characters)

# Optional - OpenAI (for embeddings)
vercel env add OPENAI_API_KEY production
# Value: Your OpenAI API key (sk-...)
```

#### 4.2 Environment Variables Reference
```env
# Get these from Supabase Dashboard > Settings > API
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Generate a strong secret
JWT_SECRET_KEY=your-super-secure-jwt-secret-key-32-chars-min

# Optional for AI features
OPENAI_API_KEY=sk-your-openai-api-key
```

### Step 5: Verify Production Deployment

#### 5.1 Test Health Endpoint
```bash
# Test production health
curl https://your-app.vercel.app/api/auth?health=true
```

#### 5.2 Test Authentication
```bash
# Test user registration
curl -X POST "https://your-app.vercel.app/api/auth" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "signup",
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

#### 5.3 Run Full Test Suite Against Production
```bash
# Run tests against production
python scripts/test_metadata_features.py --url https://your-app.vercel.app
```

### Step 6: Post-Deployment Configuration

#### 6.1 Custom Domain (Optional)
```bash
# Add custom domain
vercel domains add yourdomain.com
vercel domains add api.yourdomain.com
```

#### 6.2 Set Up Monitoring
- Configure Vercel analytics
- Set up Supabase monitoring
- Monitor logs in Vercel dashboard

#### 6.3 Security Review
- Verify CORS settings
- Check rate limiting
- Review RLS policies
- Test authentication flows

## 🛠️ Deployment Commands Summary

```bash
# 1. Create production Supabase project (web UI)
# 2. Link and migrate database
supabase link --project-ref YOUR_PROD_REF
supabase db push

# 3. Deploy to Vercel
vercel --prod

# 4. Configure environment variables
vercel env add SUPABASE_URL production
vercel env add SUPABASE_SERVICE_KEY production
vercel env add JWT_SECRET_KEY production
# ... add all required env vars

# 5. Test deployment
curl https://your-app.vercel.app/api/auth?health=true
```

## 📊 Expected Timeline

- **Supabase Setup**: 10 minutes
- **Vercel Deployment**: 5 minutes
- **Environment Configuration**: 10 minutes
- **Testing & Verification**: 15 minutes
- **Total**: ~40 minutes

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify environment variables
   - Check Supabase project status
   - Ensure RLS policies are correct

2. **Vercel Deployment Failures**
   - Check requirements.txt syntax
   - Verify Python version compatibility
   - Review build logs

3. **CORS Issues**
   - Verify vercel.json headers
   - Check API endpoint responses

4. **Authentication Failures**
   - Verify JWT secret is set
   - Check Supabase auth configuration

### Debug Commands
```bash
# Check Vercel logs
vercel logs

# Test database connection
curl https://your-app.vercel.app/api/auth?health=true

# Verify environment variables
vercel env ls
```

## ✅ Success Criteria

- [ ] Health endpoint returns 200
- [ ] User registration works
- [ ] User login works
- [ ] Entry creation works
- [ ] Search functionality works
- [ ] Metadata features work
- [ ] Rate limiting is active
- [ ] All tests pass

## 🎉 Next Steps After Deployment

1. **Domain Setup**: Configure custom domain
2. **CI/CD Pipeline**: Set up automated deployments
3. **Monitoring**: Configure alerts and dashboards
4. **Performance**: Monitor and optimize
5. **Scaling**: Plan for user growth

---

**Ready to deploy?** Let's start with Step 1: Setting up production Supabase! 