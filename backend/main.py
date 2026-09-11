from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from endpoints import users, webhook_setter, producer, live_feed, display_repos, overview, health_metrics, delete_webhook
from contextlib import asynccontextmanager
from workers.live_feed_consumer import live_feed_consumer
import asyncio
import models
from database import engine

models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
	task = asyncio.create_task(live_feed_consumer())
	yield
	task.cancel()
	await task

app = FastAPI(lifespan=lifespan)
app.include_router(users.router)
app.include_router(webhook_setter.router)
app.include_router(producer.router)
app.include_router(live_feed.router)
app.include_router(display_repos.router)
app.include_router(overview.router)
app.include_router(health_metrics.router)
app.include_router(delete_webhook)

origins = [
	"http://localhost:3000",
]
app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"]
)


@app.get("/")
def hello():
	return "hello"
	