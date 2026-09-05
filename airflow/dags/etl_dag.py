from airflow.sdk import dag, task
from airflow.timetables.trigger import CronTriggerTimetable
from airflow.sdk.bases.hook import BaseHook
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from backend.models import EventData, TrackedRepo
from seeder.seeder import SessionLocal


@dag(
	dag_id="etl_dag",
	start_date=datetime(2026, 8, 4, 2, 0, 0),
	schedule=CronTriggerTimetable("0 2 * * *", timezone='Asia/Kolkata'),
	catchup=False	
)

def etl_dag():

	@task
	#catching all the key value pairs passed by the executor using **kwargs
	def extract_github_payload(**kwargs):
		#start_date and end_date both are of the type pendulum.DateTime, i dont have to convert these into any other form for querying db cause pendulum.DateTime is inherting from the class datetime (from the stdlib datetime module) and the EventData table stores data in datetime format
		start_date = kwargs['data_interval_end'] - timedelta(days=29) #i am not implementing incremental load, hence my window will be 28 days before interval end (this window will shift nightly as interval_end keeps shifting forwards) 28 days of data + today's data
		end_date = kwargs['data_interval_end']

		#reading connection url from env (BaseHook.get() checks env variables first and then airflow's meta db)
		connection_obj = BaseHook.get_connection("backend_db")

		#extracting individual components from connection object
		con_url_parts={}
		con_url_parts["username"] = connection_obj.login
		con_url_parts["password"] = connection_obj.password
		con_url_parts["host"] = connection_obj.host
		con_url_parts["port"] = connection_obj.port
		con_url_parts["database"] = connection_obj.schema

		connection_url = URL.create("postgresql", **con_url_parts)

		engine = create_engine(connection_url)
		sessionLocal = sessionmaker(bind=engine)

		per_repo_data = {} #basically storing all the rows i got from EventData table, start date of repo monitoring and attaching them into respective repositories (repo_id basically)

		#example:
		# per_repo_data = {
		#     "repo_123": {
		#         "user_id": "user_456",
		#         "tracking_started_at": "2026-08-01",
		#         "events": [] 
		#     }
		# }

		with sessionLocal() as db:
			all_tracked_repos = db.query(TrackedRepo).all()
			
			for tracked_repo in all_tracked_repos:
				per_repo_data[tracked_repo.repo_id] = {
					"user_id": tracked_repo.user_id,
					"tracking_started_at": tracked_repo.tracking_started_at.isoformat(),
					"events": []  #data about each event, rather than storing raw payload
				}

			interval_event_data = db.query(EventData).filter(EventData.event_occurred_at >= start_date, EventData.event_occurred_at <= end_date).all()

		#since the EventData has payload data of multiple repos, i will need to calculate the metrics for each repo. interval_event_data is basically all the rows from EventData falling in that time and date range, but then i need to calculate those metrics per repo, so doing the following
		
		for row in interval_event_data:
			metric_dto = {
				"action": None,
			    "item_number": None, #pr number or issue number
			    "pr_created_at": None,
			    "is_merged": None,
			    "authors": []
			}

			metric_dto["id"] = row.id
			metric_dto["user_id"] = row.user_id
			metric_dto["repo_id"] = row.repo_id
			metric_dto["trigger_event"] = row.trigger_event

			#the column, event_occured_at is of type datetime and airflow parses the XCOMs into json, but it wont be able to parse datetime object, hence converting it into string first, making it json safe
			event_occurred_at = row.event_occurred_at.isoformat()
			metric_dto["event_occurred_at"] = event_occurred_at

			#adding relevant fields to dto from the payload itself:

			if row.trigger_event == 'push':
				#as per github webhooks, push event is also triggered when a branch is deleted and when a branch is deleted, the 'commits' key of the payload will be empty, also we must not count deleting a branch towards bus factor
				if row.payload.get("commits"):
					for commit in row.payload.get("commits"): #list of dictionary (list of commit objects) 
						name = commit.get("author", {}).get("name")
						metric_dto["authors"].append(name)
						

			elif row.trigger_event == 'pull_request':
				metric_dto["action"] = row.payload.get("action")
				metric_dto["item_number"] = row.payload.get("pull_request", {}).get("number")

				if row.payload.get("action") == 'closed':
					metric_dto["is_merged"] = row.payload.get("pull_request", {}).get("merged")
					metric_dto["pr_created_at"] = row.payload.get("pull_request", {}).get("created_at")
 

			elif row.trigger_event == 'pull_request_review':
				metric_dto["action"] = row.payload.get("action") #realistically we are only concerned with 'submitted' action of the pull_request_review event, since submit represents the true first time the maintainer reviewed the pr
				metric_dto["item_number"] = row.payload.get("pull_request", {}).get("number")
				
			elif row.trigger_event == "issues" or row.trigger_event == "issue_comment":
				metric_dto["action"] = row.payload.get("action")
				metric_dto["item_number"] = row.payload.get("issue", {}).get("number")

 
			if row.repo_id in per_repo_data:
				per_repo_data[row.repo_id]["events"].append(metric_dto)


		return per_repo_data

	@task
	def perform_analytics(per_repo_data, **kwargs):
		health_metric_dto = {}

		today = kwargs["data_interval_end"].date() #first get the date of when the task was executed, 'today' shouldn't be last active day for that repo rather it should be the current dag run date

		for repo_id, repo_data in per_repo_data.items():
			todays_activity_count = 0
			health_metric_dto[repo_id] = {"user_id": repo_data.get("user_id")}

			tracking_started_at = datetime.fromisoformat(repo_data["tracking_started_at"]).date()

			#today and tracking_started_at are both datetime.datetime objects, when we subtract two datetime objects we get datetime.timedelta object, min() doesnt work on datetime.timedelta objects, hence using .days to get an interger value that can be compared with 28
			monitored_days = min(28, (today - tracking_started_at).days)

			if monitored_days < 14:
				health_metric_dto[repo_id]["spike_decline_metric"] = 'insufficent data'

			else:
				baseline_tot = 0
				for event in repo_data.get("events"):
					event_dt = datetime.fromisoformat(event["event_occurred_at"]).date() #need to extract date, so that i can calculate, number of events per day

					if event_dt != today:
						baseline_tot += 1
					else:
						todays_activity_count += 1
				baseline_avg = baseline_tot / monitored_days

				if todays_activity_count > 1.5*baseline_avg and todays_activity_count >= 3:
					health_metric_dto[repo_id]["spike_decline_metric"] = 'spike'
				elif todays_activity_count < 0.5*baseline_avg and baseline_avg >= 1.0:
					health_metric_dto[repo_id]["spike_decline_metric"] = 'decline'
				else:
					health_metric_dto[repo_id]["spike_decline_metric"] = 'normal'

			#metric-2: pr lifecycle health:

			#if no sufficent prs in 28 days window then, calculated metric, then stop there
			tot_merged_prs=0
			time_to_merge = 0
			for event in repo_data.get("events"):
				if event["trigger_event"] == 'pull_request' and event["action"] == 'closed' and event["is_merged"]:
					tot_merged_prs += 1
					delta = datetime.fromisoformat(event["event_occurred_at"]).date() - datetime.fromisoformat(event["pr_created_at"]).date()
					time_to_merge += delta.days

			if tot_merged_prs < 3:
				health_metric_dto[repo_id]['pr_lifecycle_health'] = {"avg_time_to_merge": "insufficent data"}
			else:
				avg_time_to_merge = time_to_merge / tot_merged_prs
				health_metric_dto[repo_id]['pr_lifecycle_health'] = {"avg_time_to_merge": avg_time_to_merge}


		return health_metric_dto
				

	@task
	def store_health_metric():
		...
	
	extract = extract_github_payload()
	transform = perform_analytics(extract)
	load = store_health_metric()

	extract >> transform >> load


etl_dag()
