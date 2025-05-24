# LifeKB API Documentation
*Complete documentation of all LifeKB backend endpoints with architecture diagrams*

⚠️ **Current Status**: All endpoints are behind Vercel authentication protection as of latest deployment. This is a platform-level security feature and doesn't affect the API functionality once authenticated.

## 🏗️ System Architecture

```mermaid
graph TB
    Client[Web Client] --> Auth[/api/auth]
    Client --> Entries[/api/entries] 
    Client --> Search[/api/search]
    Client --> Embeddings[/api/embeddings]
    Client --> Metadata[/api/metadata]
    Client --> Monitoring[/api/monitoring]
    
    Auth --> Supabase[(Supabase Auth)]
    Entries --> DB[(PostgreSQL + Vector)]
    Search --> OpenAI[OpenAI API]
    Search --> DB
    Embeddings --> OpenAI
    Embeddings --> DB
    Metadata --> DB
    Monitoring --> DB
    Monitoring --> OpenAI
    
    DB --> RLS[Row Level Security]
    RLS --> UserA[User A Data]
    RLS --> UserB[User B Data]
    RLS --> UserC[User C Data]
```

## 🔐 Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as /api/auth
    participant S as Supabase Auth
    participant DB as Database
    
    C->>A: POST /login {email, password}
    A->>S: POST /auth/v1/token
    S-->>A: {access_token, user.id}
    A->>A: Generate JWT with user_id
    A-->>C: {token: "JWT", user_id: "uuid"}
    
    Note over C: Store JWT for future requests
    
    C->>A: POST /signup {email, password}
    A->>S: POST /auth/v1/signup
    S->>DB: Insert into auth.users
    S-->>A: {user.id, user.email}
    A-->>C: {success: true, user_id: "uuid"}
```

### Authentication Endpoints

| Method | Endpoint | Purpose | Request Body | Response |
|--------|----------|---------|--------------|----------|
| `POST` | `/api/auth/login` | User login | `{email: string, password: string}` | `{success: true, token: "jwt", user_id: "uuid"}` |
| `POST` | `/api/auth/signup` | User registration | `{email: string, password: string}` | `{success: true, user_id: "uuid"}` |
| `GET` | `/api/auth` | API status | - | `{api: "LifeKB Auth", status: "active"}` |

## 📝 Journal Entries API

### Entry Creation Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant E as /api/entries
    participant DB as Database
    participant EMB as /api/embeddings
    participant AI as OpenAI
    
    C->>E: POST /entries<br/>{text: "My journal entry"}
    E->>E: Verify JWT & extract user_id
    E->>DB: INSERT journal_entries<br/>(user_id, text, embedding_status: 'pending')
    DB-->>E: {id: "uuid", created_at: "timestamp"}
    E-->>C: {success: true, entry: {...}}
    
    Note over E,EMB: Background embedding generation
    EMB->>AI: Generate embedding for text
    AI-->>EMB: [1536-dimensional vector]
    EMB->>DB: UPDATE embedding & status='completed'
```

### Entries Endpoints

| Method | Endpoint | Purpose | Request | Response |
|--------|----------|---------|---------|----------|
| `GET` | `/api/entries` | List all user entries | Headers: `Authorization: Bearer <jwt>` | `{success: true, entries: [...], total: N}` |
| `GET` | `/api/entries?id=<uuid>` | Get specific entry | Headers: `Authorization: Bearer <jwt>` | `{success: true, entry: {...}}` |
| `POST` | `/api/entries` | Create new entry | `{text: string}` | `{success: true, entry: {...}}` |
| `PUT` | `/api/entries?id=<uuid>` | Update entry | `{text: string}` | `{success: true, entry: {...}}` |
| `DELETE` | `/api/entries?id=<uuid>` | Delete entry | - | `{success: true}` |

### Database Schema & RLS

