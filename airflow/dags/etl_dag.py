from airflow.sdk import dag, task
from airflow.timetables.trigger import CronTriggerTimetable
from airflow.sdk.bases.hook import BaseHook
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from backend.models import EventData


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
		start_date = kwargs['data_interval_end'] - timedelta(days=28) #i am not implementing incremental load, hence my window will be 28 days before interval end (this window will shift nightly as interval_end keeps shifting forwards)
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

		with sessionLocal() as db:
			interval_event_data = db.query(EventData).filter(EventData.event_occurred_at >= start_date, EventData.event_occurred_at <= end_date).all()

		#since the EventData has payload data of multiple repos, i will need to calculate the metrics for each repo. interval_event_data is basically all the rows from EventData falling in that time and date range, but then i need to calculate those metrics per repo, so doing the following

		per_repo_event_data = {}
		#basically storing all the rows i got from EventData table and attaching them into respective repositories (repo_id basically)
		for row in interval_event_data:
			metric_dto = {
				"action": None,
			    "item_number": None, #pr number or issue number
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
 

			elif row.trigger_event == 'pull_request_review':
				metric_dto["action"] = row.payload.get("action") #realistically we are only concerned with 'submitted' action of the pull_request_review event, since submit represents the true first time the maintainer reviewed the pr
				metric_dto["item_number"] = row.payload.get("pull_request", {}).get("number")
				
			elif row.trigger_event == "issues" or row.trigger_event == "issue_comment":
				metric_dto["action"] = row.payload.get("action")
				metric_dto["item_number"] = row.payload.get("issue", {}).get("number")


			per_repo_event_data.setdefault(row.repo_id, []).append(metric_dto)


		return per_repo_event_data

	@task
	def perform_analytics(per_repo_event_data):
		health_metric_dto = {}

		for repo_id, event_list in per_repo_event_data.items():
			daily_count={} #{date (event occured at): number of events} this event includes all the events that the webhook subscribed to
			for event in event_list:
				event_dt = datetime.fromisoformat(event["event_occurred_at"]).date() #need to extract date, so that i can calculate, number of events per day 
				daily_count[event_dt] = daily_count.get(event_dt, 0) + 1

			sorted_dates = sorted(daily_count.keys())
			today = sorted_dates[-1]
			rolling_baseline_dates = sorted_dates[:-1] #everything except the latest day

			baseline_tot = 0
			for baseline in rolling_baseline_dates:
				baseline_tot += daily_count.get(baseline, 0)

			if len(rolling_baseline_dates) == 0:  #for handling divsion by zero cases
				status = "insufficient_data"

			else:
				baseline_avg = baseline_tot / len(rolling_baseline_dates)

				todays_activity_count = daily_count[today]
				if todays_activity_count > baseline_avg * 1.5:
					status = "spike"
				elif todays_activity_count < baseline_avg * 0.5:
					status = "decline"
				else:
					status = "normal"

			health_metric_dto.setdefault(repo_id, []).append(status)

	@task
	def store_health_metric():
		...
	
	extract = extract_github_payload()
	transform = perform_analytics(extract)
	load = store_health_metric()

	extract >> transform >> load


etl_dag()
