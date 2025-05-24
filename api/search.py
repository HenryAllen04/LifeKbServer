# LifeKB Backend Search API - Vercel Serverless Function
# Purpose: Semantic search operations using OpenAI embeddings

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

# === EMBEDDED JWT HANDLER (from embeddings.py) ===

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

# === OPENAI EMBEDDING FUNCTIONS ===

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
    """Perform semantic search on journal entries"""
    
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
    
    return {
        "success": True,
        "query": query,
        "results": search_results,
        "total_count": len(search_results),
        "similarity_threshold": similarity_threshold
    }

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
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "fallback-secret-key")
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
            "api": "LifeKB Search",
            "version": "1.0.0",
            "status": "active",
            "endpoints": {
                "POST": "Semantic search with query, limit, and similarity_threshold"
            },
            "features": ["semantic_search", "openai_embeddings", "cosine_similarity"],
            "environment": {
                "openai_configured": bool(os.environ.get("OPENAI_API_KEY")),
                "supabase_configured": bool(os.environ.get("SUPABASE_URL"))
            }
        })
    
    def do_POST(self):
        """Handle POST requests - semantic search"""
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
            
            query = data.get('query', '').strip()
            if not query:
                self._send_error_response(400, "Search query is required")
                return
            
            limit = min(int(data.get('limit', 10)), 50)  # Max 50 results
            similarity_threshold = float(data.get('similarity_threshold', 0.1))
            
            if not 0.0 <= similarity_threshold <= 1.0:
                self._send_error_response(400, "Similarity threshold must be between 0.0 and 1.0")
                return
            
            start_time = datetime.now()
            result = perform_semantic_search(user_id, query, limit, similarity_threshold)
            search_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            result["search_time_ms"] = round(search_time_ms, 2)
            
            self._send_json_response(200, serialize_data(result))
            
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON in request body")
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}") 