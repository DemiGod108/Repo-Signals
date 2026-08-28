from airflow.sdk import dag, task
from airflow.timetables.trigger import CronTriggerTimetable
from airflow.sdk.bases.hook import BaseHook
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker
from datetime import datetime
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
		start_date = kwargs['data_interval_start']
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

		per_repo_data = {}
		#basically storing all the rows i got from EventData table and attaching them into respective repositories (repo_id basically)
		for row in interval_event_data:
			info_dict = {}

			info_dict["id"] = row.id
			info_dict["payload"] = row.payload
			info_dict["user_id"] = row.user_id
			info_dict["repo_id"] = row.repo_id
			info_dict["trigger_event"] = row.trigger_event

			#the column, event_occured_at is of type datetime and airflow parses the XCOMs into json, but it wont be able to parse datetime object, hence converting it into string first, making it json safe
			event_occured_at = row.event_occurred_at.isoformat()
			info_dict["event_occured_at"] = event_occured_at
			per_repo_data.setdefault(row.repo_id, []).append(info_dict)


		return per_repo_data

	@task
	def perform_analytics(interval_event_data):
		print(interval_event_data)

	@task
	def store_health_metric():
		...
	
	extract = extract_github_payload()
	transform = perform_analytics(extract)
	load = store_health_metric()

	extract >> transform >> load


etl_dag()
