# 🧪 Testing the RAG Feature

This guide shows you how to test the LifeKB RAG (Retrieval-Augmented Generation) feature using multiple methods.

## 🔧 Prerequisites

### 1. Environment Setup
You need these environment variables set:

```bash
# Required for RAG functionality
export OPENAI_API_KEY="sk-your-openai-api-key"
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-supabase-service-key"
export JWT_SECRET_KEY="your-jwt-secret"

# Optional: For automated testing
export TEST_BASE_URL="https://your-lifekb-app.vercel.app"
export TEST_JWT_TOKEN="your-test-user-jwt-token"
```

Or create a `.env` file (copy from `env.example` and fill in values).

### 2. Get a JWT Token
You'll need a valid JWT token for a user with journal entries. You can get this by:
- Logging into your LifeKB app and extracting the token from localStorage
- Creating a test user and getting their token
- Using your existing authentication system

## 🚀 Testing Methods

### Method 1: Automated Test Suite (Recommended)

Run the comprehensive test suite:

```bash
# Option A: Using environment variables
python scripts/test_rag.py

# Option B: Pass parameters directly
python scripts/test_rag.py https://your-app.vercel.app your-jwt-token

# Option C: Test against local development
python scripts/test_rag.py http://localhost:3000 your-jwt-token
```

**What it tests:**
- ✅ Environment validation
- ✅ API endpoint availability
- ✅ All three response modes (conversational, summary, analysis)
- ✅ With and without source attribution
- ✅ Error handling
- ✅ Performance metrics

### Method 2: Interactive HTML Demo

Open the demo in your browser:

```bash
# If you have a local server
open examples/rag-demo.html

# Or serve it locally
python -m http.server 8080
# Then visit: http://localhost:8080/examples/rag-demo.html
```

**Features:**
- 🎯 Real-time RAG testing
- 🎭 Switch between response modes
- 📱 Mobile-friendly interface
- 🎲 Sample query suggestions
- 📊 Performance metrics display

### Method 3: Command Line Testing

#### Quick API Info Check
```bash
curl https://your-app.vercel.app/api/search_rag
```

#### Basic RAG Search
```bash
curl -X POST https://your-app.vercel.app/api/search_rag \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How have I been feeling lately?",
    "mode": "conversational",
    "include_sources": true,
    "limit": 5
  }'
```

#### Test Different Modes
```bash
# Conversational mode
curl -X POST https://your-app.vercel.app/api/search_rag \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "When was I last stressed?", "mode": "conversational"}'

# Summary mode  
curl -X POST https://your-app.vercel.app/api/search_rag \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize my week", "mode": "summary"}'

# Analysis mode
curl -X POST https://your-app.vercel.app/api/search_rag \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What patterns do you see?", "mode": "analysis"}'
```

### Method 4: Local Development Testing

If running the API locally:

```bash
# Start your local server (if needed)
vercel dev

# Test against localhost
export TEST_BASE_URL="http://localhost:3000"
python scripts/test_rag.py
```

## 📋 Sample Test Queries

### Temporal Queries
- "When was the last time I felt anxious?"
- "How has my mood changed over the past month?"
- "What were my main concerns in 2024?"

### Pattern Analysis  
- "What activities make me happiest?"
- "What triggers my stress?"
- "How do I typically handle difficult situations?"

### Insight Generation
- "What lessons have I learned this year?"
- "What are my recurring themes?"
- "How have I grown as a person?"

## 🔍 Expected Results

### Successful Response Format
```json
{
  "success": true,
  "query": "How have I been feeling lately?",
  "ai_response": "Based on your recent entries...",
  "mode": "conversational", 
  "total_sources": 3,
  "sources": [
    {
      "id": "entry-uuid",
      "text": "Journal entry text...",
      "created_at": "2024-03-15T10:30:00Z",
      "similarity": 0.824
    }
  ],
  "processing_time_ms": 2150
}
```

### Performance Benchmarks
- **Response Time**: 2-5 seconds
- **Cost per Query**: $0.01-0.05  
- **Source Entries**: 1-20 (based on limit)
- **Similarity Threshold**: > 0.1

## 🚨 Troubleshooting

### Common Issues

#### "Authentication required" (401)
- ✅ Check JWT token is valid and not expired
- ✅ Ensure token includes proper user_id claim
- ✅ Verify JWT_SECRET_KEY matches your app

#### "OpenAI API error" (500)
- ✅ Verify OPENAI_API_KEY is valid
- ✅ Check OpenAI account has credits
- ✅ Ensure API key has proper permissions

#### "No relevant entries found"
- ✅ Try different keywords or phrases
- ✅ Check user actually has journal entries
- ✅ Verify semantic search is working

#### Slow responses
- ✅ Normal for RAG (2-5s vs 50ms for pure search)
- ✅ Consider reducing limit parameter
- ✅ Check OpenAI API status

### Debug Mode
Add verbose logging to requests:

```bash
# Enable debug output
curl -v -X POST https://your-app.vercel.app/api/search_rag \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "mode": "conversational"}'
```

## 📊 Test Results Interpretation

### Success Metrics
- ✅ All API calls return 200 status
- ✅ AI responses are contextual and relevant
- ✅ Source attribution is accurate
- ✅ Processing times are reasonable (2-5s)
- ✅ Different modes produce different response styles

### Quality Indicators
- 🎯 **Relevance**: AI responses reference specific journal entries
- 🔗 **Attribution**: Source entries match the query context  
- 🎭 **Mode Differences**: Conversational vs Summary vs Analysis feel distinct
- ⚡ **Performance**: Responses arrive within 5 seconds
- 🛡️ **Privacy**: Only relevant entries sent to OpenAI

## 🎯 Next Steps

After successful testing:

1. **Deploy to Production**: Merge the RAG feature branch
2. **User Onboarding**: Add RAG option to your frontend
3. **Monitor Usage**: Track adoption and performance metrics
4. **Gather Feedback**: Get user input on AI response quality
5. **Iterate**: Improve prompts and add new features

## 📝 Need Help?

If you encounter issues:

1. Check the comprehensive logs in `scripts/test_rag.py`
2. Review the API documentation in `docs/rag-api.md`
3. Verify your environment matches `env.example`
4. Test pure semantic search first to isolate issues

Happy testing! 🚀 