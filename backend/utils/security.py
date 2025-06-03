import base64
import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.utils import timezone


def generate_token(length=32):
    """
    Generate a secure random token for various security purposes.
    
    Args:
        length: Length of the token in bytes
    
    Returns:
        str: URL-safe base64 encoded token
    """
    token = secrets.token_bytes(length)
    return base64.urlsafe_b64encode(token).decode('utf-8').rstrip('=')


def hash_password(password, salt=None):
    """
    Hash a password using PBKDF2 with SHA-256.
    
    Args:
        password: Plain text password
        salt: Optional salt (if not provided, a new one will be generated)
    
    Returns:
        tuple: (hash, salt)
    """
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = salt.encode('utf-8')
    
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt, 
        100000
    )
    
    return (base64.b64encode(pwdhash).decode('utf-8'), 
            base64.b64encode(salt).decode('utf-8'))


def verify_password(password, stored_hash, salt):
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to check
        stored_hash: Previously stored password hash
        salt: Salt used for hashing
    
    Returns:
        bool: True if password matches
    """
    salt = base64.b64decode(salt)
    calculated_hash, _ = hash_password(password, salt)
    return calculated_hash == stored_hash


def generate_jwt_token(user_id, expiry_hours=24):
    """
    Generate a JWT token for user authentication.
    
    Args:
        user_id: User ID to encode in the token
        expiry_hours: Token validity in hours
    
    Returns:
        str: JWT token
    """
    expiry = timezone.now() + timedelta(hours=expiry_hours)
    
    payload = {
        'user_id': user_id,
        'exp': expiry,
        'iat': timezone.now(),
    }
    
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm='HS256'
    )
    
    return token


def verify_jwt_token(token):
    """
    Verify a JWT token.
    
    Args:
        token: JWT token to verify
    
    Returns:
        dict|None: Token payload if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        # Token has expired
        return None
    except jwt.InvalidTokenError:
        # Token is invalid
        return None


def is_password_strong(password):
    """
    Check if a password meets strength requirements.
    
    Requirements:
    - At least 8 characters
    - Contains at least one lowercase letter
    - Contains at least one uppercase letter
    - Contains at least one digit
    - Contains at least one special character
    
    Args:
        password: Password to check
    
    Returns:
        bool: True if password meets requirements
    """
    if len(password) < 8:
        return False
    
    # Check for lowercase, uppercase, digit, and special char
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    
    return True


def sanitize_input(input_string):
    """
    Sanitize user input to prevent XSS attacks.
    
    Args:
        input_string: User input string
    
    Returns:
        str: Sanitized string
    """
    # Replace potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', input_string)
    return sanitized