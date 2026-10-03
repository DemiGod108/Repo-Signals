#this endpoint is only for load testing, in the actual flow this endpoint is never called

from fastapi import APIRouter, status, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.routing import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from datetime import datetime, UTC
from models import EventData, ActiveRepoItems

router = APIRouter()

@router.post("/webhook-db")
async def webhook_db(request: Request, db: Session = Depends(get_db)):
	payload = await request.json()
	github_user_id = payload["repository"]["owner"]["id"]
	repo_id = payload["repository"]["id"]
	trigger_event = request.headers.get("X-Github-Event")

	enter_to_db = False
	del_from_db = False

	if trigger_event == 'push':
		event_time = int(payload["repository"]["pushed_at"])
		event_occurred_at = datetime.fromtimestamp(event_time, tz=UTC)

	elif trigger_event == "pull_request":
		event_time = payload["pull_request"]["updated_at"]

	elif trigger_event == "pull_request_review":
		event_time = payload["review"]["submitted_at"]

	elif trigger_event == "fork":
		event_time = payload["forkee"]["created_at"]

	elif trigger_event == "issues":
		event_time = payload["issue"]["updated_at"]

	elif trigger_event == "issue_comment":
		event_time = payload["comment"]["updated_at"]

	if trigger_event != "push":
		event_occurred_at = datetime.fromisoformat(event_time)

	#extracting the item number, this item number is required when we need to delete a row from the ActiveRepoItems table
	if trigger_event == "pull_request":
		item_num = payload.get("pull_request").get("number")
	if trigger_event == "issues":
		item_num = payload.get("issue").get("number")

	if trigger_event == "pull_request" or trigger_event == "issues":
		if payload.get("action") == "opened" or payload.get("action") == "reopened":
			enter_to_db = True

		#we need to specifically catch 'closed' event in elif branch because a pr/issue has multiple states like opened/closed/assigned, but we are only concerned with 'closed', so that we can delete the row once the pr/issue gets closed
		elif payload.get("action") == "closed":
			del_from_db = True

	db.add(EventData(
		payload=payload,
		user_id=github_user_id,
		repo_id=repo_id,
		trigger_event=trigger_event,
		event_occurred_at=event_occurred_at
		)
	)

	if enter_to_db:
		db.add(ActiveRepoItems(
			user_id=github_user_id,
			repo_id=repo_id,
			item_num=item_num,
			event_type=trigger_event
			)
		)

	if del_from_db:
		obj = db.query(ActiveRepoItems).filter(ActiveRepoItems.user_id == github_user_id, ActiveRepoItems.repo_id == repo_id, ActiveRepoItems.item_num == item_num).delete()

	db.commit()

	return JSONResponse(content="payload saved successfully", status_code=status.HTTP_200_OK)