# LifeKB Backend Auth API
# Purpose: Authentication endpoints for user login, signup, and token management

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
import os
import json
import logging

# Import our app modules
import sys
sys.path.append('/var/task')
from app.models import LoginRequest, UserCreate, AuthTokens, RefreshTokenRequest, APIError
from app.auth import auth_manager
from app.utils import create_error_response, create_success_response, setup_logging, get_client_ip, rate_limiter

# Setup logging
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LifeKB Auth API",
    description="Authentication endpoints for the privacy-first journaling app",
    version="1.0.0"
)

# CORS middleware
cors_origins = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:3000"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    client_ip = get_client_ip(request)
    
    if not rate_limiter.is_allowed(client_ip):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    response = await call_next(request)
    return response


@app.post("/login", response_model=AuthTokens)
async def login(request: LoginRequest):
    """
    Authenticate user and return access tokens
    
    Args:
        request: Login credentials (email and password)
    
    Returns:
        AuthTokens: Access token, refresh token, and metadata
        
    Raises:
        HTTPException: 401 for invalid credentials, 400 for other errors
    """
    try:
        logger.info(f"Login attempt for email: {request.email}")
        
        # Authenticate user
        auth_result = await auth_manager.sign_in(request.email, request.password)
        
        # Extract session info
        session = auth_result["session"]
        
        response = AuthTokens(
            access_token=session["access_token"],
            refresh_token=session["refresh_token"],
            token_type=session["token_type"],
            expires_in=session["expires_in"]
        )
        
        logger.info(f"Successful login for user: {auth_result['user']['id']}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )


@app.post("/signup", response_model=AuthTokens)
async def signup(request: UserCreate):
    """
    Register a new user account
    
    Args:
        request: User registration data (email and password)
    
    Returns:
        AuthTokens: Access token, refresh token, and metadata (if email confirmation not required)
        
    Raises:
        HTTPException: 409 for existing user, 400 for validation errors
    """
    try:
        logger.info(f"Signup attempt for email: {request.email}")
        
        # Create user account
        auth_result = await auth_manager.sign_up(request.email, request.password)
        
        # Check if we have a session (email confirmation might be required)
        if auth_result["session"]:
            session = auth_result["session"]
            
            response = AuthTokens(
                access_token=session["access_token"],
                refresh_token=session["refresh_token"],
                token_type=session["token_type"],
                expires_in=session["expires_in"]
            )
            
            logger.info(f"Successful signup for user: {auth_result['user']['id']}")
            return response
        else:
            # Email confirmation required
            logger.info(f"Signup successful, email confirmation required for: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Account created. Please check your email for confirmation."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration service unavailable"
        )


@app.post("/refresh", response_model=AuthTokens)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    
    Args:
        request: Refresh token request
    
    Returns:
        AuthTokens: New access token, refresh token, and metadata
        
    Raises:
        HTTPException: 401 for invalid refresh token
    """
    try:
        logger.info("Token refresh attempt")
        
        # Refresh tokens
        refresh_result = await auth_manager.refresh_token(request.refresh_token)
        
        response = AuthTokens(
            access_token=refresh_result["access_token"],
            refresh_token=refresh_result["refresh_token"],
            token_type=refresh_result["token_type"],
            expires_in=refresh_result["expires_in"]
        )
        
        logger.info("Token refresh successful")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service unavailable"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "auth",
        "version": "1.0.0"
    }


# Error handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=create_error_response(
            "validation_error",
            "Invalid request data",
            {"errors": exc.errors()}
        )
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return HTTPException(
        status_code=exc.status_code,
        detail=create_error_response(
            "http_error",
            exc.detail,
            {"status_code": exc.status_code}
        )
    )


# Main handler for Vercel
def handler(event, context):
    """Vercel serverless function handler"""
    import uvicorn
    return uvicorn.run(app, host="0.0.0.0", port=8000) 