from datetime import datetime, timedelta, timezone
from utils.config import settings
import jwt
import secrets
import hashlib


def hash_refresh_token(refresh_token: str):
	hashed = hashlib.sha256(refresh_token.encode()).hexdigest()
	return hashed


def create_access_token(data: dict, expires_delta: timedelta | None = None):
	to_encode = data.copy()
	if expires_delta:
		expire = datetime.now(timezone.utc) + expires_delta
	else:
		expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

	to_encode.update({"exp": expire})
	encoded_jwt = jwt.encode(to_encode, settings.secret_key.get_secret_value(), algorithm=settings.algorithm)
	return encoded_jwt

def create_refresh_token():
	return secrets.token_urlsafe(32)
