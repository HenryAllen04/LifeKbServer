# LifeKB v1 API Documentation

## Overview
The LifeKB v1 API provides a complete backend for personal knowledge management and journaling with AI-powered features. Built on Supabase with serverless Vercel deployment.

## Base URL
```
Production: https://life-kb-server-henryallen04-henryallen04s-projects.vercel.app
```

## Authentication
All API endpoints (except auth) require JWT Bearer token authentication:
```
Authorization: Bearer <jwt_token>
```

Get tokens via the `/api/auth_working` endpoint.

## Core Features
- ✅ **User Authentication** - JWT-based with Supabase Auth
- ✅ **Journal Entries** - Full CRUD with metadata (tags, mood, location)
- ✅ **AI Embeddings** - OpenAI text-embedding-3-small integration
- ✅ **Semantic Search** - Vector similarity search (coming soon)
- ✅ **User Isolation** - Complete data separation via RLS
- ✅ **Zero Dependencies** - Pure Python with urllib only

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| [`/api/auth_working`](./auth.md) | POST | Login/register users |

### Journal Management  
| Endpoint | Method | Description |
|----------|--------|-------------|
| [`/api/entries`](./entries.md) | GET | List user's journal entries |
| [`/api/entries`](./entries.md) | POST | Create new journal entry |
| [`/api/entries?id={id}`](./entries.md) | GET | Get specific entry |
| [`/api/entries`](./entries.md) | PUT | Update existing entry |
| [`/api/entries`](./entries.md) | DELETE | Delete entry |

### AI & Embeddings
| Endpoint | Method | Description |
|----------|--------|-------------|
| [`/api/embeddings`](./embeddings.md) | GET | Get embedding status/info |
| [`/api/embeddings`](./embeddings.md) | POST | Process pending embeddings |

### Utilities
| Endpoint | Method | Description |
|----------|--------|-------------|
| [`/api/setup_demo`](./setup_demo.md) | GET | Check demo setup status |
| [`/api/setup_demo`](./setup_demo.md) | POST | Create demo data |
| [`/api/fix_database_schema`](./database_fix.md) | GET | Diagnose database schema |
| [`/api/fix_database_schema`](./database_fix.md) | POST | Fix database constraints |

## Response Format
All endpoints return JSON with consistent structure:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Error Response
```json
{
  "error": "Error description",
  "timestamp": "2024-01-01T12:00:00Z", 
  "status": "error"
}
```

## HTTP Status Codes
- `200` - Success
- `201` - Created  
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `409` - Conflict
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

## Rate Limiting
| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Authentication | 20 requests | 1 hour |
| Read Operations | 100 requests | 1 hour |
| Write Operations | 50 requests | 1 hour |
| Embeddings | 30 requests | 1 hour |

Rate limit headers included in responses:
```
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995200
```

## Data Models

### User
- Managed by Supabase Auth (`auth.users`)
- UUID primary key
- Email/password authentication

### Journal Entry
```typescript
interface JournalEntry {
  id: string;           // UUID
  user_id: string;      // References auth.users(id)
  text: string;         // Entry content
  tags: string[];       // Optional tags
  category: string;     // Optional category
  mood: number;         // 1-10 scale
  location: string;     // Optional location
  weather: string;      // Optional weather
  embedding: number[];  // AI-generated vector (1536 dims)
  embedding_status: 'pending' | 'completed' | 'failed';
  created_at: string;   // ISO timestamp
  updated_at: string;   // ISO timestamp
}
```

## Security Features
- **JWT Authentication** with HMAC-SHA256
- **Row Level Security (RLS)** - Users see only their data
- **Rate Limiting** per IP address
- **Input Validation** and sanitization
- **CORS Support** for web clients

## Environment Requirements
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
JWT_SECRET_KEY=your-jwt-secret
OPENAI_API_KEY=your-openai-key
```

## Quick Start

### 1. Authentication
```bash
curl -X POST "/api/auth_working" \
  -H "Content-Type: application/json" \
  -d '{"action": "login", "email": "demo@example.com", "password": "demo123"}'
```

### 2. Create Entry
```bash
curl -X POST "/api/entries" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "My first journal entry", "mood": 8, "tags": ["test"]}'
```

### 3. Generate Embeddings
```bash
curl -X POST "/api/embeddings" \
  -H "Authorization: Bearer <token>" \
  -d '{"action": "process"}'
```

## Architecture
- **Deployment**: Vercel Serverless Functions
- **Database**: Supabase PostgreSQL with pgvector
- **AI**: OpenAI text-embedding-3-small
- **Authentication**: Supabase Auth + custom JWT
- **Security**: Row Level Security + rate limiting

## Links
- [Supabase Project Dashboard](https://supabase.com/dashboard)
- [Vercel Deployment Dashboard](https://vercel.com/dashboard)
- [OpenAI API Documentation](https://platform.openai.com/docs)

---

*For technical implementation details, see [Architecture Documentation](../SUPABASE_AUTH_ARCHITECTURE.md)* 