# LifeKB RAG Search API Documentation

## Overview

The RAG (Retrieval-Augmented Generation) Search API provides AI-powered insights from your personal journal entries. It combines semantic search with OpenAI's language models to generate thoughtful, contextual responses about your life patterns, emotions, and experiences.

## 🔐 Privacy & Security

**Important**: This endpoint sends relevant journal entries to OpenAI for AI analysis. Only entries matching your search query are sent, never your entire journal.

- ✅ **Data Minimization**: Only relevant entries are shared
- ✅ **Authentication Required**: JWT token authentication
- ✅ **User Consent**: Explicit opt-in for RAG functionality
- ✅ **Source Attribution**: All AI responses include source entries

## 🚀 Quick Start

### Basic RAG Search

```bash
curl -X POST https://your-domain.vercel.app/api/search_rag \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "when was the last time I felt anxious?",
    "mode": "conversational"
  }'
```

### Response Example

```json
{
  "success": true,
  "query": "when was the last time I felt anxious?",
  "ai_response": "Based on your journal entries, you last mentioned feeling anxious on March 15th, 2024. You described feeling 'completely overwhelmed at work' and mentioned difficulty sleeping. This followed a pattern of increasing stress over 2 weeks related to a major project deadline.",
  "mode": "conversational",
  "total_sources": 3,
  "sources": [
    {
      "id": "uuid-here",
      "text": "I'm feeling completely overwhelmed at work...",
      "created_at": "2024-03-15T10:30:00Z",
      "similarity": 0.824
    }
  ],
  "processing_time_ms": 2150
}
```

## 📋 API Reference

### Endpoint
```
POST /api/search_rag
```

### Headers
- `Authorization`: Bearer JWT token (required)
- `Content-Type`: application/json

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search query or question |
| `mode` | string | "conversational" | Response mode: `conversational`, `summary`, `analysis` |
| `include_sources` | boolean | true | Include source journal entries in response |
| `limit` | integer | 10 | Max number of source entries (max: 20) |

### Response Format

```json
{
  "success": boolean,
  "query": "string",
  "ai_response": "string",
  "mode": "string",
  "total_sources": number,
  "sources": [
    {
      "id": "string",
      "text": "string", 
      "created_at": "ISO timestamp",
      "similarity": number
    }
  ],
  "processing_time_ms": number
}
```

## 🎭 Response Modes

### Conversational Mode (default)
**Purpose**: Natural, empathetic responses to personal questions

```json
{
  "query": "How have I been handling stress lately?",
  "mode": "conversational"
}
```

**AI Response Style**: 
- Supportive and empathetic
- References specific entries
- Actionable insights
- Personal and conversational tone

### Summary Mode
**Purpose**: Organized summaries of themes and patterns

```json
{
  "query": "Summarize my mood over the past month",
  "mode": "summary"
}
```

**AI Response Style**:
- Clear, structured summaries
- Key themes and patterns
- Objective yet empathetic
- Highlights growth moments

### Analysis Mode
**Purpose**: Analytical insights and pattern recognition

```json
{
  "query": "What triggers my productivity?",
  "mode": "analysis"
}
```

**AI Response Style**:
- Pattern analysis
- Trend identification
- Behavioral observations
- Constructive insights

## 💡 Use Cases & Examples

### Temporal Queries
```bash
# When-based questions
curl -X POST /api/search_rag \
  -d '{"query": "When was the last time I felt burnout?"}'

# Timeline analysis
curl -X POST /api/search_rag \
  -d '{"query": "How has my mood changed over the past month?", "mode": "summary"}'
```

### Pattern Analysis
```bash
# Behavioral patterns
curl -X POST /api/search_rag \
  -d '{"query": "What activities make me happiest?", "mode": "analysis"}'

# Trigger identification
curl -X POST /api/search_rag \
  -d '{"query": "What triggers my stress?", "mode": "analysis"}'
```

