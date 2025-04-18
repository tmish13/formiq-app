from cryptography.fernet import Fernet
from typing import Optional
from app.core.config import settings

class Encryptor:
    """Singleton class to handle encryption/decryption operations."""
    _instance: Optional['Encryptor'] = None
    _cipher: Optional[Fernet] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._cipher is None:
            self._init_cipher()

    def _init_cipher(self):
        """Initialize the Fernet cipher with the configured key."""
        try:
            key = settings.ENCRYPTION_KEY.encode()
            self._cipher = Fernet(key)
        except Exception as e:
            raise ValueError(f"Failed to initialize encryption: {str(e)}")

    def encrypt_data(self, data: str) -> str:
        """
        Encrypt a string using Fernet symmetric encryption.
        
        Args:
            data: String to encrypt
            
        Returns:
            str: Encrypted data as a string
            
        Raises:
            ValueError: If encryption fails
        """
        try:
            return self._cipher.encrypt(data.encode()).decode()
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")

    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt a Fernet-encrypted string.
        
        Args:
            encrypted_data: Encrypted string to decrypt
            
        Returns:
            str: Decrypted data as a string
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            return self._cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

# Global encryptor instance
_encryptor = Encryptor()

# Expose encryption functions
def encrypt_data(data: str) -> str:
    """Encrypt data using the global encryptor instance."""
    return _encryptor.encrypt_data(data)

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data using the global encryptor instance."""
    return _encryptor.decrypt_data(encrypted_data) 