import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from functools import wraps

from src.config import app_settings

logger = logging.getLogger(__name__)

class DataEncryption:
    """Handles encryption/decryption of sensitive data"""
    
    def __init__(self):
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption key using app settings"""
        try:
            # Use database password as base for encryption key
            password = app_settings.db_config.password.encode()
            salt = b'language_tutor_salt'  # In production, use a secure random salt
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self._fernet = Fernet(key)
            logger.info("Encryption initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not data:
            return data
        try:
            return self._fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt encrypted data"""
        if not encrypted_data:
            return encrypted_data
        try:
            return self._fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

def encrypt_sensitive_data(func):
    """Decorator to encrypt sensitive fields in database operations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Fields that should be encrypted
        sensitive_fields = {'message_text', 'first_name', 'last_name'}
        
        # Encrypt data in kwargs
        for field in sensitive_fields:
            if field in kwargs and kwargs[field]:
                try:
                    kwargs[field] = encryptor.encrypt(str(kwargs[field]))
                except Exception as e:
                    logger.error(f"Failed to encrypt {field}: {e}")
                    raise
        
        return func(*args, **kwargs)
    return wrapper

def decrypt_sensitive_data(func):
    """Decorator to decrypt sensitive fields in database queries"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # Skip if no result
        if not result:
            return result
        
        # Decrypt single dict
        if isinstance(result, dict):
            return _decrypt_dict(result)
        
        # Decrypt list of dicts
        if isinstance(result, list):
            return [_decrypt_dict(item) if isinstance(item, dict) else item for item in result]
        
        return result
    return wrapper

def _decrypt_dict(data: dict) -> dict:
    """Helper to decrypt sensitive fields in a dictionary"""
    sensitive_fields = {'message_text', 'first_name', 'last_name'}
    
    for field in sensitive_fields:
        if field in data and data[field]:
            try:
                data[field] = encryptor.decrypt(str(data[field]))
            except Exception as e:
                logger.error(f"Failed to decrypt {field}: {e}")
                # Return encrypted value if decryption fails
                pass
    
    return data

# Global encryption instance
encryptor = DataEncryption()
