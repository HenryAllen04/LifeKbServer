# LifeKB Backend Specification

## 🎯 Project Overview

### What is LifeKB?
LifeKB is a privacy-first iOS journaling application that transforms personal journal entries into a searchable knowledge base using AI embeddings. The iOS app allows users to:

- Write and store journal entries locally
- Perform semantic search across their personal history  
- Sync data across devices securely
- Generate insights from their writing patterns

### Backend Purpose
This backend server provides:
- **User Authentication** via Supabase Auth
- **Journal Entry Storage** in PostgreSQL with user isolation
- **AI Embeddings Generation** using OpenAI's text-embedding-3-small
- **Semantic Search** via pgvector (PostgreSQL vector extension)
- **RESTful API** for iOS app communication

## 🏗️ Architecture

```
iOS App (Swift/SwiftUI) 
    ↓ HTTPS/JSON
FastAPI Server (Python) - Vercel Serverless
    ↓ SQL
Supabase (PostgreSQL + Auth + pgvector)
    ↓ API
OpenAI Embeddings (text-embedding-3-small)
```

### Key Design Principles
- **Privacy First**: User data is isolated and encrypted
- **Serverless**: Cost-effective auto-scaling with Vercel
- **AI-Powered**: Semantic search beyond keyword matching
- **iOS Native**: Optimized for mobile-first experience

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI (Python 3.9+) | Fast async API with automatic docs |
| **Deployment** | Vercel Serverless | Zero-config deployment with generous free tier |
| **Database** | Supabase PostgreSQL | Managed Postgres with built-in auth |
| **Vector Search** | pgvector extension | High-performance similarity search |
| **Authentication** | Supabase Auth | JWT-based auth with social logins |
| **AI Embeddings** | OpenAI API | text-embedding-3-small (1536 dimensions) |
| **Environment** | Python 3.9+ | Async/await support for performance |

## 🗄️ Database Schema

### Tables

```sql
-- Users table (managed by Supabase Auth)
-- auth.users table exists automatically

-- Journal entries with vector embeddings
CREATE TABLE journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    embedding vector(1536), -- OpenAI embedding dimensions
    embedding_status TEXT DEFAULT 'pending', -- pending, completed, failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Row Level Security (RLS) for user isolation
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access own entries" ON journal_entries
    FOR ALL USING (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX idx_journal_entries_user_id ON journal_entries(user_id);
CREATE INDEX idx_journal_entries_created_at ON journal_entries(created_at DESC);
CREATE INDEX idx_journal_entries_embedding ON journal_entries 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Vector Search Function

```sql
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
```

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/signup` - User registration  
- `POST /api/auth/refresh` - Refresh JWT token

### Journal Entries
- `POST /api/entries` - Create new journal entry
- `GET /api/entries` - Get user's entries (paginated)
- `PUT /api/entries/{id}` - Update entry
- `DELETE /api/entries/{id}` - Delete entry

### Search
- `POST /api/search` - Semantic search across user's entries
- `GET /api/search/suggestions` - Get search suggestions

### Embeddings
- `POST /api/embeddings/regenerate` - Regenerate embeddings for user
- `GET /api/embeddings/status` - Check embedding generation status

## 📁 Project Structure

```
lifekb-api/
├── api/                          # Vercel serverless functions
│   ├── entries.py               # Journal CRUD operations
│   ├── search.py                # Semantic search endpoint
│   ├── auth.py                  # Authentication endpoints
│   └── embeddings.py            # Embedding management
├── app/                         # Shared application code
│   ├── __init__.py
│   ├── database.py              # Supabase connection & queries
│   ├── models.py                # Pydantic request/response models
│   ├── embeddings.py            # OpenAI integration
│   ├── auth.py                  # JWT validation & user management
│   └── utils.py                 # Helper functions
├── tests/                       # Test suite
│   ├── test_entries.py
│   ├── test_search.py
│   └── test_auth.py
├── scripts/                     # Utility scripts
│   ├── setup_database.sql       # Database initialization
│   └── seed_data.py             # Test data generation
├── requirements.txt             # Python dependencies
├── vercel.json                  # Vercel deployment config
├── .env.example                 # Environment template
├── .gitignore
└── README.md
```

## 🚀 Setup Guide

### Prerequisites
- Python 3.9+
- Supabase account (free tier)
- OpenAI API key
- Vercel account (free tier)
- Git

### 1. Repository Setup

```bash
# Create new repository
mkdir lifekb-api && cd lifekb-api
git init

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (create requirements.txt first)
pip install -r requirements.txt
```

### 2. Supabase Configuration

1. Create new Supabase project at [supabase.com](https://supabase.com)
2. Navigate to SQL Editor and run:
   ```sql
   -- Enable pgvector extension
   CREATE EXTENSION IF NOT EXISTS vector;
   
   -- Run the database schema from above
   ```
3. Get your project credentials:
   - Project URL: `https://your-project.supabase.co`
   - Service Role Key (for server-side operations)

### 3. Environment Variables

Create `.env` file:
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# App Config
ENVIRONMENT=development
DEBUG=true
```

### 4. Local Development

```bash
# Install Vercel CLI
npm i -g vercel

# Start local development server
vercel dev

# Test endpoints
curl http://localhost:3000/api/entries
```

### 5. Vercel Deployment

```bash
# Login to Vercel
vercel login

# Deploy (first time)
vercel

# Set environment variables in Vercel dashboard
# Project Settings > Environment Variables
```

### 6. iOS App Integration

Update your iOS app's API client to point to:
- Development: `http://localhost:3000`
- Production: `https://your-app.vercel.app`

## 💰 Cost Analysis

### Free Tier Limits
- **Vercel**: 100GB bandwidth, 100GB function execution time/month
- **Supabase**: 500MB database, 50K monthly active users  
- **OpenAI**: Pay-per-use (~$0.00002 per 1K tokens)

### Estimated Monthly Costs
- **Development**: $0 (free tiers)
- **Small Scale** (100 users): ~$2-5/month
- **Medium Scale** (1000 users): ~$15-25/month
- **Large Scale** (10K users): ~$50-100/month

## 🧪 Testing Strategy

### Unit Tests
```bash
# Run tests
pytest tests/

# With coverage
pytest tests/ --cov=app
```

### Integration Tests
```bash
# Test with local Supabase
pytest tests/integration/

# Test deployment
vercel dev & pytest tests/e2e/
```

### Load Testing
```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load_test.py
```

## 🔒 Security Considerations

1. **JWT Validation**: All endpoints validate Supabase JWT tokens
2. **Row Level Security**: Database enforces user data isolation
3. **Rate Limiting**: Implement rate limiting for embedding generation
4. **Input Sanitization**: Validate all user inputs
5. **CORS Configuration**: Restrict origins to iOS app domain
6. **Environment Variables**: Never commit secrets to git

## 📋 Development Workflow

1. **Feature Development**: Create branch, implement feature, write tests
2. **Local Testing**: Use `vercel dev` for local API testing
3. **PR Review**: Automated tests must pass
4. **Staging**: Deploy to staging environment for integration testing
5. **Production**: Deploy via Vercel GitHub integration

## 🎯 Success Metrics

- **Performance**: API response time < 200ms
- **Reliability**: 99.9% uptime
- **Scalability**: Handle 1000 concurrent users
- **Search Quality**: Semantic search accuracy > 80%
- **Cost Efficiency**: Stay within $25/month for first 1000 users

---

Ready to build the future of personal knowledge management! 🚀 