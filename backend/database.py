from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

db_password = os.getenv("POSTGRES_PASSWORD")
db_user = os.getenv("POSTGRES_USER")

#user the service name (instead of localhost) of the postgres db as per docker-compose-backend.yaml file
engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_password}@database:5432/backend_db")

sessionLocal = sessionmaker(bind=engine)

def get_db():
	db = sessionLocal()
	try:
		yield db
	finally:
		db.close()