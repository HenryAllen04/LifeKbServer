# LifeKB Backend Embeddings API - Production Serverless Function
# Purpose: OpenAI embedding generation and management with embedded monitoring/security features

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import os
import time
import uuid
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Optional, Any, List
import hashlib
import hmac
import base64
import asyncio

# === EMBEDDED MONITORING SYSTEM ===
_metrics_store = defaultdict(list)
_rate_limit_store = defaultdict(list)

class PerformanceMonitor:
    @staticmethod
    def record_request(endpoint: str, method: str, response_time: float, status_code: int):
        timestamp = datetime.now().isoformat()
        metric = {
            "timestamp": timestamp,
            "endpoint": endpoint,
            "method": method,
            "response_time": response_time,
            "status_code": status_code
        }
        _metrics_store[endpoint].append(metric)
        if len(_metrics_store[endpoint]) > 100:
            _metrics_store[endpoint] = _metrics_store[endpoint][-100:]

class RateLimiter:
    @staticmethod
    def check_rate_limit(client_ip: str, limit: int = 50, window: int = 3600) -> tuple[bool, Dict]:
        now = time.time()
        window_start = now - window
        
        _rate_limit_store[client_ip] = [
            timestamp for timestamp in _rate_limit_store[client_ip] 
            if timestamp > window_start
        ]
        
        current_requests = len(_rate_limit_store[client_ip])
        
        if current_requests >= limit:
            return False, {
                "error": "Rate limit exceeded",
                "limit": limit,
                "window": window,
                "retry_after": int(window_start + window - now)
            }
        
        _rate_limit_store[client_ip].append(now)
        return True, {"requests_remaining": limit - current_requests - 1}

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

# === OPENAI EMBEDDING FUNCTIONS (No external dependencies) ===

import urllib.request
import urllib.error

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
        "model": "text-embedding-3-small"  # Cost effective embedding model
    }
    
    # Convert to bytes
    data = json.dumps(payload).encode('utf-8')
    
    # Create request
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

def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None):
    """Make direct HTTP requests to Supabase REST API (no external deps)"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        raise Exception("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured")
    
    url = f"{supabase_url}/rest/v1/{endpoint}"
    if params:
        query_string = urllib.parse.urlencode(params)
        url += f"?{query_string}"
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    # Prepare request data
    request_data = None
    if data:
        request_data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status not in [200, 201, 204]:
                error_text = response.read().decode('utf-8')
                raise Exception(f"Supabase error: {response.status} - {error_text}")
            
            if response.status == 204:
                return {}
            
            return json.loads(response.read().decode('utf-8'))
            
    except urllib.error.HTTPError as e:
        error_text = e.read().decode('utf-8') if e.fp else str(e)
        raise Exception(f"Supabase error: {e.code} - {error_text}")

def process_pending_embeddings(user_id: str, limit: int = 10):
    """Process pending embeddings for a user"""
    
    # Get pending entries
    params = {
        "user_id": f"eq.{user_id}",
        "embedding_status": "eq.pending",
        "limit": limit
    }
    
    entries = supabase_request("GET", "journal_entries", params=params)
    
    if not entries:
        return {
            "success": True,
            "processed": 0,
            "message": "No pending embeddings found"
        }
    
    processed = 0
    errors = []
    
    for entry in entries:
        try:
            # Generate embedding
            embedding = generate_openai_embedding(entry["text"])
            
            # Update entry with embedding
            update_data = {
                "embedding": embedding,
                "embedding_status": "completed",
                "updated_at": datetime.now().isoformat()
            }
            
            params = {"id": f"eq.{entry['id']}"}
            supabase_request("PATCH", "journal_entries", update_data, params)
            
            processed += 1
            
        except Exception as e:
            errors.append(f"Entry {entry['id']}: {str(e)}")
            
            # Mark as failed
            update_data = {"embedding_status": "failed"}
            params = {"id": f"eq.{entry['id']}"}
            try:
                supabase_request("PATCH", "journal_entries", update_data, params)
            except:
                pass  # Don't fail if we can't update status
    
    return {
        "success": True,
        "processed": processed,
        "total_pending": len(entries),
        "errors": errors
    }

def get_embedding_status(user_id: str):
    """Get embedding status for user's entries"""
    
    # Get counts by status
    params = {"user_id": f"eq.{user_id}"}
    entries = supabase_request("GET", "journal_entries", params=params)
    
    status_counts = {
        "pending": 0,
        "completed": 0,
        "failed": 0,
        "total": len(entries)
    }
    
    for entry in entries:
        status = entry.get("embedding_status", "pending")
        if status in status_counts:
            status_counts[status] += 1
    
    return status_counts

