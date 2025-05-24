# LifeKB Backend

A privacy-first journaling backend with AI-powered semantic search, built with FastAPI and deployed on Vercel serverless functions.

## 🎯 Overview

LifeKB transforms personal journal entries into a searchable knowledge base using AI embeddings. The backend provides:

- **User Authentication** via Supabase Auth
- **Journal Entry Management** with full CRUD operations
- **AI Embeddings Generation** using OpenAI's text-embedding-3-small
- **Semantic Search** via pgvector (PostgreSQL vector extension)
- **RESTful API** optimized for iOS app integration

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

## 🛠️ Tech Stack

- **API Framework**: FastAPI (Python 3.9+)
- **Deployment**: Vercel Serverless Functions
- **Database**: Supabase PostgreSQL with pgvector
- **Authentication**: Supabase Auth (JWT-based)
- **AI Embeddings**: OpenAI text-embedding-3-small
- **Vector Search**: pgvector extension

## 📁 Project Structure

```
lifekb-api/
├── api/                          # Vercel serverless functions
│   ├── auth.py                  # Authentication endpoints
│   ├── entries.py               # Journal CRUD operations
│   ├── search.py                # Semantic search endpoint
│   └── embeddings.py            # Embedding management
├── app/                         # Shared application code
│   ├── __init__.py
│   ├── database.py              # Supabase connection & queries
│   ├── models.py                # Pydantic request/response models
│   ├── embeddings.py            # OpenAI integration
│   ├── auth.py                  # JWT validation & user management
│   └── utils.py                 # Helper functions
├── scripts/                     # Utility scripts
│   └── setup_database.sql       # Database initialization
├── requirements.txt             # Python dependencies
├── vercel.json                  # Vercel deployment config
├── env.example                  # Environment template
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Supabase account (free tier)
- OpenAI API key
- Vercel account (free tier)

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd lifekb-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env with your credentials
```

Required environment variables:
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Optional
ENVIRONMENT=development
DEBUG=true
```

### 3. Database Setup

1. Create new Supabase project
2. In SQL Editor, run the setup script:
   ```sql
   -- Copy and paste contents from scripts/setup_database.sql
   ```
3. Enable pgvector extension if not already enabled

### 4. Local Development

```bash
# Install Vercel CLI
npm i -g vercel

# Start local development server
vercel dev

# API will be available at http://localhost:3000
```

### 5. Testing

```bash
# Test authentication
curl -X POST http://localhost:3000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Test health endpoints
curl http://localhost:3000/api/auth/health
curl http://localhost:3000/api/entries/health
curl http://localhost:3000/api/search/health
curl http://localhost:3000/api/embeddings/health
```

## 📚 API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/signup` | User registration |
| POST | `/api/auth/refresh` | Refresh JWT token |

### Journal Entry Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/entries/` | Create new entry |
| GET | `/api/entries/` | Get entries (paginated) |
| GET | `/api/entries/{id}` | Get specific entry |
| PUT | `/api/entries/{id}` | Update entry |
| DELETE | `/api/entries/{id}` | Delete entry |

### Search Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search/` | Semantic search |
| GET | `/api/search/suggestions` | Search suggestions |
| GET | `/api/search/similar/{id}` | Find similar entries |

### Embedding Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/embeddings/status` | Embedding status |
| POST | `/api/embeddings/regenerate` | Regenerate all embeddings |
| POST | `/api/embeddings/process-pending` | Process pending embeddings |

## 🔐 Authentication

All endpoints (except auth and health) require JWT authentication:

```bash
# Include in request headers
Authorization: Bearer <your-jwt-token>
```

## 📊 Example Usage

### Create Journal Entry

```bash
curl -X POST http://localhost:3000/api/entries/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Today I learned about semantic search and vector databases. It was fascinating to see how AI can understand the meaning behind text."
  }'
```

### Semantic Search

```bash
curl -X POST http://localhost:3000/api/search/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "learning about technology",
    "limit": 5,
    "similarity_threshold": 0.1
  }'
```

## 🚀 Deployment

### Vercel Deployment

```bash
# Login to Vercel
vercel login

# Deploy
vercel

# Set environment variables in Vercel dashboard
# Project Settings > Environment Variables
```

### Environment Variables in Vercel

Add all environment variables from your `.env` file to Vercel:
1. Go to Vercel Dashboard
2. Select your project
3. Go to Settings > Environment Variables
4. Add each variable

## 🔍 Monitoring & Debugging

### Health Checks

Each service has a health endpoint:
- `/api/auth/health`
- `/api/entries/health`  
- `/api/search/health`
- `/api/embeddings/health`

### Logging

Logs are available in:
- **Local Development**: Console output
- **Vercel Production**: Vercel Dashboard > Functions > Logs

### Common Issues

1. **Database Connection Issues**
   - Check Supabase credentials
   - Verify database is running
   - Check RLS policies

2. **OpenAI API Issues**
   - Verify API key is valid
   - Check rate limits
   - Monitor usage quotas

3. **Authentication Issues**
   - Verify JWT token format
   - Check token expiration
   - Ensure proper CORS setup

## 💰 Cost Optimization

### Free Tier Limits
- **Vercel**: 100GB bandwidth, 100GB function execution time/month
- **Supabase**: 500MB database, 50K monthly active users
- **OpenAI**: Pay-per-use (~$0.00002 per 1K tokens)

### Cost Estimates
- **Small Scale** (100 users): ~$2-5/month
- **Medium Scale** (1000 users): ~$15-25/month

## 🧪 Testing

```bash
# Run unit tests (when implemented)
pytest tests/

# Load testing
pip install locust
locust -f tests/load_test.py
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support:
1. Check the documentation above
2. Review common issues section
3. Check Vercel/Supabase documentation
4. Open an issue in the repository

---

**Built with ❤️ for privacy-first personal knowledge management** 