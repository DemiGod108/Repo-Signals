from pydantic import BaseModel

class SelectRepo(BaseModel):
	repo_name: str