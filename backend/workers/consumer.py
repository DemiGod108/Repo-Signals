import json
import signal
from confluent_kafka import Consumer
from database import sessionLocal
from models import EventData
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
		print("no msg")
		continue
	if msg.error():
		print(f"Error: {msg.error()}")
		continue

	header = msg.headers() #header is a list of tuple basically it will be in [('event', b'push')] format
	print(header)
	value = msg.value().decode('utf-8')
	payload = json.loads(value)

	github_user_id = payload["repository"]["owner"]["id"]
	repo_id = payload["repository"]["id"]
	trigger_event = header[0][1].decode('utf-8') #since the event itself will be in byte format converting into string

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

	with sessionLocal() as db:
		db.add(EventData(
			payload=payload, 
			user_id=github_user_id, 
			repo_id=repo_id, 
			trigger_event=trigger_event,
			event_occurred_at=event_occurred_at
			)
		)

		db.commit()
	consumer.commit(msg)
		
consumer.close()