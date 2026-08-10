from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/webhook-payload")
async def webhook_payload(request: Request):
	payload = await request.json()
	repo_id = payload["repository"]["id"]
	event = request.headers.get("X-Github-Event")

	print(repo_id, event)