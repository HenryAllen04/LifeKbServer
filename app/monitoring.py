# Purpose: Application monitoring, logging, and performance tracking for LifeKB backend
# Provides structured logging, performance metrics, rate limiting, and security monitoring

import time
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from functools import wraps
import asyncio
from collections import defaultdict
import os

# Performance metrics storage (in-memory for now, could be Redis in production)
_metrics_store = defaultdict(list)
_rate_limit_store = defaultdict(list)

class LogLevel:
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Logger:
    """Structured logging for LifeKB API with JSON output for production monitoring"""
    
    def __init__(self, component: str):
        self.component = component
        self.environment = os.getenv("ENVIRONMENT", "development")
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method with structured JSON output"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "component": self.component,
            "message": message,
            "environment": self.environment,
            **kwargs
        }
        
        # In development, pretty print for readability
        if self.environment == "development":
            print(f"[{level}] {self.component}: {message}")
            if kwargs:
                for key, value in kwargs.items():
                    print(f"  {key}: {value}")
        else:
            # In production, output JSON for log aggregation
            print(json.dumps(log_entry))
    
    def debug(self, message: str, **kwargs):
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warn(self, message: str, **kwargs):
        self._log(LogLevel.WARN, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(LogLevel.CRITICAL, message, **kwargs)

class PerformanceMonitor:
    """Performance monitoring for API endpoints with metrics collection"""
    
    def __init__(self):
        self.logger = Logger("performance")
    
    def track_request(self, endpoint: str, method: str, user_id: Optional[str] = None):
        """Decorator for tracking API request performance"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                request_id = str(uuid.uuid4())[:8]
                start_time = time.time()
                
                self.logger.info(
                    f"Request started: {method} {endpoint}",
                    request_id=request_id,
                    endpoint=endpoint,
                    method=method,
                    user_id=user_id
                )
                
                try:
                    result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Store metrics
                    self._store_metric(endpoint, method, duration, "success", user_id)
                    
                    self.logger.info(
                        f"Request completed: {method} {endpoint}",
                        request_id=request_id,
                        duration_ms=round(duration * 1000, 2),
                        status="success"
                    )
                    
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    
                    # Store error metrics
                    self._store_metric(endpoint, method, duration, "error", user_id)
                    
                    self.logger.error(
                        f"Request failed: {method} {endpoint}",
                        request_id=request_id,
                        duration_ms=round(duration * 1000, 2),
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    
                    raise
            
            return wrapper
        return decorator
    
    def _store_metric(self, endpoint: str, method: str, duration: float, status: str, user_id: Optional[str]):
        """Store performance metrics for analysis"""
        metric = {
            "timestamp": datetime.utcnow(),
            "endpoint": endpoint,
            "method": method,
            "duration": duration,
            "status": status,
            "user_id": user_id
        }
        
        key = f"{method}:{endpoint}"
        _metrics_store[key].append(metric)
        
        # Keep only last 1000 metrics per endpoint to prevent memory issues
        if len(_metrics_store[key]) > 1000:
            _metrics_store[key] = _metrics_store[key][-1000:]
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics summary for the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        summary = {}
        
        for endpoint_key, metrics in _metrics_store.items():
            recent_metrics = [m for m in metrics if m["timestamp"] > cutoff_time]
            
            if not recent_metrics:
                continue
            
            durations = [m["duration"] for m in recent_metrics]
            success_count = len([m for m in recent_metrics if m["status"] == "success"])
            error_count = len([m for m in recent_metrics if m["status"] == "error"])
            
            summary[endpoint_key] = {
                "total_requests": len(recent_metrics),
                "success_requests": success_count,
                "error_requests": error_count,
                "success_rate": round(success_count / len(recent_metrics) * 100, 2) if recent_metrics else 0,
                "avg_duration_ms": round(sum(durations) / len(durations) * 1000, 2) if durations else 0,
                "max_duration_ms": round(max(durations) * 1000, 2) if durations else 0,
                "min_duration_ms": round(min(durations) * 1000, 2) if durations else 0
            }
        
        return summary

class RateLimiter:
    """Rate limiting to prevent API abuse and ensure fair usage"""
    
    def __init__(self):
        self.logger = Logger("rate_limiter")
    
    def limit_requests(self, max_requests: int, window_minutes: int, key_func=None):
        """Rate limiting decorator
        
        Args:
            max_requests: Maximum requests allowed in the time window
            window_minutes: Time window in minutes
            key_func: Function to generate rate limit key (default: user_id)
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract user_id or IP for rate limiting key
                if key_func:
                    rate_key = key_func(*args, **kwargs)
                else:
                    # Default: try to extract user_id from request
                    rate_key = kwargs.get("user_id", "anonymous")
                
                now = datetime.utcnow()
                window_start = now - timedelta(minutes=window_minutes)
                
                # Clean old requests
                _rate_limit_store[rate_key] = [
                    req_time for req_time in _rate_limit_store[rate_key] 
                    if req_time > window_start
                ]
                
                current_requests = len(_rate_limit_store[rate_key])
                
                if current_requests >= max_requests:
                    self.logger.warn(
                        f"Rate limit exceeded for {rate_key}",
                        rate_key=rate_key,
                        current_requests=current_requests,
                        max_requests=max_requests,
                        window_minutes=window_minutes
                    )
                    
                    raise Exception(f"Rate limit exceeded. Max {max_requests} requests per {window_minutes} minutes.")
                
                # Add current request
                _rate_limit_store[rate_key].append(now)
                
                self.logger.debug(
                    f"Rate limit check passed for {rate_key}",
                    rate_key=rate_key,
                    current_requests=current_requests + 1,
                    max_requests=max_requests
                )
                
                return func(*args, **kwargs)
            
            return wrapper
        return decorator

class SecurityMonitor:
    """Security monitoring for suspicious activity detection"""
    
    def __init__(self):
        self.logger = Logger("security")
    
    def log_auth_attempt(self, email: str, success: bool, ip_address: str = "unknown"):
        """Log authentication attempts for security monitoring"""
        self.logger.info(
            f"Authentication attempt: {'successful' if success else 'failed'}",
            email=email,
            success=success,
            ip_address=ip_address,
            security_event="auth_attempt"
        )
    
    def log_suspicious_activity(self, event_type: str, details: Dict[str, Any], user_id: str = None):
        """Log suspicious activity for security analysis"""
        self.logger.warn(
            f"Suspicious activity detected: {event_type}",
            event_type=event_type,
            user_id=user_id,
            security_event="suspicious_activity",
            **details
        )
    
    def validate_input_size(self, field_name: str, value: str, max_length: int):
        """Validate input size and log potential attacks"""
        if len(value) > max_length:
            self.logger.warn(
                f"Input size validation failed: {field_name}",
                field_name=field_name,
                input_length=len(value),
                max_length=max_length,
                security_event="input_validation_failed"
            )
            raise ValueError(f"{field_name} exceeds maximum length of {max_length} characters")
    
    def check_content_safety(self, text: str) -> bool:
        """Basic content safety check (can be enhanced with ML models)"""
        # Basic checks for now - could integrate with content moderation APIs
        suspicious_patterns = [
            "<script", "javascript:", "eval(", "document.cookie",
            "DROP TABLE", "DELETE FROM", "INSERT INTO", "UPDATE SET"
        ]
        
        text_lower = text.lower()
        for pattern in suspicious_patterns:
            if pattern.lower() in text_lower:
                self.logger.warn(
                    "Potentially malicious content detected",
                    pattern=pattern,
                    text_length=len(text),
                    security_event="content_safety_check"
                )
                return False
        
        return True

# Global instances for easy import
performance_monitor = PerformanceMonitor()
rate_limiter = RateLimiter()
security_monitor = SecurityMonitor()

def create_logger(component: str) -> Logger:
    """Factory function to create component-specific loggers"""
    return Logger(component) 