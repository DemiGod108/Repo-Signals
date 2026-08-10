from cryptography.fernet import Fernet
from utils.config import settings

#encoding is required, since Fernet objects require key to be in bytes format
key=settings.github_encryption_key.get_secret_value().encode('utf-8') #SecretStr requires you to use .get_secret_value() because it doesnt load string directly
cipher=Fernet(key)