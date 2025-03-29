from cryptography.fernet import Fernet
from app.core.config import settings

# Initialize Fernet cipher with the secret key
cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_data(data: str) -> str:
    """Encrypt a string using Fernet symmetric encryption."""
    try:
        encrypted_data = cipher_suite.encrypt(data.encode())
        return encrypted_data.decode()
    except Exception as e:
        raise ValueError(f"Error encrypting data: {str(e)}")

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    try:
        decrypted_data = cipher_suite.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    except Exception as e:
        raise ValueError(f"Error decrypting data: {str(e)}") 