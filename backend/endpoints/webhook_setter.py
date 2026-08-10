import httpx
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from models import Users
from schemas import SelectRepo
from utils.auth import get_current_user
from utils.encrypt_decrypt import cipher
from utils.config import backend_ngrok

router = APIRouter()

@router.post("/setup-webhook")
async def setup_webhooks(repo_name: SelectRepo, user: Users = Depends(get_current_user)):
	encrypted_github_token = user.encrypted_github_access_token.encode('utf-8') #in db it will stored in string format, but for .decrypt() to work it needs encrypted content in bytes format hence encoding it
	decrypted_github_token = cipher.decrypt(encrypted_github_token).decode('utf-8') #needs to be in string format for Authorization Bearer to work

	headers = {
		"accept": "application/vnd.github+json",
		"Authorization": f"Bearer {decrypted_github_token}"
	}

	#first make sure whether the current user has the permission to setup webhooks for the entered repo, this is done by retrieving repo details
	async with httpx.AsyncClient() as client:
		repo_details = await client.get(url=f"https://api.github.com/repos/{user.github_username}/{repo_name.repo_name}", headers=headers)
	data = repo_details.json()


	#if repo exists and the current user is the admin, setup the webhook (as per github, only admins can setup webhooks for a repo)
	if repo_details.status_code == httpx.codes.OK and data["permissions"]["admin"]:
		headers={
			"accept": "application/vnd.github+json",
			"Authorization": f"Bearer {decrypted_github_token}"
		}
		data = {
			"name": "web",
			"config": {
				"url": f"{backend_ngrok}/webhook-payload",
				"content_type": "json",
				"insecure_ssl": "0"
			},
			"events": ["push", "pull_request", "fork", "issues"]
		}
		#setting up webhooks
		async with httpx.AsyncClient() as client:
			webhook = await client.post(f"https://api.github.com/repos/{user.github_username}/{repo_name.repo_name}/hooks", headers=headers, json=data)

		#happy path, webhook gets setup 
		if webhook.status_code == httpx.codes.CREATED:
			return JSONResponse(
				content={"detail": "webhook created"},
				status_code=status.HTTP_201_CREATED
			)
		#sad path
		else:
			data = webhook.json()
			print(data["errors"])
			raise HTTPException(status_code=webhook.status_code, detail="failed to create webhook")

	#repo exists but the current user is not the admin (user is not admin, hence forbidden from setting up webhook)
	elif repo_details.status_code == httpx.codes.OK:
		raise HTTPException(detail="repo exists but you are not the admin", status_code=status.HTTP_403_FORBIDDEN)

	#the repo which the user entered doesnt even exist
	elif repo_details.status_code == httpx.codes.NOT_FOUND:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="repositry does not exist")

	#occurs if, the github access token is invalid, or revoked (this happens when user manually revokes the app)
	else:
		raise HTTPException(status_code=repo_details.status_code, detail="failed to fetch repo details")