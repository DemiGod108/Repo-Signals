import json
import signal
from confluent_kafka import Consumer
from database import sessionLocal
from models import EventData, ActiveRepoItems
from datetime import datetime, UTC

class GracefulKiller:
	kill_now = False
	def __init__(self):
		signal.signal(signal.SIGINT, self.exit_gracefully)
		signal.signal(signal.SIGTERM, self.exit_gracefully)

	def exit_gracefully(self, signum, frame):
		self.kill_now = True

consumer_config = {
	"bootstrap.servers": "kafka:9092",
	"group.id": "event-data-reader",
	"auto.offset.reset": "earliest",
	"enable.auto.commit": False
}

consumer = Consumer(consumer_config)
consumer.subscribe(["^[0-9]+-[a-zA-Z0-9._-]+$"]) #regex pattern to subscribe to topic name repo-id-repo-name

killer = GracefulKiller()

while not killer.kill_now:
	msg = consumer.poll(1.0)
	if msg is None:
		continue
	if msg.error():
		print(f"Error: {msg.error()}")
		continue

	header = msg.headers() #header is a list of tuple basically it will be in [('event', b'push')] format
	value = msg.value().decode('utf-8')
	payload = json.loads(value)

	github_user_id = payload["repository"]["owner"]["id"]
	repo_id = payload["repository"]["id"]
	trigger_event = header[0][1].decode('utf-8') #since the event itself will be in byte format converting into string

	#need these two flags to decide whether to add or delete pr and issues event to the ActiveRepoItems table
	enter_to_db = False
	del_from_db = False

	#extracting datetime details based on the event that triggered the webhook
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

	else: #this else part is mainly for the 'ping' event which occurs when the webhook is created
		continue

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

 
	with sessionLocal() as db:
		db.add(EventData(
			payload=payload, 
			user_id=github_user_id, 
			repo_id=repo_id, 
			trigger_event=trigger_event,
			event_occurred_at=event_occurred_at
			)
		)

		db.flush()

		if enter_to_db:
			db.add(ActiveRepoItems(
				user_id=github_user_id,
				repo_id=repo_id,
				item_num=item_num,
				event_type=trigger_event
				)
			)
		if del_from_db:
			#chaining .delete() directly executes a single sql command without fetching the row first, this also performs the sql command in one network trip and ignores missing rows (like pre-existing prs) without throwing a NoneType error when i try to delete it after fetching
			obj = db.query(ActiveRepoItems).filter(ActiveRepoItems.user_id == github_user_id, ActiveRepoItems.repo_id == repo_id, ActiveRepoItems.item_num == item_num).delete()
		db.commit()
	consumer.commit(msg)
		
consumer.close()