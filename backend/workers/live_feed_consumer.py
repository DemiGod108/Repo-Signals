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
			elif msg.error():
				print(f"Error: {msg.error()}")
				continue

			##DTO stuff here i will decide what to display, for now dumping the entire payload	

			payload = json.loads(msg.value().decode('utf-8'))
			repo_id = payload["repository"]["id"]

			#loop through all the connected clients to a particular repo. A repo can have many maintainers, hence we push the DTO to each connected client
			for queue in connected_clients.get(repo_id, set()):
				queue.put_nowait(payload)

	except asyncio.CancelledError:
		consumer.close()
		raise