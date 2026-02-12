import os
from cryptography.fernet import Fernet
from pathlib import Path

class CryptoManager:
    def __init__(self):
        self.key = self._load_key()
        self.fernet = Fernet(self.key)

    def _load_key(self) -> bytes:
        # 1. Environment variable
        if "SECRET_KEY" in os.environ:
            return os.environ["SECRET_KEY"].encode()

        # 2. File in data directory (persistent in Docker)
        key_path = Path("data/secret.key")

        if key_path.exists():
            return key_path.read_bytes()

        # 3. Generate new
        key = Fernet.generate_key()

        try:
            if not key_path.parent.exists():
                key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_bytes(key)
        except Exception:
            # Fallback if filesystem is read-only
            pass

        return key

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
