# LifeKB Backend RAG Search API - Vercel Serverless Function
# Purpose: Retrieval-Augmented Generation (RAG) search with AI-powered insights

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import os
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Optional, Any, List
import hashlib
import hmac
import base64

# === EMBEDDED JWT HANDLER (from search.py) ===

class JWTHandler:
    @staticmethod
    def decode_jwt(token: str, secret: str) -> tuple[bool, Optional[Dict], Optional[str]]:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False, None, "Invalid token format"
            
            header_encoded, payload_encoded, signature_encoded = parts
            
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            
            signature_padded = signature_encoded + '=' * (4 - len(signature_encoded) % 4)
            received_signature = base64.urlsafe_b64decode(signature_padded)
            
            if not hmac.compare_digest(expected_signature, received_signature):
                return False, None, "Invalid signature"
            
            payload_padded = payload_encoded + '=' * (4 - len(payload_encoded) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_padded).decode())
            
            if "exp" in payload and payload["exp"] < time.time():
                return False, None, "Token expired"
            
            return True, payload, None
            
        except Exception as e:
            return False, None, f"Token decode error: {str(e)}"

# === OPENAI FUNCTIONS ===

def generate_openai_embedding(text: str) -> List[float]:
    """Generate embedding using OpenAI API with urllib (no external deps)"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OPENAI_API_KEY not configured")
    
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "input": text,
        "model": "text-embedding-3-small"
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                error_text = response.read().decode('utf-8')
                raise Exception(f"OpenAI API error: {response.status} - {error_text}")
            
            result = json.loads(response.read().decode('utf-8'))
            return result["data"][0]["embedding"]
            
    except urllib.error.HTTPError as e:
        error_text = e.read().decode('utf-8') if e.fp else str(e)
        raise Exception(f"OpenAI API error: {e.code} - {error_text}")

def call_openai_chat(query: str, context: str, mode: str = "conversational") -> str:
    """Call OpenAI Chat Completion API for RAG responses"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OPENAI_API_KEY not configured")
    
    # Prepare system prompts based on mode
    system_prompts = {
        "conversational": """You are a helpful AI assistant analyzing personal journal entries. 
        Your task is to provide thoughtful, empathetic responses based on the provided journal context.
        Be supportive, insightful, and maintain privacy. Always reference specific entries when relevant.
        Keep responses concise and actionable.""",
        
        "summary": """You are an AI assistant specializing in summarizing personal journal entries.
        Provide clear, organized summaries that capture key themes, emotions, and patterns.
        Be objective yet empathetic. Highlight important insights and growth moments.""",
        
        "analysis": """You are an AI assistant providing analytical insights from personal journal entries.
        Focus on patterns, trends, emotional states, and behavioral observations.
        Provide constructive analysis while maintaining empathy and support."""
    }
    
    system_prompt = system_prompts.get(mode, system_prompts["conversational"])
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o-mini",  # Cost-effective model for most use cases
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": f"Based on these journal entries:\n\n{context}\n\nUser question: {query}"
            }
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                error_text = response.read().decode('utf-8')
                raise Exception(f"OpenAI Chat API error: {response.status} - {error_text}")
            
            result = json.loads(response.read().decode('utf-8'))
            return result["choices"][0]["message"]["content"]
            
    except urllib.error.HTTPError as e:
        error_text = e.read().decode('utf-8') if e.fp else str(e)
        raise Exception(f"OpenAI Chat API error: {e.code} - {error_text}")

# === SUPABASE FUNCTIONS ===

