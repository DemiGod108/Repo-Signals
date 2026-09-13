from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta, UTC
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


@router.get("/graph/{repo_id}")
def activity_graph(repo_id: int, user: Users = Depends(get_current_user), db: Session = Depends(get_db)):
	github_id = user.github_id

	tracked_repo_obj = db.query(TrackedRepo).filter(TrackedRepo.user_id == github_id, TrackedRepo.repo_id == repo_id).first()

	if not tracked_repo_obj:
		raise HTTPException(detail="invalid repository", status_code=status.HTTP_400_BAD_REQUEST)
	
	today = datetime.now(tz=UTC).date() #this is a date object NOT datetime object anymore because of .date
	past = today - timedelta(days=29) #past is of type date, because we subtracted number of days from date object (i.e today)

	#in tracked_repo table the tracking_started_at is stored as timezone aware object, i.e it is a datetime object so we need to convert even tracking_started_at to date object so that we can subtract it from variable today with no TypeErrors
	tracking_started_at = tracked_repo_obj.tracking_started_at.date()

	#same idea as spike / delcine metric
	if (today - tracking_started_at).days < 14:
		raise HTTPException(detail="insufficient data", status_code=status.HTTP_404_NOT_FOUND)

	#the db column: event_occured_at stores values that are of type datetime in python, so i cant directly compare it with today and past cause both or date objects, so before comparing i need to convert event_occured_at from datetime object to date object which is done by using func.date().
	event_objs = db.query(EventData).filter(func.date(EventData.event_occurred_at) <= today, func.date(EventData.event_occurred_at) >= past, EventData.repo_id == repo_id).order_by(func.date(EventData.event_occurred_at)).all()

	date_count = {}
	#loop stores number of events occured on each calendar date on that window (today-past window)
	for event_obj in event_objs:
		event_date = event_obj.event_occurred_at.date()
		date_count[event_date] = date_count.get(event_date, 0) + 1

	#this loop just fills the date_count dictionary with missing dates, and sets its value to zero, so that chart.js and render graphs properly
	running_date = past
	while running_date <= today:
		if running_date not in date_count:
			date_count[running_date] = 0

		running_date += timedelta(days=1)

	#sorting in chronological order, so that graphs can be render properly
	#sorted() on a dictionary returns a list of tuples something like: [(key1, value1), (key2, value2), ...] but in sorted order, sorting happens based on dates, because its the first item in the tuple of (date, count)
	sorted_date_count = sorted(date_count.items()) 

	#building the response:
	dates_list=[]
	counts_list=[]
	for date, count in sorted_date_count:
		dates_list.append(date)
		counts_list.append(count)

	json_safe_dates_list = jsonable_encoder(dates_list) #datetime object arent json safe so need to convert them, whereas play integer stored in counts is json safe

	return JSONResponse(content={'dates': json_safe_dates_list, 'count': counts_list}, status_code=status.HTTP_200_OK)
