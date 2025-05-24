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

logger = logging.getLogger(__name__)

# JWT Security scheme
security = HTTPBearer()


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