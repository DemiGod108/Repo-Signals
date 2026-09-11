from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from models import Users, TrackedRepo
from utils.auth import get_current_user
from database import get_db
from sqlalchemy.orm import Session
from datetime import datetime

router = APIRouter()

@router.get("/display-tracked-repos")
def display_tracked_repos(user: Users = Depends(get_current_user), db: Session = Depends(get_db)):
	github_id = user.github_id

	#get all the db rows from the table TrackedRepo where the user_id matches the github_id of the logged in user
	tracked_repo_obj = db.query(TrackedRepo).filter(TrackedRepo.user_id == github_id).all()

	#creating a neat data structure to return to the frontend
	response_list = []
	for obj in tracked_repo_obj:
		tracking_started_at = obj.tracking_started_at.isoformat() #the timedate info stored in db is a datetime.datetime object and its not json serializable hence need to convert into json safe format
		each_repo = {
			"repo_id": obj.repo_id,
			"repo_name": obj.repo_name,
			"tracking_started_at": tracking_started_at
		}
		response_list.append(each_repo)

	return JSONResponse(
		content={"tracked_repos": response_list},
		status_code=status.HTTP_200_OK
	)


