import httpx
import os
import models
from fastapi import APIRouter, status, Depends, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from database import sessionLocal, engine
from utils import auth
from utils import encrypt_decrypt
from utils.config import settings
from datetime import datetime, UTC, timedelta

models.Base.metadata.create_all(bind=engine)
load_dotenv()

def get_db():
	db = sessionLocal()
	try:
		yield db
	finally:
		db.close()

if settings.development:
	backend_url="http://127.0.0.1:8000"
else:
	backend_url=''

router = APIRouter()

github_client_id = os.getenv("GITHUB_CLIENT_ID")
github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")


@router.get("/github-auth")
async def github_auth():
	return RedirectResponse(f"https://github.com/login/oauth/authorize?client_id={github_client_id}&redirect_uri={backend_url}/callback", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

#github sends temporary code on authorizing my app
#github returns error if user denies to authorize, then redirect user to landing page again
@router.get("/callback")
async def complete_auth(code: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
	if error:
		return RedirectResponse(f"{backend_url}/landing-page")	#if user denies to authorize

	#if they accept to authorize:
	params={
		"client_id": github_client_id,
		"client_secret": github_client_secret,
		"code": code,
	}
	headers={"Accept": "application/json"}

	#get the github access token 
	async with httpx.AsyncClient() as client:
		response = await client.post(url="https://github.com/login/oauth/access_token", params=params, headers=headers)
	data = response.json()

	access_token = data['access_token']	#github access token
	access_token_bytes = access_token.encode('utf-8')	#converting it into bytes inorder to encrypt it
	encrypted_token = encrypt_decrypt.cipher.encrypt(access_token_bytes)	#encrypting the token


	#sending get request to github api endpoint, to get github username and github numeric id
	async with httpx.AsyncClient() as client:
		headers.update({"Authorization": f'Bearer {access_token}'})
		response = await client.get("https://api.github.com/user", headers=headers)
	data = response.json()

	github_username = data['login']
	github_id = data['id']

	#if user had already authorized in the past, we just have to update the stored encrypted token, if we insert again, then we will end up with duplicate rows for the same user
	user = db.query(models.Users).filter(models.Users.github_id == github_id).first()
	if user:
		user.ecrypted_github_access_token = encrypted_token
		db.commit()
	else:		
		db.add(models.Users(github_id=github_id, github_username=github_username, ecrypted_github_access_token=encrypted_token))
		db.flush()

		access_token = auth.create_access_token({"sub": github_id}) #access token issued by fastapi

		refresh_token = auth.create_refresh_token()
		hashed_rf = auth.hash_refresh_token(refresh_token)

		db.add(models.RefreshToken(user_id=github_id, token_hash=hashed_rf, created_at=datetime.now(tz=UTC), expires_at=datetime.now(tz=UTC)+timedelta(days=20), is_revoked=False))

		db.commit()

	redirect_response = RedirectResponse(f"{backend_url}/dashboard") #after authorizing my app (regardless of whether they are returning user or new user) redirect them to dashboard page

	#once authorized we set the cookies
	redirect_response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite='lax')
	redirect_response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite='lax')

	return redirect_response

@router.post("/refresh")
def refresh_access_token(request: Request, db: Session=Depends(get_db)):
	refresh_token = request.cookies.get("refresh_token")
	if refresh_token:
		hashed_rf = auth.hash_refresh_token(refresh_token)
		refresh_token_obj = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == hashed_rf).first()
	else:
		raise HTTPException(detail="login again", status_code=status.HTTP_401_UNAUTHORIZED)
	if refresh_token_obj:
		if not refresh_token_obj.is_revoked and refresh_token_obj.expires_at > datetime.now(tz=UTC):
			github_id = refresh_token_obj.user_id
			new_access_token = auth.create_access_token({"sub": github_id})

			response = Response(status_code=status.HTTP_200_OK, content="success")
			response.set_cookie(key="access_token", value=new_access_token, httponly=True, secure=True, samesite='lax')
			return response
		else:
			raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="please login again")

	else:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user doesnt exist")