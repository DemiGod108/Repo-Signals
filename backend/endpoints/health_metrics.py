from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from database import get_db
from sqlalchemy.orm import Session
from models import TrackedRepo, HealthMetrics, Users
from utils.auth import get_current_user


router = APIRouter()

@router.get("/health-metrics/{repo_id}")
def display_health_metrics(repo_id: int, db: Session = Depends(get_db), user: Users = Depends(get_current_user)):

	tracked_repo = db.query(TrackedRepo).filter(TrackedRepo.repo_id == repo_id, TrackedRepo.user_id == user.github_id).scalar()

	if not tracked_repo:
		raise HTTPException(detail='Incorrect repository', status_code=status.HTTP_400_BAD_REQUEST)

	health_metric_row = db.query(HealthMetrics).filter(HealthMetrics.repo_id == repo_id).order_by(HealthMetrics.calculated_at.desc()).first()

	if health_metric_row:
		health_metric = jsonable_encoder(health_metric_row)
		return JSONResponse(content=health_metric)

	else:
		#building this dictionary because then i wouldnt need to handle any logic in the frontend. In fe i will just need to use the same keys regardless of whether the dag has completed its first execution or not
		health_metric = {
			"spike_decline_metric": "insufficient data",
			"pr_lifecycle_health":  "insufficient data",
			"bus_factor": "insufficient data",
			"stale_issue": "insufficient data"
		}

		return JSONResponse(content=health_metric)

	#reason for if-else branch:
	#if a user sets up monitoring for a repo at 3pm, the airflow dag wont run till 2am, this would mean till 2am, the HealthMetric table wont have any record of that particular repo (repo_id) 
	#this 'No sufficent data yet' case is different from one in the transform step (dag logic)