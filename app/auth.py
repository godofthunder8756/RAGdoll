#!/usr/bin/env python3
"""
Authentication module for RAGdoll Enterprise API
Provides JWT-based authentication with role-based access control
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os
from functools import wraps

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel


# Configuration
SECRET_KEY = os.getenv("RAGDOLL_SECRET_KEY", "ragdoll-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security scheme
security = HTTPBearer()

# User roles
class UserRole:
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    READONLY = "readonly"

# Pydantic models
class TokenData(BaseModel):
    username: Optional[str] = None
    roles: List[str] = []

class User(BaseModel):
    username: str
    email: Optional[str] = None
    roles: List[str] = []
    namespaces: List[str] = []  # Namespaces the user has access to
    is_active: bool = True

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class LoginRequest(BaseModel):
    username: str
    password: str

# Simple in-memory user database (replace with real database in production)
fake_users_db = {
    "admin": {
        "username": "admin",
        "email": "admin@ragdoll.local",
        "hashed_password": pwd_context.hash("admin123"),  # Change in production!
        "roles": [UserRole.ADMIN],
        "namespaces": ["*"],  # Access to all namespaces
        "is_active": True,
    },
    "hr_manager": {
        "username": "hr_manager",
        "email": "hr@company.com",
        "hashed_password": pwd_context.hash("hr123"),
        "roles": [UserRole.MANAGER],
        "namespaces": ["hr", "general"],
        "is_active": True,
    },
    "legal_user": {
        "username": "legal_user",
        "email": "legal@company.com",
        "hashed_password": pwd_context.hash("legal123"),
        "roles": [UserRole.USER],
        "namespaces": ["legal", "general"],
        "is_active": True,
    },
    "readonly": {
        "username": "readonly",
        "email": "readonly@company.com",
        "hashed_password": pwd_context.hash("readonly123"),
        "roles": [UserRole.READONLY],
        "namespaces": ["*"],
        "is_active": True,
    }
}

# Authentication functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database"""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with username and password"""
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    return User(
        username=user.username,
        email=user.email,
        roles=user.roles,
        namespaces=user.namespaces,
        is_active=user.is_active
    )

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Authorization functions
def require_role(required_role: str):
    """Decorator to require specific role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(current_user: User = Depends(get_current_active_user), *args, **kwargs):
            if required_role not in current_user.roles and UserRole.ADMIN not in current_user.roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Operation requires {required_role} role"
                )
            return await func(current_user, *args, **kwargs)
        return wrapper
    return decorator

def require_namespace_access(namespace: str, user: User) -> bool:
    """Check if user has access to namespace"""
    # Admin has access to everything
    if UserRole.ADMIN in user.roles:
        return True
    
    # Check if user has wildcard access
    if "*" in user.namespaces:
        return True
    
    # Check if user has specific namespace access
    if namespace in user.namespaces:
        return True
    
    return False

def check_namespace_access(namespace: str):
    """Dependency to check namespace access"""
    def _check_access(current_user: User = Depends(get_current_active_user)):
        if not require_namespace_access(namespace, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to namespace '{namespace}'"
            )
        return current_user
    return _check_access

# Role-based access control helpers
def can_read(user: User) -> bool:
    """Check if user can read documents"""
    return any(role in user.roles for role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER, UserRole.READONLY])

def can_write(user: User) -> bool:
    """Check if user can ingest documents"""
    return any(role in user.roles for role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER])

def can_manage_namespaces(user: User) -> bool:
    """Check if user can create/delete namespaces"""
    return any(role in user.roles for role in [UserRole.ADMIN, UserRole.MANAGER])

def can_admin(user: User) -> bool:
    """Check if user has admin privileges"""
    return UserRole.ADMIN in user.roles

# Authentication endpoints
def login_for_access_token(form_data: LoginRequest) -> Token:
    """Login endpoint to get access token"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

def get_current_user_profile(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current user profile"""
    return current_user
