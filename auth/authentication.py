import hashlib
import os


class AuthManager:
    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple:
        if not salt:
            salt = os.urandom(16).hex()
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return pwd_hash, salt

    @staticmethod
    def verify_password(stored_password_hash: str, salt: str, provided_password: str) -> bool:
        pwd_hash, _ = AuthManager.hash_password(provided_password, salt)
        return pwd_hash == stored_password_hash