def supabase_rpc(function_name: str, params: Dict):
    """Call Supabase RPC function"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        raise Exception("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured")
    
    url = f"{supabase_url}/rest/v1/rpc/{function_name}"
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    data = json.dumps(params).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status not in [200, 201]:
                error_text = response.read().decode('utf-8')
                raise Exception(f"Supabase RPC error: {response.status} - {error_text}")
            
            result = json.loads(response.read().decode('utf-8'))
            return result
            
    except urllib.error.HTTPError as e:
        error_text = e.read().decode('utf-8') if e.fp else str(e)
        raise Exception(f"Supabase RPC error: {e.code} - {error_text}")

def perform_semantic_search(user_id: str, query: str, limit: int = 10, similarity_threshold: float = 0.1):
    """Perform semantic search on journal entries (reused from search.py)"""
    
    # Generate embedding for the search query
    query_embedding = generate_openai_embedding(query)
    
    # Call the database search function
    params = {
        "query_embedding": query_embedding,
        "target_user_id": user_id,
        "similarity_threshold": similarity_threshold,
        "limit_count": limit
    }
    
    results = supabase_rpc("search_entries", params)
    
    # Format results
    search_results = []
    for row in results:
        search_results.append({
            "id": row["id"],
            "text": row["text"],
            "created_at": row["created_at"],
            "similarity": float(row["similarity"])
        })
    
    return search_results

# === RAG CORE FUNCTIONS ===

def format_entries_for_llm(search_results: List[Dict]) -> str:
    """Format search results into context for LLM"""
    if not search_results:
        return "No relevant journal entries found."
    
    formatted_entries = []
    for entry in search_results:
        # Format date for readability
        created_at = entry["created_at"]
        if isinstance(created_at, str):
            try:
                date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%B %d, %Y at %I:%M %p")
            except:
                formatted_date = created_at
        else:
            formatted_date = str(created_at)
        
        similarity_score = f"(relevance: {entry['similarity']:.3f})"
        
        formatted_entry = f"Entry from {formatted_date} {similarity_score}:\n{entry['text']}"
        formatted_entries.append(formatted_entry)
    
    return "\n\n---\n\n".join(formatted_entries)

def perform_rag_search(user_id: str, query: str, mode: str = "conversational", include_sources: bool = True, limit: int = 10):
    """Perform RAG search with AI-generated insights"""
    
    # Step 1: Perform semantic search to get relevant entries
    search_results = perform_semantic_search(user_id, query, limit)
    
    if not search_results:
        return {
            "success": True,
            "query": query,
            "ai_response": "I couldn't find any relevant journal entries for your query. Try using different keywords or phrases.",
            "sources": [],
            "mode": mode,
            "total_sources": 0
        }
    
    # Step 2: Format entries for LLM context
    context = format_entries_for_llm(search_results)
    
    # Step 3: Get AI response
    ai_response = call_openai_chat(query, context, mode)
    
    # Step 4: Format response
    result = {
        "success": True,
        "query": query,
        "ai_response": ai_response,
        "mode": mode,
        "total_sources": len(search_results)
    }
    
    # Include sources if requested
    if include_sources:
        result["sources"] = search_results
    
    return result

def serialize_data(data):
    """Recursively serialize datetime objects in data."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            try:
                result[key] = serialize_data(value)
            except Exception:
                result[key] = str(value)
        return result
    elif isinstance(data, list):
        return [serialize_data(item) for item in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data

# === MAIN REQUEST HANDLER ===

class handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.start_time = time.time()
        super().__init__(*args, **kwargs)
    
    def _send_json_response(self, status_code: int, data: Dict):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _send_error_response(self, status_code: int, error_message: str):
        self._send_json_response(status_code, {
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        })
    
    def _verify_auth(self) -> Optional[str]:
        """Verify JWT token and return user_id"""
        auth_header = self.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header[7:]
        jwt_secret = os.environ.get("JWT_SECRET_KEY")
        if not jwt_secret:
            return None
        
        valid, payload, _ = JWTHandler.decode_jwt(token, jwt_secret)
        
        if not valid:
            return None
        
        return payload.get("user_id")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests - API info"""
        self._send_json_response(200, {
            "api": "LifeKB RAG Search",
            "version": "1.0.0",
            "status": "active",
            "description": "Retrieval-Augmented Generation search with AI-powered insights",
            "endpoints": {
                "POST": "RAG search with query, mode, include_sources, and limit"
            },
            "features": [
                "semantic_search", 
                "ai_insights", 
                "multiple_modes",
                "privacy_aware"
            ],
            "modes": ["conversational", "summary", "analysis"],
            "environment": {
                "openai_configured": bool(os.environ.get("OPENAI_API_KEY")),
                "supabase_configured": bool(os.environ.get("SUPABASE_URL"))
            },
            "privacy_notice": "This endpoint sends relevant journal entries to OpenAI for AI analysis. Only relevant entries matching your search are sent, never your entire journal."
        })
    
    def do_POST(self):
        """Handle POST requests - RAG search"""
        # Auth verification
        user_id = self._verify_auth()
        if not user_id:
            self._send_error_response(401, "Authentication required")
            return
        
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                request_body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(request_body)
            else:
                data = {}
            
            # Validate required parameters
            query = data.get('query', '').strip()
            if not query:
                self._send_error_response(400, "Search query is required")
                return
            
            # Optional parameters with defaults
            mode = data.get('mode', 'conversational')
            if mode not in ['conversational', 'summary', 'analysis']:
                self._send_error_response(400, "Mode must be one of: conversational, summary, analysis")
                return
            
            include_sources = data.get('include_sources', True)
            limit = min(int(data.get('limit', 10)), 20)  # Max 20 results for RAG
            
            # Performance tracking
            start_time = datetime.now()
            
            # Perform RAG search
            result = perform_rag_search(user_id, query, mode, include_sources, limit)
            
            # Add timing information
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            result["processing_time_ms"] = round(processing_time_ms, 2)
            
            self._send_json_response(200, serialize_data(result))
            
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON in request body")
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}") 