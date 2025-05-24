# LifeKB API Documentation
*Purpose: Complete API reference for LifeKB backend services with metadata and analytics features*

## Table of Contents
- [Authentication](#authentication)
- [Journal Entries](#journal-entries)
- [Search](#search)
- [Metadata & Analytics](#metadata--analytics)
- [Data Models](#data-models)
- [Error Handling](#error-handling)

## Base URL
- Development: `http://localhost:3001`
- Production: `https://your-vercel-app.vercel.app`

## Authentication

All protected endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### POST /api/auth

#### Signup
```bash
curl -X POST "/api/auth" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "signup",
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

#### Login
```bash
curl -X POST "/api/auth" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "login",
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "created_at": "2025-05-24T17:00:00Z"
  }
}
```

### GET /api/auth?health=true
Check API health status and database connectivity.

## Journal Entries

### POST /api/entries
Create a new journal entry with metadata support.

```bash
curl -X POST "/api/entries" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "text": "Today was an amazing day. I went hiking and felt so grateful for nature.",
    "tags": ["gratitude", "nature", "hiking"],
    "category": "personal",
    "mood": 9,
    "location": "Mount Wilson Trail",
    "weather": "sunny"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Entry created successfully",
  "entry": {
    "id": "uuid",
    "user_id": "uuid",
    "text": "Today was an amazing day...",
    "tags": ["gratitude", "nature", "hiking"],
    "category": "personal",
    "mood": 9,
    "location": "Mount Wilson Trail",
    "weather": "sunny",
    "embedding_status": "pending",
    "created_at": "2025-05-24T17:00:00Z",
    "updated_at": "2025-05-24T17:00:00Z"
  }
}
```

### GET /api/entries
List journal entries with pagination and filtering.

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `limit` (integer): Items per page (max: 100, default: 20)
- `category` (string): Filter by category
- `tags` (array): Filter by tags (can specify multiple)
- `min_mood` (integer): Minimum mood rating (1-10)
- `max_mood` (integer): Maximum mood rating (1-10)

```bash
curl -X GET "/api/entries?page=1&limit=10&category=personal&min_mood=7" \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "success": true,
  "items": [...],
  "total_count": 45,
  "page": 1,
  "limit": 10,
  "total_pages": 5,
  "has_next": true,
  "has_prev": false,
  "filters_applied": {
    "category": "personal",
    "tags": null,
    "min_mood": 7,
    "max_mood": null
  }
}
```

### GET /api/entries?id=<entry_id>
Get a specific journal entry.

### PUT /api/entries?id=<entry_id>
Update a journal entry (partial updates supported).

```bash
curl -X PUT "/api/entries?id=<entry_id>" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "mood": 10,
    "tags": ["updated", "better"]
  }'
```

### DELETE /api/entries?id=<entry_id>
Delete a journal entry.

## Search

### POST /api/search
Perform semantic search with metadata filtering.

```bash
curl -X POST "/api/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "query": "gratitude and nature",
    "limit": 5,
    "similarity_threshold": 0.2,
    "filters": {
      "tags": ["gratitude"],
      "category": "personal",
      "min_mood": 7,
      "max_mood": 10
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "query": "gratitude and nature",
  "results": [
    {
      "id": "uuid",
      "text": "Today was an amazing day...",
      "tags": ["gratitude", "nature", "hiking"],
      "category": "personal",
      "mood": 9,
      "location": "Mount Wilson Trail",
      "weather": "sunny",
      "created_at": "2025-05-24T17:00:00Z",
      "similarity": 0.89
    }
  ],
  "total_count": 1,
  "similarity_threshold": 0.2,
  "filters_applied": {
    "tags": ["gratitude"],
    "category": "personal",
    "min_mood": 7,
    "max_mood": 10
  },
  "search_time_ms": 23.45
}
```

### GET /api/search?action=status
Get embedding generation status.

### GET /api/search?action=process&limit=5
Process pending embeddings.

## Metadata & Analytics

### GET /api/metadata
Get comprehensive user metadata statistics and analytics.

**Query Parameters:**
- `days` (integer): Time period in days (default: 30, max: 365)

```bash
curl -X GET "/api/metadata?days=30" \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "period_days": 30,
    "basic_stats": {
      "total_entries": 156,
      "entries_with_tags": 142,
      "entries_with_category": 138,
      "entries_with_mood": 134,
      "average_mood": 7.2
    },
    "popular_tags": [
      {"tag": "gratitude", "count": 45},
      {"tag": "work", "count": 32},
      {"tag": "family", "count": 28}
    ],
    "popular_categories": [
      {"category": "personal", "count": 78},
      {"category": "work", "count": 42},
      {"category": "health", "count": 36}
    ],
    "mood_trend": [
      {"date": "2025-05-20", "mood": 8},
      {"date": "2025-05-21", "mood": 7}
    ],
    "insights": {
      "most_active_day": "Tuesday",
      "mood_patterns": {
        "Monday": 6.8,
        "Tuesday": 7.5,
        "Wednesday": 7.2
      },
      "location_patterns": [
        {"location": "Home", "count": 89},
        {"location": "Office", "count": 34}
      ],
      "weather_patterns": [
        {"weather": "sunny", "count": 67},
        {"weather": "cloudy", "count": 23}
      ],
      "tagging_frequency": 91.0
    },
    "generated_at": "2025-05-24T17:00:00Z"
  }
}
```

### POST /api/metadata
Get intelligent tag suggestions based on entry text.

```bash
curl -X POST "/api/metadata" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "text": "Had a challenging day at work but learned something new about leadership."
  }'
