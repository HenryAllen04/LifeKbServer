# LifeKB API Postman Collection Guide

## 🚀 Quick Start

### 1. Import Files
1. **Import Collection**: `LifeKB_API_Collection.postman_collection.json`
2. **Import Environment**: `LifeKB_Local_Environment.postman_environment.json`
3. **Select Environment**: Choose "LifeKB Local Environment" in top-right

### 2. Test User Account Ready to Use!
✅ **Email**: `test@example.com`  
✅ **Password**: `testpassword123`  
✅ **User ID**: `6f395e39-92b2-4a19-a8a9-c9304ee768a6`

## 🔐 **IMPORTANT: Fixed Authentication**

### Login Request Format (CORRECTED):
```json
{
  "email": "test@example.com", 
  "password": "testpassword123",
  "action": "login"
}
```

**❌ Wrong**: `POST /api/auth/login`  
**✅ Correct**: `POST /api/auth` (with `action: "login"`)

## 📊 **Metadata API Status Fixed**

### API Status Endpoints:
- **Metadata Status**: `POST /api/metadata` (no auth required) ✅
- **User Analytics**: `GET /api/metadata?days=N` (auth required) ✅

**Note**: The metadata API status check uses POST method to return API capabilities without requiring authentication, while GET method returns actual user analytics and requires a valid JWT token.

## 📋 **Testing Workflow**

### Step 1: Login
1. Run **"🔐 Authentication → Login User"**
2. ✅ Auto-saves JWT token and user ID
3. Check Postman Console for confirmation

### Step 2: Test API Status (FIXED!)
1. Run **"📊 Analytics & Metadata → Metadata API Status"** 
2. ✅ Now working with POST method!

### Step 3: Test Analytics (FIXED!)
1. Run **"📊 Analytics & Metadata → User Analytics - 30 Days"**
2. Run **"📊 Analytics & Metadata → User Analytics - 7 Days"** 
3. ✅ Both endpoints are working now!

### Step 4: Create Content
1. Run **"📝 Journal Entries → Create Entry"**
2. ✅ Auto-saves entry ID for subsequent requests

### Step 5: Test Search & RAG
1. Run **"🔍 Semantic Search → Basic Semantic Search"**
2. Run **"🤖 RAG Search → RAG Conversational Mode"**

## 📊 **Analytics Endpoints - Now Working!**

| Endpoint | Description | Example Response |
|----------|-------------|------------------|
| `GET /api/metadata?days=30` | 30-day analytics | Tag usage, mood trends, insights |
| `GET /api/metadata?days=7` | 7-day analytics | Weekly summary |
| `GET /api/metadata` | Default 30-day | Same as ?days=30 |

### Sample Analytics Response:
```json
{
  "success": true,
  "metadata": {
    "period_days": 30,
    "basic_stats": {
      "total_entries": 3,
      "entries_with_tags": 0,
      "entries_with_category": 0, 
      "entries_with_mood": 0,
      "average_mood": null,
      "entries_with_embeddings": 0,
      "embedding_completion_rate": 0.0
    },
    "popular_tags": [],
    "popular_categories": [],
    "mood_trend": [],
    "insights": {
      "most_active_day": "Saturday",
      "mood_by_day": {},
      "average_text_length": 189,
      "writing_frequency": 0.1,
      "tagging_frequency": 0.0
    },
    "processing_time_ms": 41.09
  }
}
```

## 🤖 **RAG Search Modes**

### Conversational Mode
- **Purpose**: Friendly, therapeutic responses
- **Use for**: "How have I been feeling lately?"

### Summary Mode  
- **Purpose**: Structured overviews with bullet points
- **Use for**: "What are my main themes this month?"

### Analysis Mode
- **Purpose**: Deep pattern recognition and insights
- **Use for**: "What patterns do you see in my motivation?"

## 🔄 **Auto-Token Management**

The collection automatically handles:
- ✅ **JWT Token**: Saved from login response
- ✅ **User ID**: Extracted and saved  
- ✅ **Entry ID**: Saved when creating entries

## 🌐 **Production Testing**

To test against production:
1. **Import**: `LifeKB_Production_Environment.postman_environment.json`
2. **Update Variables**:
   - `userEmail`: Your production email
   - `userPassword`: Your production password
3. **Select Environment**: "LifeKB Production Environment"
4. **Production URL**: `https://life-kb-server.vercel.app`

## 🐛 **Troubleshooting**

### "404 Not Found" on Login
- ❌ **Wrong**: Using `/api/auth/login`
- ✅ **Fix**: Use `/api/auth` with `action: "login"`

### "502 Bad Gateway" on Metadata Status
- ❌ **Wrong**: Using `GET /api/metadata` (requires auth)
- ✅ **Fix**: Use `POST /api/metadata` (no auth required for status)

### "Unknown action" on Embeddings
- ❌ **Wrong**: Missing `"action"` parameter in request body
- ✅ **Fix**: Include `{"action": "generate", "entry_id": "uuid"}` for single embedding
- ✅ **Fix**: Include `{"action": "process", "limit": 10}` for batch processing

### "404 Not Found" on Batch Embeddings
- ❌ **Wrong**: Using `/api/embeddings/batch` endpoint
- ✅ **Fix**: Use `/api/embeddings` with `{"action": "process"}`

### "NO_RESPONSE_FROM_FUNCTION" 
- **Issue**: Missing auth token or invalid format
- **Fix**: Run login first, check token is saved

### Metadata Endpoints Not Working
- **Issue**: Authentication required
- **Fix**: Login first, then test analytics endpoints

### "Token expired"
- **Fix**: Re-run login request to get fresh token

## 📱 **For Swift iOS Development**

After testing in Postman, use this base URL in your iOS app:

```swift
// Local development
static let baseURL = "http://localhost:3000"

// Production  
static let baseURL = "https://life-kb-server.vercel.app"
```

## 🎯 **Testing Checklist**

- [ ] ✅ Login works (returns JWT token)
- [ ] ✅ Metadata API status works (returns API info)
- [ ] ✅ Create entry works (creates journal entry)
- [ ] ✅ Get entries works (lists entries)
- [ ] ✅ Semantic search works (finds relevant entries)
- [ ] ✅ RAG search works (AI responses)
- [ ] ✅ 30-day analytics works (metadata stats)
- [ ] ✅ 7-day analytics works (weekly stats)

Your LifeKB API is fully functional! 🚀 