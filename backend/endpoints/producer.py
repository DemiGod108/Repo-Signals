from fastapi import APIRouter, Request
from confluent_kafka import Producer
import json

producer_config= {
	"bootstrap.servers": "kafka:9092"
}

producer = Producer(producer_config)

def ack(error, msg):
	if msg:
		print(f"Topic name: {msg.topic()}")
		print(f"Partition: {msg.partition()}")
		print(f"Payload: {msg.value().decode('utf-8')}")
	else:
		print(error)

router = APIRouter()

@router.post("/webhook-payload")
async def webhook_payload(request: Request):
	payload = await request.json()
	repo_id = payload["repository"]["id"]
	repo_name = payload["repository"]["name"]
	event = request.headers.get("X-Github-Event")

	kafka_record = json.dumps(payload).encode('utf-8')

	print("route hit")

	producer.produce(
		topic=f"{repo_id}-{repo_name}",
		headers={"event": event},
		value=kafka_record,
		callback=ack
	)

	producer.poll(0)