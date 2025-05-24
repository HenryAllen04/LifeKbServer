# LifeKB Backend Metadata API - Vercel Serverless Function
# Purpose: User analytics and statistics (tags, categories, mood trends)

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import urllib.request
import urllib.error
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import hashlib
import hmac
import base64

# === EMBEDDED JWT HANDLER ===

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

# === SUPABASE REQUEST FUNCTION ===

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

# === METADATA ANALYTICS FUNCTIONS ===

def get_user_metadata_stats(user_id: str, days: int = 30) -> Dict[str, Any]:
    """Get comprehensive metadata statistics for a user"""
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get all entries for the user in the date range
    params = {
        "user_id": f"eq.{user_id}",
        "created_at": f"gte.{start_date.isoformat()}",
        "select": "id,text,tags,category,mood,location,weather,created_at,embedding_status"
    }
    
    entries = supabase_request("GET", "journal_entries", params=params)
    
    if not entries:
        return {
            "period_days": days,
            "basic_stats": {
                "total_entries": 0,
                "entries_with_tags": 0,
                "entries_with_category": 0,
                "entries_with_mood": 0,
                "average_mood": None,
                "entries_with_embeddings": 0
            },
            "popular_tags": [],
            "popular_categories": [],
            "mood_trend": [],
            "insights": {},
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    # Calculate statistics
    total_entries = len(entries)
    entries_with_tags = 0
    entries_with_category = 0
    entries_with_mood = 0
    entries_with_embeddings = 0
    mood_values = []
    tag_counts = {}
    category_counts = {}
    mood_trend = []
    
    for entry in entries:
        # Tag analysis
        if entry.get("tags") and len(entry["tags"]) > 0:
            entries_with_tags += 1
            for tag in entry["tags"]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Category analysis
        if entry.get("category"):
            entries_with_category += 1
            category_counts[entry["category"]] = category_counts.get(entry["category"], 0) + 1
        
        # Mood analysis
        if entry.get("mood"):
            entries_with_mood += 1
            mood_values.append(entry["mood"])
            mood_trend.append({
                "date": entry["created_at"][:10],
                "mood": entry["mood"]
            })
        
        # Embedding status
        if entry.get("embedding_status") == "completed":
            entries_with_embeddings += 1
    
    # Calculate average mood
    average_mood = sum(mood_values) / len(mood_values) if mood_values else None
    
    # Sort popular tags and categories
    popular_tags = [
        {"tag": tag, "count": count}
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    ]
    
    popular_categories = [
        {"category": category, "count": count}
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    
    # Calculate insights
    insights = calculate_insights(entries)
    
    return {
        "period_days": days,
        "basic_stats": {
            "total_entries": total_entries,
            "entries_with_tags": entries_with_tags,
            "entries_with_category": entries_with_category,
            "entries_with_mood": entries_with_mood,
            "average_mood": round(average_mood, 2) if average_mood else None,
            "entries_with_embeddings": entries_with_embeddings,
            "embedding_completion_rate": round((entries_with_embeddings / total_entries) * 100, 1) if total_entries > 0 else 0
        },
        "popular_tags": popular_tags,
        "popular_categories": popular_categories,
        "mood_trend": mood_trend,
        "insights": insights,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

def calculate_insights(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate insights from entries"""
    if not entries:
        return {}
    
    # Analyze writing patterns
    day_counts = {}
    mood_by_day = {}
    text_lengths = []
    
    for entry in entries:
        # Day of week analysis
        created_at = datetime.fromisoformat(entry["created_at"].replace("Z", "+00:00"))
        day_name = created_at.strftime("%A")
        day_counts[day_name] = day_counts.get(day_name, 0) + 1
        
        # Mood by day
        if entry.get("mood"):
            if day_name not in mood_by_day:
                mood_by_day[day_name] = []
            mood_by_day[day_name].append(entry["mood"])
        
        # Text length analysis
        if entry.get("text"):
            text_lengths.append(len(entry["text"]))
    
    # Most active day
    most_active_day = max(day_counts, key=day_counts.get) if day_counts else None
    
    # Average mood by day
    mood_averages = {}
    for day, moods in mood_by_day.items():
        mood_averages[day] = round(sum(moods) / len(moods), 2)
    
    # Writing stats
    avg_text_length = round(sum(text_lengths) / len(text_lengths)) if text_lengths else 0
    
    return {
        "most_active_day": most_active_day,
        "mood_by_day": mood_averages,
        "average_text_length": avg_text_length,
        "writing_frequency": round(len(entries) / 30, 2),  # entries per day
        "tagging_frequency": round((sum(1 for e in entries if e.get("tags")) / len(entries)) * 100, 1)
    }

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
        """Handle GET requests - user metadata stats"""
        user_id = self._verify_auth()
        if not user_id:
            self._send_error_response(401, "Authentication required")
            return
        
        try:
            # Parse query parameters
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            days = int(query_params.get('days', [30])[0])
            days = min(max(days, 1), 365)  # Limit between 1 and 365 days
            
            start_time = datetime.now()
            stats = get_user_metadata_stats(user_id, days)
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            stats["processing_time_ms"] = round(processing_time_ms, 2)
            
            self._send_json_response(200, {
                "success": True,
                "metadata": stats
            })
            
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests - API info or specific metadata requests"""
        self._send_json_response(200, {
            "api": "LifeKB Metadata",
            "version": "1.0.0",
            "status": "active",
            "endpoints": {
                "GET": "User metadata statistics with ?days=N parameter"
            },
            "features": [
                "user_analytics",
                "tag_statistics", 
                "mood_trends",
                "category_analysis",
                "writing_insights"
            ]
        }) 