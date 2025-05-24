# Purpose: Monitoring API endpoint for performance metrics, health checks, and system status
# Provides real-time monitoring data for the LifeKB backend system

import json
import os
from datetime import datetime
from typing import Dict, Any

from app.monitoring import performance_monitor, create_logger, _metrics_store, _rate_limit_store
from app.database import get_supabase_client
from app.auth import get_user_from_token

logger = create_logger("monitoring_api")

def handler(request):
    """Handle monitoring endpoint requests"""
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Content-Type': 'application/json'
    }
    
    if request.method == "OPTIONS":
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        if request.method == "GET":
            return handle_get_monitoring(request, headers)
        else:
            return {
                'statusCode': 405,
                'headers': headers,
                'body': json.dumps({"error": "Method not allowed"})
            }
            
    except Exception as e:
        logger.error("Monitoring endpoint error", error=str(e), error_type=type(e).__name__)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                "error": "Internal server error",
                "message": str(e)
            })
        }

def handle_get_monitoring(request, headers: Dict[str, str]):
    """Handle GET requests for monitoring data"""
    
    # Parse query parameters
    query_params = request.args if hasattr(request, 'args') else {}
    
    # Check if authentication is required (for detailed metrics)
    auth_header = request.headers.get('Authorization', '') if hasattr(request, 'headers') else ''
    
    # Public health check (no auth required)
    if query_params.get('type') == 'health':
        health_data = get_health_check()
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(health_data)
        }
    
    # Basic metrics (no auth required)
    if query_params.get('type') == 'basic':
        basic_metrics = get_basic_metrics()
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(basic_metrics)
        }
    
    # Detailed metrics (authentication required)
    if auth_header:
        try:
            # Verify admin or user token
            user_data = get_user_from_token(auth_header.replace('Bearer ', ''))
            if user_data:
                detailed_metrics = get_detailed_metrics(query_params)
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(detailed_metrics)
                }
        except Exception as e:
            logger.warn("Authentication failed for monitoring access", error=str(e))
    
    # Default: return public monitoring summary
    summary = get_public_monitoring_summary()
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(summary)
    }

def get_health_check() -> Dict[str, Any]:
    """Get basic health check information"""
    logger.info("Health check requested")
    
    try:
        # Test database connection
        supabase = get_supabase_client()
        db_status = test_database_connection(supabase)
        
        health_status = {
            "status": "healthy" if db_status["connected"] else "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "components": {
                "database": db_status,
                "api": {
                    "status": "online",
                    "uptime": "unknown"  # Could track since start
                }
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }

def get_basic_metrics() -> Dict[str, Any]:
    """Get basic performance metrics (public)"""
    logger.info("Basic metrics requested")
    
    try:
        metrics_summary = performance_monitor.get_metrics_summary(hours=1)
        
        # Aggregate basic stats
        total_requests = sum(m.get("total_requests", 0) for m in metrics_summary.values())
        avg_response_time = 0
        success_rate = 0
        
        if metrics_summary:
            avg_response_time = sum(m.get("avg_duration_ms", 0) for m in metrics_summary.values()) / len(metrics_summary)
            total_success = sum(m.get("success_requests", 0) for m in metrics_summary.values())
            success_rate = (total_success / total_requests * 100) if total_requests > 0 else 100
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "period": "last_hour",
            "summary": {
                "total_requests": total_requests,
                "average_response_time_ms": round(avg_response_time, 2),
                "success_rate_percent": round(success_rate, 2),
                "active_endpoints": len(metrics_summary)
            }
        }
        
    except Exception as e:
        logger.error("Failed to get basic metrics", error=str(e))
        return {
            "error": "Failed to retrieve metrics",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

def get_detailed_metrics(query_params: Dict[str, str]) -> Dict[str, Any]:
    """Get detailed performance metrics (requires authentication)"""
    logger.info("Detailed metrics requested", query_params=query_params)
    
    try:
        hours = int(query_params.get('hours', 24))
        
        # Get performance metrics
        metrics_summary = performance_monitor.get_metrics_summary(hours=hours)
        
        # Get rate limiting stats
        rate_limit_stats = get_rate_limit_stats()
        
        # System stats
        system_stats = get_system_stats()
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "period_hours": hours,
            "performance_metrics": metrics_summary,
            "rate_limiting": rate_limit_stats,
            "system": system_stats,
            "endpoint_details": [
                {
                    "endpoint": endpoint,
                    "metrics": metrics
                }
                for endpoint, metrics in metrics_summary.items()
            ]
        }
        
    except Exception as e:
        logger.error("Failed to get detailed metrics", error=str(e))
        return {
            "error": "Failed to retrieve detailed metrics",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

def get_public_monitoring_summary() -> Dict[str, Any]:
    """Get public monitoring summary"""
    return {
        "service": "LifeKB API",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "endpoints": {
            "/api/auth": "Authentication services",
            "/api/entries": "Journal entry operations",
            "/api/search": "Semantic search",
            "/api/embeddings": "Embedding management",
            "/api/monitoring": "System monitoring"
        },
        "documentation": "https://github.com/yourusername/lifekb-api",
        "support": "For monitoring details, authenticate with your API token"
    }

def test_database_connection(supabase) -> Dict[str, Any]:
    """Test database connectivity and basic functionality"""
    try:
        # Simple query to test connection
        result = supabase.table('journal_entries').select('id').limit(1).execute()
        
        return {
            "status": "connected",
            "response_time_ms": "unknown",  # Could measure this
            "last_check": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
            "last_check": datetime.utcnow().isoformat() + "Z"
        }

def get_rate_limit_stats() -> Dict[str, Any]:
    """Get rate limiting statistics"""
    try:
        active_users = len(_rate_limit_store)
        total_tracked_requests = sum(len(requests) for requests in _rate_limit_store.values())
        
        return {
            "active_rate_limited_users": active_users,
            "total_tracked_requests": total_tracked_requests,
            "rate_limit_hits": 0  # Would need to track this separately
        }
        
    except Exception as e:
        logger.error("Failed to get rate limit stats", error=str(e))
        return {"error": "Failed to get rate limit statistics"}

def get_system_stats() -> Dict[str, Any]:
    """Get basic system statistics"""
    try:
        return {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "python_version": "3.9+",
            "memory_usage": "unknown",  # Could add memory tracking
            "active_connections": "unknown",  # Could track DB connections
            "uptime": "unknown"  # Could track since start
        }
        
    except Exception as e:
        logger.error("Failed to get system stats", error=str(e))
        return {"error": "Failed to get system statistics"} 