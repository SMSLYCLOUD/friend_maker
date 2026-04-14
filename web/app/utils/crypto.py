import os
import logging
from cryptography.fernet import Fernet
from pathlib import Path

class CryptoManager:
    def __init__(self, key_path: str = "data/secret.key"):
        self.logger = logging.getLogger("CryptoManager")
        self.key_path = Path(key_path)
        self.key = self._load_or_generate_key()
        self.fernet = self._build_fernet(self.key)

    def _build_fernet(self, key: bytes) -> Fernet:
        try:
            return Fernet(key)
        except Exception:
            self.logger.warning("Invalid crypto key provided; generating a new Fernet key.")
            new_key = Fernet.generate_key()
            self._persist_key(new_key)
            self.key = new_key
            return Fernet(new_key)

    def _is_valid_key(self, key: bytes) -> bool:
        try:
            Fernet(key)
            return True
        except Exception:
            return False

    def _is_valid_key(self, key: bytes) -> bool:
        try:
            Fernet(key)
            return True
        except Exception:
            return False

    def _is_valid_key(self, key: bytes) -> bool:
        try:
            Fernet(key)
            return True
        except Exception:
            return False

    def _is_valid_key(self, key: bytes) -> bool:
        try:
            Fernet(key)
            return True
        except Exception:
            return False

    def _load_or_generate_key(self) -> bytes:
        # 1. Environment variable
        env_key = os.getenv("SECRET_KEY", "").strip()
        if env_key:
            key = env_key.encode()
            if self._is_valid_key(key):
                return key
            self.logger.warning("SECRET_KEY is invalid; falling back to file/generated key.")

        # 2. File in data directory (persistent in Docker)
        if self.key_path.exists():
            key = self.key_path.read_bytes()
            if self._is_valid_key(key):
                return key
            self.logger.warning("Persisted key is invalid; generating a new Fernet key.")

        # 3. Generate new
        key = Fernet.generate_key()
        self._persist_key(key)
        return key

    def _persist_key(self, key: bytes):
        try:
            if not self.key_path.parent.exists():
                self.key_path.parent.mkdir(parents=True, exist_ok=True)
            self.key_path.write_bytes(key)
        except Exception:
            # Fallback if filesystem is read-only
            pass

    def encrypt(self, data: str) -> str:
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        try:
            return self.fernet.decrypt(token.encode()).decode()
        except Exception:
            return ""

# Global instance
crypto = CryptoManager()