```

**Response:**
```json
{
  "success": true,
  "suggested_tags": ["work", "learning", "leadership", "growth", "challenge"]
}
```

## Data Models

### Journal Entry
```typescript
interface JournalEntry {
  id: string;
  user_id: string;
  text: string;
  tags?: string[];
  category?: EntryCategory;
  mood?: number; // 1-10
  location?: string;
  weather?: string;
  embedding_status: 'pending' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}
```

### Entry Categories
```typescript
enum EntryCategory {
  PERSONAL = "personal",
  WORK = "work",
  TRAVEL = "travel",
  HEALTH = "health",
  RELATIONSHIPS = "relationships",
  GOALS = "goals",
  GRATITUDE = "gratitude",
  REFLECTION = "reflection",
  LEARNING = "learning",
  CREATIVITY = "creativity",
  OTHER = "other"
}
```

### Search Filters
```typescript
interface MetadataFilter {
  tags?: string[];
  category?: EntryCategory;
  min_mood?: number;
  max_mood?: number;
  location?: string;
  weather?: string;
}
```

## Rate Limits

- **Authentication**: 5 requests per 5 minutes
- **Entry Creation**: 100 requests per minute
- **Entry Reading**: 200 requests per minute
- **Entry Updates**: 50 requests per minute
- **Entry Deletion**: 30 requests per minute
- **Search**: 50 requests per minute
- **Metadata Analytics**: 50 requests per minute
- **Tag Suggestions**: 30 requests per minute

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Error type",
  "message": "Detailed error description",
  "details": {
    "field": "Additional context"
  }
}
```

### Common HTTP Status Codes
- `200`: Success
- `201`: Created successfully
- `400`: Bad request (validation error)
- `401`: Unauthorized (invalid token)
- `403`: Forbidden (rate limited)
- `404`: Resource not found
- `429`: Too many requests
- `500`: Internal server error

### Common Error Types
- `Authentication failed`
- `Validation error`
- `Rate limit exceeded`
- `Resource not found`
- `Internal server error`

## Features Summary

### ✅ Implemented
- **Metadata Support**: Tags, categories, mood, location, weather
- **Advanced Filtering**: Multi-dimensional filtering across all attributes
- **Semantic Search**: OpenAI embeddings with metadata filtering
- **Analytics Dashboard**: User insights, trends, and statistics
- **Tag Suggestions**: AI-powered intelligent tag recommendations
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Security and data integrity
- **Monitoring**: Performance tracking and logging
- **Authentication**: Supabase-based secure auth

### 🔄 Performance Optimizations
- GIN indexes for array operations
- Standard B-tree indexes for filtering
- Pagination for large datasets
- Efficient database functions
- Connection pooling
- Response caching headers

### 🔒 Security Features
- JWT-based authentication
- Input size validation
- SQL injection prevention
- Rate limiting per endpoint
- CORS configuration
- Secure headers 