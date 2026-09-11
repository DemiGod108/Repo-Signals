import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models import TrackedRepo, Users
from utils.auth import get_current_user
from utils.encrypt_decrypt import cipher
from database import get_db

router = APIRouter()

@router.delete("/delete-webhook")
async def delete_webhook(repo_id: int, user: Users = Depends(get_current_user), db: Session = Depends(get_db)):

	#perform authorization
	tracked_repo_obj = db.query(TrackedRepo).filter(TrackedRepo.user_id == user.github_id, TrackedRepo.repo_id == repo_id).first()
	if not tracked_repo_obj:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='invalid repo id')

	#if the current logged in user is indeed tracking the given repo (repo_id then delete it)
	encrypted_github_token = user.encrypted_github_access_token.encode('utf-8') #in db it will stored in string format, but for .decrypt() to work it needs encrypted content in bytes format hence encoding it
	decrypted_github_token = cipher.decrypt(encrypted_github_token).decode('utf-8') #needs to be in string format for Authorization Bearer to work

	headers = {
		"accept": "application/vnd.github+json",
		"Authorization": f"Bearer {decrypted_github_token}"
	}
	
	hook_id = tracked_repo_obj.hook_id
	async with httpx.AsyncClient() as client:
		del_webhook_req = await client.delete(f"https://api.github.com/repos/{user.github_username}/{tracked_repo_obj.repo_name}/hooks/{hook_id}", headers=headers)

	if del_webhook_req.status_code == httpx.codes.NO_CONTENT:
		db.delete(tracked_repo_obj)
		db.commit()

		return JSONResponse(
			content={"detail": "webhook deleted, monitoring stopped"},
			status_code=status.HTTP_200_OK
		)

	elif del_webhook_req.status_code == httpx.codes.NOT_FOUND:
		raise HTTPException(detail="webhook for this repo not found", status_code=status.HTTP_404_NOT_FOUND)
