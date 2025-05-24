# LifeKB Backend Entries API - Production Serverless Function
# Purpose: Complete journal entry CRUD operations with embedded monitoring/security features

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import urllib.request
import urllib.error
import os
import time
import uuid
from datetime import datetime
from collections import defaultdict
from typing import Dict, Optional, Any, List
import hashlib
import hmac
import base64

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

def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None):
    """Make direct HTTP requests to Supabase REST API"""
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

class handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.start_time = time.time()
        super().__init__(*args, **kwargs)
    
    def _send_json_response(self, status_code: int, data: Dict):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
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
            self._send_error_response(500, "Server configuration error")
            return None
        
        valid, payload, _ = JWTHandler.decode_jwt(token, jwt_secret)
        
        if not valid:
            return None
        
        return payload.get("user_id")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests - list entries or get specific entry"""
        user_id = self._verify_auth()
        if not user_id:
            self._send_error_response(401, "Authentication required")
            return
        
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            entry_id = query_params.get('id', [None])[0]
            
            if entry_id:
                # Get specific entry
                params = {
                    "id": f"eq.{entry_id}",
                    "user_id": f"eq.{user_id}"
                }
                entries = supabase_request("GET", "journal_entries", params=params)
                
                if not entries:
                    self._send_error_response(404, "Entry not found")
                    return
                
                self._send_json_response(200, {
                    "success": True,
                    "entry": entries[0]
                })
            else:
                # List all entries
                params = {"user_id": f"eq.{user_id}"}
                entries = supabase_request("GET", "journal_entries", params=params)
                
                self._send_json_response(200, {
                    "success": True,
                    "entries": entries or [],
                    "total": len(entries) if entries else 0
                })
                
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests - create new entry"""
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
            
            text = data.get('text', '').strip()
            if not text:
                self._send_error_response(400, "Text is required")
                return
            
            # Create entry
            entry_id = str(uuid.uuid4())
            entry_data = {
                "id": entry_id,
                "user_id": user_id,
                "text": text,
                "tags": data.get('tags', []),
                "category": data.get('category'),
                "mood": data.get('mood'),
                "location": data.get('location'),
                "weather": data.get('weather'),
                "embedding_status": "pending",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = supabase_request("POST", "journal_entries", entry_data)
            
            self._send_json_response(201, {
                "success": True,
                "message": "Journal entry created successfully",
                "entry": result[0] if isinstance(result, list) else result
            })
            
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON in request body")
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def do_PUT(self):
        """Handle PUT requests - update entry"""
        user_id = self._verify_auth()
        if not user_id:
            self._send_error_response(401, "Authentication required")
            return
        
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        entry_id = query_params.get('id', [None])[0]
        
        if not entry_id:
            self._send_error_response(400, "Entry ID is required")
            return
        
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                request_body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(request_body)
            else:
                data = {}
            
            # Build update data
            update_data = {"updated_at": datetime.now().isoformat()}
            
            if 'text' in data:
                update_data["text"] = data['text']
                update_data["embedding_status"] = "pending"
            if 'tags' in data:
                update_data["tags"] = data['tags']
            if 'category' in data:
                update_data["category"] = data['category']
            if 'mood' in data:
                update_data["mood"] = data['mood']
            if 'location' in data:
                update_data["location"] = data['location']
            if 'weather' in data:
                update_data["weather"] = data['weather']
            
            params = {
                "id": f"eq.{entry_id}",
                "user_id": f"eq.{user_id}"
            }
            
            result = supabase_request("PATCH", "journal_entries", update_data, params)
            
            if not result:
                self._send_error_response(404, "Entry not found")
                return
            
            self._send_json_response(200, {
                "success": True,
                "message": "Journal entry updated successfully",
                "entry": result[0] if isinstance(result, list) else result
            })
            
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON in request body")
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def do_DELETE(self):
        """Handle DELETE requests - delete entry"""
        user_id = self._verify_auth()
        if not user_id:
            self._send_error_response(401, "Authentication required")
            return
        
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        entry_id = query_params.get('id', [None])[0]
        
        if not entry_id:
            self._send_error_response(400, "Entry ID is required")
            return
        
        try:
            params = {
                "id": f"eq.{entry_id}",
                "user_id": f"eq.{user_id}"
            }
            
            # Check if entry exists
            entries = supabase_request("GET", "journal_entries", params=params)
            if not entries:
                self._send_error_response(404, "Entry not found")
                return
            
            # Delete the entry
            supabase_request("DELETE", "journal_entries", params=params)
            
            self._send_json_response(200, {
                "success": True,
                "message": "Journal entry deleted successfully",
                "deleted_entry_id": entry_id
            })
            
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}") 