### Insight Generation
```bash
# Personal growth
curl -X POST /api/search_rag \
  -d '{"query": "What lessons have I learned this year?", "mode": "conversational"}'

# Recurring themes
curl -X POST /api/search_rag \
  -d '{"query": "What are my recurring themes?", "mode": "summary"}'
```

## ⚡ Performance & Costs

| Metric | Value |
|--------|-------|
| **Response Time** | 2-5 seconds |
| **Cost per Query** | $0.01-0.05 |
| **Model Used** | GPT-4o-mini |
| **Max Tokens** | 500 |
| **Rate Limiting** | User-based authentication |

### Cost Comparison

| Search Type | Speed | Cost | Privacy | Value |
|-------------|-------|------|---------|-------|
| **Pure Semantic** | ~50ms | $0.0004 | High | Raw data |
| **RAG Search** | ~2-5s | $0.01-0.05 | Medium | AI insights |

## 🛡️ Error Handling

### Authentication Errors
```json
{
  "error": "Authentication required",
  "timestamp": "2024-03-15T10:30:00Z",
  "status": "error"
}
```

### Validation Errors
```json
{
  "error": "Mode must be one of: conversational, summary, analysis",
  "timestamp": "2024-03-15T10:30:00Z", 
  "status": "error"
}
```

### API Errors
```json
{
  "error": "OpenAI Chat API error: 429 - Rate limit exceeded",
  "timestamp": "2024-03-15T10:30:00Z",
  "status": "error"
}
```

## 🔧 Integration Examples

### Frontend JavaScript
```javascript
async function performRAGSearch(query, mode = 'conversational') {
  try {
    const response = await fetch('/api/search_rag', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query,
        mode,
        include_sources: true,
        limit: 10
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      return {
        aiResponse: data.ai_response,
        sources: data.sources,
        processingTime: data.processing_time_ms
      };
    } else {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('RAG search failed:', error);
    throw error;
  }
}

// Usage
const result = await performRAGSearch(
  "What makes me feel most productive?", 
  "analysis"
);
```

### Python Client
```python
import requests
import json

def rag_search(query, token, mode="conversational", include_sources=True):
    url = "https://your-domain.vercel.app/api/search_rag"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": query,
        "mode": mode,
        "include_sources": include_sources,
        "limit": 10
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error: {response.status_code} - {response.text}")

# Usage
result = rag_search(
    "How do I typically handle difficult situations?",
    user_token,
    mode="analysis"
)

print(f"AI Response: {result['ai_response']}")
print(f"Based on {result['total_sources']} entries")
```

## 🔄 Fallback Behavior

When RAG search encounters issues:

1. **No relevant entries found**: Returns helpful message suggesting alternative keywords
2. **OpenAI API failure**: Falls back to error message with suggestion to try pure semantic search
3. **Token limit exceeded**: Truncates context intelligently while preserving most relevant entries

## 📊 Monitoring & Analytics

The API automatically tracks:
- Processing time per request
- Number of source entries used
- Mode distribution
- Error rates
- User adoption metrics

## 🚨 Rate Limiting

- Authentication-based rate limiting
- Expensive RAG queries limited per user
- Fallback to pure search if RAG fails
- Cost monitoring and alerts

## 🔗 Related APIs

- **Pure Semantic Search**: `/api/search` - Fast, privacy-first search
- **Entry Management**: `/api/entries` - CRUD operations for journal entries
- **User Authentication**: `/api/auth` - JWT token management

## 📝 Best Practices

1. **Query Formulation**: Use natural, specific questions for best results
2. **Mode Selection**: Choose appropriate mode for your use case
3. **Privacy Awareness**: Understand that entries are sent to OpenAI
4. **Cost Management**: Monitor usage for expensive RAG queries
5. **Fallback Strategy**: Always have pure search as backup

## 🆕 Future Enhancements

- [ ] Streaming responses for long answers
- [ ] Follow-up question suggestions  
- [ ] Conversation history
- [ ] Custom prompt templates
- [ ] Response caching
- [ ] Enhanced privacy modes 