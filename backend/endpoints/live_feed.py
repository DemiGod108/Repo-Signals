import models
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from utils.auth import get_current_user
from database import get_db
from sqlalchemy.orm import Session
from registry import connected_clients

async def stream_events(clients, con_queue, repo_id):
	try:
		while True:
			event_raw = await con_queue.get()
			event = json.dumps(event_raw)
			yield f"data: {event}\n\n"
	finally:
		clients[repo_id].discard(con_queue)

router = APIRouter()

@router.get("/live-feed/{repo_id}")
async def get_real_time_data(repo_id: int, user: models.Users = Depends(get_current_user), db: Session = Depends(get_db)):

	#first we need to make sure whether the current user (maintainer) has setup monitoring for the repo_id being requested (basically authoriztion)
	tracked_repo_obj = db.query(models.TrackedRepo).filter(models.TrackedRepo.repo_id == repo_id, models.TrackedRepo.user_id == user.github_id).first()

	#this means the repo whose live feed is being requested isnt owned by the current logged in user
	if not tracked_repo_obj:
		raise HTTPException(detail="unable to load live feed", status_code=status.HTTP_400_BAD_REQUEST)

	repo_id = tracked_repo_obj.repo_id
	connection_queue = asyncio.Queue()	#designate a queue for the current connection
	connected_clients.setdefault(repo_id, set()).add(connection_queue)


	return StreamingResponse(stream_events(connected_clients, connection_queue, repo_id), media_type="text/event-stream")