```mermaid
erDiagram
    auth_users {
        uuid id PK
        string email
        timestamp created_at
    }
    
    journal_entries {
        uuid id PK
        uuid user_id FK
        text text
        vector1536 embedding
        string embedding_status
        text_array tags
        string category
        int mood
        timestamp created_at
        timestamp updated_at
    }
    
    auth_users ||--o{ journal_entries : "owns"
    
    journal_entries {
        RLS_POLICY "Users can access own entries"
        WHERE "auth.uid() = user_id"
    }
```

## 🔍 Semantic Search Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant S as /api/search
    participant AI as OpenAI
    participant DB as Database
    
    C->>S: POST /search<br/>{query: "authentication working", limit: 10}
    S->>S: Verify JWT & extract user_id
    S->>AI: Generate embedding for query
    AI-->>S: [1536-dimensional vector]
    S->>DB: CALL search_entries(query_embedding, user_id)
    
    Note over DB: Cosine similarity search<br/>1 - (embedding <=> query_embedding)
    
    DB-->>S: [{id, text, similarity}, ...]
    S-->>C: {results: [...], search_time_ms: 45}
```

### Search Endpoints

| Method | Endpoint | Purpose | Request Body | Response |
|--------|----------|---------|--------------|----------|
| `GET` | `/api/search` | API info | - | `{api: "LifeKB Search", features: [...]}` |
| `POST` | `/api/search` | Semantic search | `{query: string, limit?: number, similarity_threshold?: number}` | `{success: true, results: [...], search_time_ms: number}` |

### Search Response Example
```json
{
  "success": true,
  "query": "authentication system working",
  "results": [
    {
      "id": "80b19f75-7155-47b3-8642-1f71a7f21805",
      "text": "This is my first journal entry! The authentication system is now working...",
      "created_at": "2024-01-15T10:30:00Z",
      "similarity": 0.496
    }
  ],
  "total_count": 1,
  "similarity_threshold": 0.1,
  "search_time_ms": 47.23
}
```

## 🤖 Vector Embeddings API

```mermaid
flowchart TD
    A[New Journal Entry] --> B{Has Embedding?}
    B -->|No| C[POST /api/embeddings]
    B -->|Yes| D[Skip Generation]
    
    C --> E[Extract Text Content]
    E --> F[Call OpenAI API]
    F --> G[text-embedding-3-small]
    G --> H[1536-dimensional Vector]
    H --> I[Store in Database]
    I --> J[Update Status: 'completed']
    
    J --> K[Available for Search]
    D --> K
