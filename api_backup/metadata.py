# LifeKB Backend Metadata API - Vercel Serverless Function
# Purpose: User metadata analytics and statistics (tags, categories, mood trends)

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Supabase imports
from supabase import create_client, Client

# Import monitoring and security
from app.monitoring import performance_monitor, rate_limiter, create_logger

logger = create_logger("metadata_api")

def get_supabase_client():
    """Initialize and return Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
    
    return create_client(url, key)

class AuthError(Exception):
    """Custom exception for authentication errors."""
    pass

def get_user_from_token(token: str):
    """Get user data from JWT token."""
    try:
        supabase = get_supabase_client()
        response = supabase.auth.get_user(token)
        
        if not response.user:
            raise AuthError("Invalid token")
        
        return response.user
    except Exception as e:
        raise AuthError(f"Authentication failed: {str(e)}")

@rate_limiter.limit_requests(max_requests=50, window_minutes=1)
@performance_monitor.track_request("/api/metadata", "GET")
async def get_user_metadata_stats(user_id: str, days: int = 30) -> Dict[str, Any]:
    """Get comprehensive metadata statistics for a user."""
    try:
        supabase = get_supabase_client()
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get basic stats from embedding_stats view
        stats_response = supabase.table("embedding_stats")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        basic_stats = stats_response.data[0] if stats_response.data else {
            "total_entries": 0,
            "entries_with_tags": 0,
            "entries_with_category": 0,
            "entries_with_mood": 0,
            "average_mood": None
        }
        
        # Get popular tags
        tags_response = supabase.table("user_tags_stats")\
            .select("tag, tag_usage_count")\
            .eq("user_id", user_id)\
            .order("tag_usage_count", desc=True)\
            .limit(20)\
            .execute()
        
        popular_tags = [
            {"tag": row["tag"], "count": row["tag_usage_count"]}
            for row in tags_response.data
        ] if tags_response.data else []
        
        # Get popular categories
        categories_response = supabase.table("user_categories_stats")\
            .select("category, category_usage_count")\
            .eq("user_id", user_id)\
            .order("category_usage_count", desc=True)\
            .execute()
        
        popular_categories = [
            {"category": row["category"], "count": row["category_usage_count"]}
            for row in categories_response.data
        ] if categories_response.data else []
        
        # Get mood trend over time (last 30 days)
        mood_trend_response = supabase.table("journal_entries")\
            .select("mood, created_at")\
            .eq("user_id", user_id)\
            .not_.is_("mood", "null")\
            .gte("created_at", start_date.isoformat())\
            .order("created_at", desc=False)\
            .execute()
        
        mood_trend = []
        if mood_trend_response.data:
            for entry in mood_trend_response.data:
                mood_trend.append({
                    "date": entry["created_at"][:10],  # Extract date part
                    "mood": entry["mood"]
                })
        
        # Get recent entries with metadata for insights
        recent_entries_response = supabase.table("journal_entries")\
            .select("tags, category, mood, location, weather, created_at")\
            .eq("user_id", user_id)\
            .gte("created_at", start_date.isoformat())\
            .order("created_at", desc=True)\
            .limit(50)\
            .execute()
        
        # Calculate insights
        insights = calculate_metadata_insights(recent_entries_response.data if recent_entries_response.data else [])
        
        result = {
            "period_days": days,
            "basic_stats": basic_stats,
            "popular_tags": popular_tags,
            "popular_categories": popular_categories,
            "mood_trend": mood_trend,
            "insights": insights,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        logger.info("Metadata stats generated successfully", 
                   user_id=user_id, period_days=days, 
                   total_tags=len(popular_tags), total_categories=len(popular_categories))
        
        return result
        
    except Exception as e:
        logger.error("Failed to get metadata stats", user_id=user_id, error=str(e))
        raise Exception(f"Database error: {str(e)}")

def calculate_metadata_insights(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate insights from recent entries."""
    if not entries:
        return {
            "most_active_day": None,
            "mood_patterns": {},
            "location_patterns": [],
            "weather_patterns": [],
            "tagging_frequency": 0
        }
    
    # Analyze patterns
    day_counts = {}
    mood_by_day = {}
    locations = {}
    weather_patterns = {}
    tagged_entries = 0
    
    for entry in entries:
        # Extract day of week
        created_at = datetime.fromisoformat(entry["created_at"].replace("Z", "+00:00"))
        day_name = created_at.strftime("%A")
        day_counts[day_name] = day_counts.get(day_name, 0) + 1
        
        # Mood patterns by day
        if entry.get("mood"):
            if day_name not in mood_by_day:
                mood_by_day[day_name] = []
            mood_by_day[day_name].append(entry["mood"])
        
        # Location patterns
        if entry.get("location"):
            locations[entry["location"]] = locations.get(entry["location"], 0) + 1
        
        # Weather patterns
        if entry.get("weather"):
            weather_patterns[entry["weather"]] = weather_patterns.get(entry["weather"], 0) + 1
        
        # Tag usage
        if entry.get("tags") and len(entry["tags"]) > 0:
            tagged_entries += 1
    
    # Find most active day
    most_active_day = max(day_counts, key=day_counts.get) if day_counts else None
    
    # Calculate average mood by day
    mood_averages = {}
    for day, moods in mood_by_day.items():
        mood_averages[day] = sum(moods) / len(moods)
    
    # Top locations and weather
    top_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]
    top_weather = sorted(weather_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "most_active_day": most_active_day,
        "mood_patterns": mood_averages,
        "location_patterns": [{"location": loc, "count": count} for loc, count in top_locations],
        "weather_patterns": [{"weather": weather, "count": count} for weather, count in top_weather],
        "tagging_frequency": (tagged_entries / len(entries)) * 100 if entries else 0
    }

