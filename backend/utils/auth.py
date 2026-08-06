from datetime import datetime, timedelta, timezone
from utils.config import settings
import jwt
from pwdlib import PasswordHash
import secrets

refresh_token_hash = PasswordHash.recommended()
def hash_refresh_token(refresh_token: str):
	return refresh_token_hash.hash(refresh_token)

def verify_refresh_token(plain_refresh_token, hashed_refresh_token):
	return refresh_token_hash.verify(plain_refresh_token, hashed_refresh_token)


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
