from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB
from models import Users, EventData, TrackedRepo, ActiveRepoItems
from database import get_db
from utils.auth import get_current_user

router = APIRouter()

@router.get("/overview/{repo_id}")
def repo_overview(repo_id: int, user: Users = Depends(get_current_user), db: Session = Depends(get_db)):
	github_id = user.github_id

	tracked_repo_obj = db.query(TrackedRepo).filter(TrackedRepo.user_id == github_id, TrackedRepo.repo_id == repo_id).first()

	if not tracked_repo_obj:
		raise HTTPException(detail="invalid repository", status_code=status.HTTP_400_BAD_REQUEST)

	#remember the payload is stored as text based JSON
	# 1. Extract the commits key from the payload
	# 2. .cast(JSONB) converts the text into a Postgres binary JSON array so that i can use the func.jsonb_array_length() function
	# 3. func.jsonb_array_length() counts the items inside that array for each row
	# 4. func.sum() adds those individual row counts together
	# 5. .scalar() strips away the SQLAlchemy tuple wrapper to return a clean integer
	total_num_commits =  db.query(func.sum(func.jsonb_array_length(EventData.payload["commits"].cast(JSONB)))).filter(EventData.repo_id == repo_id, EventData.trigger_event == "push").scalar()

	total_num_forks = db.query(EventData).filter(EventData.repo_id == repo_id, EventData.trigger_event == "fork").count()

	total_num_open_prs = db.query(ActiveRepoItems).filter(ActiveRepoItems.repo_id == repo_id, ActiveRepoItems.event_type == "pull_request").count()

	total_num_open_issues = db.query(ActiveRepoItems).filter(ActiveRepoItems.repo_id == repo_id, ActiveRepoItems.event_type == "issues").count()

	overview = {
		"total_num_commits": total_num_commits,
		"total_num_forks": total_num_forks,
		"total_num_open_prs": total_num_open_prs,
		"total_num_open_issues": total_num_open_issues
	}

	return JSONResponse(
		content={"repo_overview": overview},
		status_code=status.HTTP_200_OK
	)
