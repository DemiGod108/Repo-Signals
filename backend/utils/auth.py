import jwt
from jwt.exceptions import InvalidTokenError
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from utils.config import settings
from database import sessionLocal
from sqlalchemy.orm import Session
from models import Users
from fastapi import Request, Depends, HTTPException, status

def get_db():
	db = sessionLocal()
	try:
		yield db
	finally:
		db.close()


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

def get_current_user(request: Request, db: Session = Depends(get_db)):
	access_token = request.cookies.get("access_token")

	if access_token:
		try:
			payload = jwt.decode(access_token, key=settings.secret_key.get_secret_value(), algorithms=[settings.algorithm])
			github_user_id = payload.get("sub")

			user_obj = db.query(Users).filter(Users.github_id == github_user_id).first()

			if user_obj:
				return user_obj
			else:
				raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
		except InvalidTokenError:
			raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
		
	else:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)