def generate_single_embedding(user_id: str, entry_id: str):
    """Generate embedding for a specific entry"""
    
    # Get the entry
    params = {
        "id": f"eq.{entry_id}",
        "user_id": f"eq.{user_id}"
    }
    
    entries = supabase_request("GET", "journal_entries", params=params)
    
    if not entries:
        raise Exception("Entry not found or access denied")
    
    entry = entries[0]
    
    # Generate embedding
    embedding = generate_openai_embedding(entry["text"])
    
    # Update entry
    update_data = {
        "embedding": embedding,
        "embedding_status": "completed",
        "updated_at": datetime.now().isoformat()
    }
    
    params = {"id": f"eq.{entry_id}"}
    result = supabase_request("PATCH", "journal_entries", update_data, params)
    
    return {
        "success": True,
        "entry_id": entry_id,
        "embedding_dimensions": len(embedding)
    }

def serialize_datetime(obj):
    """Convert datetime objects to ISO format strings for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    return obj

def serialize_data(data):
    """Recursively serialize datetime objects in data."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            try:
                result[key] = serialize_data(value)
            except Exception as e:
                result[key] = str(value)
        return result
    elif isinstance(data, list):
        return [serialize_data(item) for item in data]
    else:
        return serialize_datetime(data)

# === MAIN REQUEST HANDLER ===

class handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.start_time = time.time()
        super().__init__(*args, **kwargs)
    
    def _get_client_ip(self) -> str:
        forwarded_for = self.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return getattr(self.client_address, '0', '127.0.0.1') if self.client_address else '127.0.0.1'
    
    def _log_request(self, status_code: int):
        end_time = time.time()
        response_time = (end_time - self.start_time) * 1000
        PerformanceMonitor.record_request(self.path, self.command, response_time, status_code)
    
    def _send_json_response(self, status_code: int, data: Dict):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
        self._log_request(status_code)
    
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
        # Get JWT secret (no fallback for security)
        jwt_secret = os.environ.get("JWT_SECRET_KEY")
        if not jwt_secret:
            self._send_error_response(500, "Server configuration error")
            return
        
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
        self._log_request(200)
    
    def do_GET(self):
        """Handle GET requests - status and processing"""
        client_ip = self._get_client_ip()
        
        # Rate limiting
        rate_ok, rate_info = RateLimiter.check_rate_limit(client_ip)
        if not rate_ok:
            self._send_error_response(429, rate_info["error"])
            return
        
        # Auth verification
        user_id = self._verify_auth()
        if not user_id:
            self._send_error_response(401, "Authentication required")
            return
        
        # Parse query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        action = query_params.get('action', [None])[0]
        
        try:
            if action == 'status':
                result = get_embedding_status(user_id)
                self._send_json_response(200, {
                    "success": True,
                    "status": serialize_data(result)
                })
            
            elif action == 'process':
                limit = int(query_params.get('limit', [10])[0])
                result = process_pending_embeddings(user_id, limit)
                self._send_json_response(200, serialize_data(result))
            
            else:
                # API info
                self._send_json_response(200, {
                    "api": "LifeKB Embeddings",
                    "version": "1.0.0",
                    "status": "active",
                    "endpoints": {
                        "GET ?action=status": "Get embedding status",
                        "GET ?action=process&limit=N": "Process N pending embeddings",
                        "POST action=generate": "Generate embedding for specific entry"
                    },
                    "features": ["openai_embeddings", "rate_limiting", "monitoring", "zero_external_deps"],
                    "environment": {
                        "openai_configured": bool(os.environ.get("OPENAI_API_KEY")),
                        "supabase_configured": bool(os.environ.get("SUPABASE_URL"))
                    }
                })
            
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests - generate specific embeddings"""
        client_ip = self._get_client_ip()
        
        # Rate limiting
        rate_ok, rate_info = RateLimiter.check_rate_limit(client_ip, limit=30)
        if not rate_ok:
            self._send_error_response(429, rate_info["error"])
            return
        
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
            
            action = data.get('action', '')
            
            if action == 'generate':
                entry_id = data.get('entry_id')
                if not entry_id:
                    self._send_error_response(400, "entry_id required")
                    return
                
                result = generate_single_embedding(user_id, entry_id)
                self._send_json_response(200, serialize_data(result))
            
            elif action == 'process':
                limit = data.get('limit', 10)
                result = process_pending_embeddings(user_id, limit)
                self._send_json_response(200, serialize_data(result))
            
            else:
                self._send_error_response(400, f"Unknown action: {action}")
            
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON in request body")
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}") 