import httpx
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from models import Users
from schemas import SelectRepo
from utils.auth import get_current_user
from utils.encrypt_decrypt import cipher
from utils.config import backend_ngrok
from database import sessionLocal
from models import TrackedRepo

def get_db():
	db = sessionLocal()
	try:
		yield db
	finally:
		db.close()

router = APIRouter()

@router.post("/setup-webhook")
async def setup_webhooks(repo_name: SelectRepo, user: Users = Depends(get_current_user), db: TrackedRepo = Depends(get_db)):
	encrypted_github_token = user.encrypted_github_access_token.encode('utf-8') #in db it will stored in string format, but for .decrypt() to work it needs encrypted content in bytes format hence encoding it
	decrypted_github_token = cipher.decrypt(encrypted_github_token).decode('utf-8') #needs to be in string format for Authorization Bearer to work

	headers = {
		"accept": "application/vnd.github+json",
		"Authorization": f"Bearer {decrypted_github_token}"
	}

	#we need to retrieve repo details in order to decide whether this current user can setup webhook for the specified repo or not
	async with httpx.AsyncClient() as client:
		repo_details = await client.get(url=f"https://api.github.com/repos/{user.github_username}/{repo_name.repo_name}", headers=headers)
	resp = repo_details.json()

	repository_id = resp["id"]
	repository_name = resp["name"]
	tracked_repo_obj = db.query(TrackedRepo).filter(TrackedRepo.user_id == user.github_id, TrackedRepo.repo_id == repository_id).first()

	#this handles the case when the admin (i.e the repo maintainer) who setup webhook is trying to setup webhook for the same repo again (same maintainer trying to setup webhook for the same repo, hence repo_id, github_userid pair isnt unique)
	if tracked_repo_obj:
		raise HTTPException(detail="repository is already added")

	else:
		#if repo exists and the current user is the admin, setup the webhook (as per github, only admins can setup webhooks for a repo)
		if repo_details.status_code == httpx.codes.OK and resp["permissions"]["admin"]:
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
				"events": ["push", "pull_request", "pull_request_review", "fork", "issues", "issue_comment"]
			}
			#setting up webhooks
			async with httpx.AsyncClient() as client:
				webhook = await client.post(f"https://api.github.com/repos/{user.github_username}/{repo_name.repo_name}/hooks", headers=headers, json=data)


			#happy path, webhook gets setup and we need to insert the repo details and current user's github id into db
			if webhook.status_code == httpx.codes.CREATED:
				db.add(TrackedRepo(
					repo_id=repository_id,
					repo_name=repository_name,
					user_id=user.github_id
				))
				db.commit()

				return JSONResponse(
					content={"detail": "webhook created"},
					status_code=status.HTTP_201_CREATED
				)

			#this elif branch is meant for handling case when a repo has two (or more) maintainers and the webhook for that repo was already created by some other maintainer, but we are inserting into db table cause (repo_id, github_useid) pair is unique (two different repo maintainer of the same repo will obviously have diff github_userid)
			elif webhook.status_code == httpx.codes.UNPROCESSABLE_ENTITY:
				error_body = webhook.json()
				error_msg = error_body.get("errors")[0].get("message")

				if error_msg == "Hook already exists on this repository":
					db.add(TrackedRepo(
						repo_id=repository_id,
						repo_name=repository_name,
						user_id=user.github_id
					))
					db.commit()
					return JSONResponse(
						content={"detail": "webhook created"},
						status_code=status.HTTP_201_CREATED
					)
				else:
					raise HTTPException(status_code=webhook.status_code, detail="failed to create webhook")
		
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
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="repository does not exist")

		#occurs if, the github access token is invalid, or revoked (this happens when user manually revokes the app)
		else:
			raise HTTPException(status_code=repo_details.status_code, detail="failed to fetch repo details")