@rate_limiter.limit_requests(max_requests=30, window_minutes=1)
@performance_monitor.track_request("/api/metadata", "POST")
async def suggest_tags(user_id: str, text: str) -> List[str]:
    """Suggest tags based on entry text and user's previous tags."""
    try:
        supabase = get_supabase_client()
        
        # Get user's existing tags
        tags_response = supabase.table("user_tags_stats")\
            .select("tag, tag_usage_count")\
            .eq("user_id", user_id)\
            .order("tag_usage_count", desc=True)\
            .limit(50)\
            .execute()
        
        existing_tags = [row["tag"].lower() for row in tags_response.data] if tags_response.data else []
        
        # Simple keyword-based suggestions
        text_lower = text.lower()
        suggested_tags = []
        
        # Check for common patterns
        tag_patterns = {
            "work": ["work", "job", "meeting", "project", "deadline", "office", "colleague"],
            "travel": ["travel", "trip", "vacation", "airport", "hotel", "sightseeing"],
            "health": ["exercise", "workout", "gym", "run", "doctor", "medicine", "healthy"],
            "food": ["food", "restaurant", "cooking", "recipe", "dinner", "lunch"],
            "family": ["family", "mom", "dad", "brother", "sister", "kids", "children"],
            "friends": ["friends", "friend", "hangout", "party", "social"],
            "love": ["love", "relationship", "date", "partner", "romantic"],
            "gratitude": ["grateful", "thankful", "blessed", "appreciate", "grateful"],
            "learning": ["learn", "study", "book", "course", "education", "knowledge"],
            "creativity": ["creative", "art", "music", "writing", "painting", "design"]
        }
        
        for tag, keywords in tag_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                suggested_tags.append(tag)
        
        # Include frequently used existing tags that might be relevant
        for existing_tag in existing_tags[:10]:  # Top 10 most used tags
            if existing_tag in text_lower:
                suggested_tags.append(existing_tag)
        
        # Remove duplicates and limit to 5 suggestions
        unique_suggestions = list(set(suggested_tags))[:5]
        
        logger.info("Tag suggestions generated", 
                   user_id=user_id, suggestions_count=len(unique_suggestions))
        
        return unique_suggestions
        
    except Exception as e:
        logger.error("Failed to suggest tags", user_id=user_id, error=str(e))
        raise Exception(f"Database error: {str(e)}")

class handler(BaseHTTPRequestHandler):
    def send_json_response(self, status_code: int, data: dict):
        """Helper to send JSON responses with proper headers."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def get_request_body(self) -> dict:
        """Parse JSON request body."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return {}
            
            post_data = self.rfile.read(content_length)
            return json.loads(post_data.decode('utf-8'))
        except (json.JSONDecodeError, ValueError):
            logger.warn("Failed to parse request body")
            return {}

    def get_user_id(self) -> str:
        """Extract and validate user ID from JWT token."""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise AuthError('Missing or invalid Authorization header')
        
        token = auth_header.replace('Bearer ', '')
        user = get_user_from_token(token)
        
        return str(user.id)

    def do_GET(self):
        """Handle GET requests - metadata statistics and analytics."""
        try:
            user_id = self.get_user_id()
            
            import urllib.parse
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # Get time period (default 30 days)
            days = int(query_params.get('days', [30])[0])
            if days > 365:  # Limit to 1 year
                days = 365
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            stats = loop.run_until_complete(get_user_metadata_stats(user_id, days))
            loop.close()
            
            self.send_json_response(200, {
                'success': True,
                'stats': stats
            })
            
        except AuthError as e:
            self.send_json_response(401, {'error': str(e)})
        except Exception as e:
            logger.error("GET request failed", error=str(e))
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_POST(self):
        """Handle POST requests - tag suggestions."""
        try:
            user_id = self.get_user_id()
            body = self.get_request_body()
            
            text = body.get('text', '').strip()
            if not text:
                self.send_json_response(400, {'error': 'Text is required for tag suggestions'})
                return
            
            if len(text) > 1000:  # Limit text length for suggestions
                self.send_json_response(400, {'error': 'Text too long for tag suggestions (max 1000 characters)'})
                return
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            suggestions = loop.run_until_complete(suggest_tags(user_id, text))
            loop.close()
            
            self.send_json_response(200, {
                'success': True,
                'suggested_tags': suggestions
            })
            
        except AuthError as e:
            self.send_json_response(401, {'error': str(e)})
        except Exception as e:
            logger.error("POST request failed", error=str(e))
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers() 