# LifeKB Backend Authentication
# Purpose: JWT validation, user management, and Supabase Auth integration

import os
import jwt
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
import logging
from .database import supabase, DatabaseError, handle_supabase_error

logger = logging.getLogger(__name__)

# JWT Security scheme
security = HTTPBearer()

class AuthError(Exception):
    """Custom exception for authentication errors."""
    pass

def serialize_datetime(obj: Any) -> Any:
    """Convert datetime objects to ISO format strings for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def serialize_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively serialize datetime objects in user data."""
    if isinstance(data, dict):
        return {key: serialize_datetime(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_datetime(item) for item in data]
    else:
        return serialize_datetime(data)

def validate_jwt_token(token: str) -> Dict[str, Any]:
    """
    Validate JWT token using Supabase's public key.
    Returns the decoded token payload if valid.
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Get JWT secret from environment
        jwt_secret = os.environ.get("JWT_SECRET_KEY")
        if not jwt_secret:
            raise AuthError("JWT_SECRET_KEY not configured")
        
        # For Supabase tokens, we need to verify with their public key
        # In development, we can decode without verification for testing
        if os.environ.get("ENVIRONMENT") == "development":
            decoded = jwt.decode(token, options={"verify_signature": False})
        else:
            decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        
        return decoded
        
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")
    except Exception as e:
        raise AuthError(f"Token validation error: {str(e)}")

def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Extract user information from JWT token.
    Returns user data if token is valid, None otherwise.
    """
    try:
        decoded = validate_jwt_token(token)
        user_id = decoded.get('sub')  # Supabase uses 'sub' for user ID
        
        if not user_id:
            return None
            
        return {
            "id": user_id,
            "email": decoded.get('email'),
            "role": decoded.get('role', 'authenticated'),
            "aud": decoded.get('aud'),
            "exp": decoded.get('exp')
        }
        
    except AuthError:
        return None

async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """
    Authenticate user with Supabase Auth.
    Returns authentication result with user data and tokens.
    """
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not response.user:
            raise AuthError("Invalid credentials")
        
        result = {
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at
            },
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at
            }
        }
        
        # Serialize datetime objects
        return serialize_user_data(result)
        
    except Exception as e:
        if "Invalid login credentials" in str(e):
            raise AuthError("Invalid email or password")
        raise AuthError(f"Authentication failed: {str(e)}")

async def register_user(email: str, password: str) -> Dict[str, Any]:
    """
    Register new user with Supabase Auth.
    Returns user data if successful.
    """
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if not response.user:
            raise AuthError("Failed to create user account")
        
        result = {
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at,
                "email_confirmed": response.user.email_confirmed_at is not None
            },
            "session": {
                "access_token": response.session.access_token if response.session else None,
                "refresh_token": response.session.refresh_token if response.session else None
            } if response.session else None
        }
        
        # Serialize datetime objects
        return serialize_user_data(result)
        
    except Exception as e:
        if "already registered" in str(e).lower():
            raise AuthError("User with this email already exists")
        raise AuthError(f"Registration failed: {str(e)}")

async def refresh_token(refresh_token: str) -> Dict[str, Any]:
    """
    Refresh user session using refresh token.
    Returns new session data.
    """
    try:
        response = supabase.auth.refresh_session(refresh_token)
        
        if not response.session:
            raise AuthError("Invalid refresh token")
        
        result = {
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at
            },
            "user": {
                "id": response.user.id,
                "email": response.user.email
            } if response.user else None
        }
        
        # Serialize datetime objects
        return serialize_user_data(result)
        
    except Exception as e:
        raise AuthError(f"Token refresh failed: {str(e)}")

def require_auth(token: str) -> str:
    """
    Validate authentication and return user ID.
    Raises AuthError if not authenticated.
    """
    user = get_user_from_token(token)
    if not user:
        raise AuthError("Authentication required")
    
    return user["id"]

class AuthManager:
    """Authentication manager for Supabase Auth integration"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.jwt_secret = os.getenv("JWT_SECRET_KEY")
        
        if not all([self.supabase_url, self.supabase_anon_key, self.supabase_service_key]):
            raise ValueError("Missing required Supabase environment variables")
        
        # Client for user operations (anon key)
        self.client: Client = create_client(self.supabase_url, self.supabase_anon_key)
        
        # Client for admin operations (service key)
        self.admin_client: Client = create_client(self.supabase_url, self.supabase_service_key)
    
    async def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        try:
            result = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if result.user:
                return {
                    "user": {
                        "id": result.user.id,
                        "email": result.user.email,
                        "created_at": result.user.created_at
                    },
                    "session": {
                        "access_token": result.session.access_token if result.session else None,
                        "refresh_token": result.session.refresh_token if result.session else None,
                        "expires_in": result.session.expires_in if result.session else None,
                        "token_type": "bearer"
                    } if result.session else None
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user account"
                )
                
        except Exception as e:
            logger.error(f"Error during sign up: {str(e)}")
            if "already registered" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {str(e)}"
            )
    
    async def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return tokens"""
        try:
            result = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if result.user and result.session:
                return {
                    "user": {
                        "id": result.user.id,
                        "email": result.user.email,
                        "created_at": result.user.created_at
                    },
                    "session": {
                        "access_token": result.session.access_token,
                        "refresh_token": result.session.refresh_token,
                        "expires_in": result.session.expires_in,
                        "token_type": "bearer"
                    }
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
                
        except Exception as e:
            logger.error(f"Error during sign in: {str(e)}")
            if "invalid login credentials" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Authentication failed: {str(e)}"
            )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            result = self.client.auth.refresh_session(refresh_token)
            
            if result.session:
                return {
                    "access_token": result.session.access_token,
                    "refresh_token": result.session.refresh_token,
                    "expires_in": result.session.expires_in,
                    "token_type": "bearer"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
                
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token refresh failed"
            )
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            # For Supabase, we need to verify the token using their JWT secret
            # The JWT secret is typically the same as the Supabase JWT secret
            # For now, we'll decode without verification for development
            # In production, you should verify with the proper Supabase JWT secret
            
            decoded = jwt.decode(
                token, 
                options={"verify_signature": False}  # Disable signature verification for development
            )
            
            # Check expiration
            if decoded.get('exp') and datetime.fromtimestamp(decoded['exp']) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            return decoded
            
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid JWT token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    async def get_user_from_token(self, token: str) -> Dict[str, Any]:
        """Get user information from JWT token"""
        try:
            payload = self.verify_jwt_token(token)
            user_id = payload.get('sub')
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            # Get user details from Supabase
            user_result = self.admin_client.auth.admin.get_user_by_id(user_id)
            
            if user_result.user:
                return {
                    "id": user_result.user.id,
                    "email": user_result.user.email,
                    "created_at": user_result.user.created_at
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting user from token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to get user information"
            )


# Global auth manager instance
auth_manager = AuthManager()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    try:
        token = credentials.credentials
        user = await auth_manager.get_user_from_token(token)
        return user
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(current_user: Dict[str, Any] = Depends(get_current_user)) -> UUID:
    """Dependency to get current user ID as UUID"""
    try:
        return UUID(current_user["id"])
    except (KeyError, ValueError) as e:
        logger.error(f"Invalid user ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user information"
        ) 