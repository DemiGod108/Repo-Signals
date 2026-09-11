import httpx
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from models import Users
from schemas import SelectRepo
from utils.auth import get_current_user
from utils.encrypt_decrypt import cipher
from utils.config import backend_ngrok
from database import get_db
from sqlalchemy.orm import Session
from models import TrackedRepo

router = APIRouter()

@router.post("/setup-webhook")
async def setup_webhooks(repo_name: SelectRepo, user: Users = Depends(get_current_user), db: Session = Depends(get_db)):
	encrypted_github_token = user.encrypted_github_access_token.encode('utf-8') #in db it will stored in string format, but for .decrypt() to work it needs encrypted content in bytes format hence encoding it
	decrypted_github_token = cipher.decrypt(encrypted_github_token).decode('utf-8') #needs to be in string format for Authorization Bearer to work

	headers = {
		"accept": "application/vnd.github+json",
		"Authorization": f"Bearer {decrypted_github_token}"
	}

	#we need to retrieve repo details in order to decide whether this current user can setup webhook for the specified repo or not
	async with httpx.AsyncClient() as client:
		repo_details_req = await client.get(url=f"https://api.github.com/repos/{user.github_username}/{repo_name.repo_name}", headers=headers)
	repo_details = repo_details_req.json()

	#handles the case when the user entered repo doesnt even exist, if it doesnt exists exit the function
	if repo_details_req.status_code == httpx.codes.NOT_FOUND:
		raise HTTPException(detail="Repo not found", status_code=status.HTTP_404_NOT_FOUND)

	#this if branch is for handling case when the github access token was manually revoked by the user in the github website, if token is invalid again exit the function right away
	if repo_details_req.status_code != 200:
		raise HTTPException(detail="failed to fetch repo details", status_code=repo_details_req.status_code)

	#repo exists, github access token is valid hence we extract repo info (repo_details_req.status_code==200 case:)
	repository_id = repo_details["id"]
	repository_name = repo_details["name"]

	#if the current user isnt the admin of the repo then they cant setup webhook (as per github only admins can setup webhooks for a particular repo) hence just exit the function right away
	if not repo_details["permissions"]["admin"]:
		raise HTTPException(detail="you are not the admin", status_code=status.HTTP_403_FORBIDDEN)

	#if the execution reached here that means, repo exists, current user is indeed its admin 
	tracked_repo_obj = db.query(TrackedRepo).filter(TrackedRepo.user_id == user.github_id, TrackedRepo.repo_id == repository_id).first()

	#this handles the case when the admin (i.e the repo maintainer) who setup webhook is trying to setup webhook for the same repo again (same maintainer trying to setup webhook for the same repo, hence repo_id, github_userid pair isnt unique), exit right away
	if tracked_repo_obj:
		raise HTTPException(detail="repository is already added", status_code=status.HTTP_400_BAD_REQUEST)

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
	data = webhook.json()

	#happy path, webhook gets setup and we need to insert the repo details and current user's github id into db
	if webhook.status_code == httpx.codes.CREATED:
		hook_id = data.get("id")
		db.add(TrackedRepo(
			repo_id=repository_id,
			repo_name=repository_name,
			user_id=user.github_id,
			hook_id = hook_id,
			tracking_started_at = datetime.now(tz=UTC)
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

			#even if the webhook exists, i cant get its hook_id when the status code is 422, github wont send it, hence i will need to 	use github api to query for webhook details for that particular repo and find the one which was set by my app
			async with httpx.AsyncClient() as client:
				webhook_req = await client.get(f"https://api.github.com/repos/{user.github_username}/{repo_name.repo_name}/hooks", headers=headers)

			webhook_data = webhook_req.json()

			if webhook_req.status_code == httpx.codes.OK:
				hook_id = None
				#the same repo can have multiple webhooks, so i need to loop through all the webhook of that repo and find that webhook which has the same config url as my backend payload delivery url, after finding it extract the id and store in db
				for data in webhook_data:
					if data["config"]["url"] == f"{backend_ngrok}/webhook-payload":
						hook_id = data["id"]
						break

				if hook_id is None:
					raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No webhook for Repo Signals")

				db.add(TrackedRepo(
					repo_id=repository_id,
					repo_name=repository_name,
					user_id=user.github_id,
					tracking_started_at=datetime.now(tz=UTC),
					hook_id=hook_id
				))
				db.commit()
				return JSONResponse(
					content={"detail": "webhook created"},
					status_code=status.HTTP_201_CREATED
				)
			else:
				raise HTTPException(status_code=webhook_req.status_code, detail="failed to create webhook")
		else:
			raise HTTPException(status_code=webhook.status_code, detail="failed to create webhook")

	else:
		raise HTTPException(status_code=webhook.status_code, detail="failed to create webhook")