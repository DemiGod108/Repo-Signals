from pydantic import SecretStr
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
	secret_key: SecretStr
	algorithm: str = "HS256"
	access_token_expire_minutes: int = 30
	github_encryption_key: SecretStr
	development: bool

settings = Settings()

if settings.development:
    backend_url = "http://127.0.0.1:8000"
    backend_ngrok = "https://smudgy-synopses-appraisal.ngrok-free.dev"
    frontend_url = "http://localhost:3000"
else:
    backend_url = ""