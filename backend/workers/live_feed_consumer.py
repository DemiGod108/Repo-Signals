import asyncio
import json
from confluent_kafka import Consumer
from registry import connected_clients

consumer_config = {
	"bootstrap.servers": "kafka:9092",
	"group.id": "live-feed",
	"auto.offset.reset": "latest", 	#it makes no sense to stream old / backlog / stale data into the live feed section hence making it latest
	"enable.auto.commit": False #we dont want it to commit any offset, because we need to start streaming the latest event
}

consumer = Consumer(consumer_config)
consumer.subscribe(["^[0-9]+-[a-zA-Z0-9._-]+$"])

async def live_feed_consumer():
	try:
		while True:	#consumer.poll() is synchronous, since we assign it a different thread where it can run independently without blocking the event loop
			msg = await asyncio.to_thread(consumer.poll, 1)

			if msg is None:
				continue
			if msg.error():
				print(f"Error: {msg.error()}")
				continue

			if not msg.headers():
				continue

			header = msg.headers()
			event_type = header[0][1].decode('utf-8')

			payload = json.loads(msg.value().decode('utf-8'))
			repo_id = payload.get("repository", {}).get("id")

			if not repo_id:
				continue 

			message = ""
			url = ""

			if event_type == "push":
				commits = payload.get("commits", [])
				count = len(commits)
				ref = payload.get("ref", "")
				branch = ref.split("/")[-1] if "/" in ref else ref
				url = payload.get("compare", "")
				message = f"{count} commits pushed to {branch}"

			elif event_type == "pull_request":
				pr = payload.get("pull_request", {})
				number = pr.get("number")
				action = payload.get("action")
				user_name = pr.get("user", {}).get("login", "someone")
				url = pr.get("html_url", "")

				if action == "closed" and pr.get("merged"):
					action = "merged"

				message = f"PR #{number} {action} by {user_name}"

			elif event_type == "pull_request_review":
				review = payload.get("review", {})
				pr = payload.get("pull_request", {})
				number = pr.get("number")
				state = review.get("state", "").replace("_", " ").lower()
				user_name = review.get("user", {}).get("login", "someone")
				url = review.get("html_url", "")

				message = f"{user_name} {state} PR #{number}"

			elif event_type == "issues":
				issue = payload.get("issue", {})
				number = issue.get("number")
				action = payload.get("action")
				user_name = issue.get("user", {}).get("login", "someone")
				url = issue.get("html_url", "")

				message = f"Issue #{number} {action} by {user_name}"

			elif event_type == "issue_comment":
				issue = payload.get("issue", {})
				comment = payload.get("comment", {})
				number = issue.get("number")
				user_name = comment.get("user", {}).get("login", "someone")
				url = comment.get("html_url", "")

				message = f"{user_name} commented on Issue #{number}"

			elif event_type == "fork":
				forkee = payload.get("forkee", {})
				user_name = forkee.get("owner", {}).get("login", "someone")
				url = forkee.get("html_url", "")

				message = f"Repo forked by {user_name}"

			else:	#this is for handling the ping event (i wouldnt technically need this branch because i control what events are subscribed in the webhook, but we need to handle the ping event that occurs when webhook gets created)
				continue


            #Universal DTO object
			dto = {
				"event_type": event_type,
				"message": message,
				"url": url
			}

			#loop through all the connected clients of a particular repo. A repo can have many maintainers, hence we push the DTO to each connected client
			for queue in connected_clients.get(repo_id, set()):
				queue.put_nowait(dto)

	except asyncio.CancelledError:
		consumer.close()
		raise