```

### Embeddings Endpoints

| Method | Endpoint | Purpose | Request Body | Response |
|--------|----------|---------|--------------|----------|
| `GET` | `/api/embeddings` | API status | - | `{api: "LifeKB Embeddings", models: [...]}` |
| `POST` | `/api/embeddings` | Generate embedding | `{entry_id: "uuid"}` | `{success: true, embedding: [...]}` |
| `POST` | `/api/embeddings/batch` | Batch generation | `{entry_ids: ["uuid1", "uuid2"]}` | `{completed: N, failed: N}` |

## 📊 Multi-User Data Isolation

```mermaid
graph LR
    subgraph "User A Session"
        A1[JWT: user_a_id]
        A2[Query: SELECT * FROM journal_entries]
        A3[RLS Filter: WHERE user_id = user_a_id]
        A4[Results: Only User A's entries]
    end
    
    subgraph "User B Session"
        B1[JWT: user_b_id]
        B2[Query: SELECT * FROM journal_entries]
        B3[RLS Filter: WHERE user_id = user_b_id]
        B4[Results: Only User B's entries]
    end
    
    A1 --> A2 --> A3 --> A4
    B1 --> B2 --> B3 --> B4
    
    subgraph "Database Layer"
        DB[(journal_entries table)]
        RLS[Row Level Security]
        DB --> RLS
    end
    
    A3 --> RLS
    B3 --> RLS
```

**Each user has completely isolated data through PostgreSQL Row Level Security:**
- User A can only see/modify entries where `user_id = user_a_id`  
- User B can only see/modify entries where `user_id = user_b_id`
- Zero application code needed - database enforces isolation automatically
- Scales to unlimited users with no performance impact

## 🔒 Security Features

### JWT Authentication
- Custom JWT implementation with HMAC-SHA256
- User ID embedded in token payload  
- Automatic expiration checking
- Bearer token authorization header

### Row Level Security (RLS)
```sql
-- Automatic user isolation
CREATE POLICY "Users can access own entries" ON journal_entries
    FOR ALL USING (auth.uid() = user_id);
```

### Input Validation
- Text length limits (10,000 characters)
- Vector dimension validation (1536)
- SQL injection prevention via parameterized queries
- Rate limiting and request size limits

## 📈 Performance Characteristics

### Search Performance
- **Vector Index**: IVFFlat with cosine similarity
- **Typical Search Time**: 15-50ms for 1000+ entries
- **Similarity Threshold**: 0.1 (configurable)
- **Result Limits**: Max 50 results per query

### Embedding Generation  
- **Model**: OpenAI text-embedding-3-small
- **Dimensions**: 1536
- **API Latency**: ~200-500ms per request
- **Batch Processing**: Supported for multiple entries

## 🚀 Deployment Architecture

```mermaid
graph TB
    subgraph "Vercel Serverless"
        API1[/api/auth.py]
        API2[/api/entries.py] 
        API3[/api/search.py]
        API4[/api/embeddings.py]
    end
    
    subgraph "Supabase Backend"
        AUTH[Supabase Auth]
        DB[(PostgreSQL + pgvector)]
        RLS[Row Level Security]
    end
    
    subgraph "External Services"
        OPENAI[OpenAI API<br/>text-embedding-3-small]
    end
    
    API1 <--> AUTH
    API2 <--> DB
    API3 <--> DB
    API3 <--> OPENAI
    API4 <--> DB
    API4 <--> OPENAI
    
    DB --> RLS
```

## 🛠️ Environment Setup

### Required Environment Variables
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
OPENAI_API_KEY=sk-your-openai-key
JWT_SECRET_KEY=your-jwt-secret
```

### Database Setup
```sql
-- Enable vector extension
CREATE EXTENSION vector;

-- Create journal entries table
CREATE TABLE journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    embedding vector(1536),
    embedding_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;

-- Create RLS policy
CREATE POLICY "Users can access own entries" ON journal_entries
    FOR ALL USING (auth.uid() = user_id);
```

## 📋 API Response Standards

### Success Response Format
```json
{
  "success": true,
  "data": {...},
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Response Format  
```json
{
  "error": "Error description",
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "error"
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error 

## 📊 New Production Endpoints

### Metadata Analytics API

| Method | Endpoint | Purpose | Request | Response |
|--------|----------|---------|---------|----------|
| `GET` | `/api/metadata?days=30` | User analytics stats | Headers: `Authorization: Bearer <jwt>` | `{success: true, metadata: {...}}` |
| `POST` | `/api/metadata` | API info | - | `{api: "LifeKB Metadata", features: [...]}` |

**Features:**
- Tag usage analysis and popularity rankings
- Mood trend tracking with daily averages
- Category statistics and distribution
- Writing insights (frequency, active days, text length)
- Embedding completion rates and status

### System Monitoring API

| Method | Endpoint | Purpose | Request | Response |
|--------|----------|---------|---------|----------|
| `GET` | `/api/monitoring?type=health` | System health check | - | `{status: "healthy", components: {...}}` |
| `GET` | `/api/monitoring?type=metrics` | Basic system metrics | - | `{success: true, metrics: {...}}` |
| `GET` | `/api/monitoring?type=endpoints` | API endpoint status | - | `{success: true, endpoints: {...}}` |
| `GET` | `/api/monitoring?type=full` | Complete report | Optional: `Authorization: Bearer <jwt>` | `{health: {...}, metrics: {...}, endpoints: {...}}` |

**Features:**
- Database connection health monitoring
- OpenAI API configuration validation
- Environment variable verification
- User count and entry statistics
- Embedding generation performance metrics
- API endpoint availability testing 