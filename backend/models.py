from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import ForeignKey
from datetime import datetime
from sqlalchemy import DateTime

class Base(DeclarativeBase):
	pass

class Users(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
	github_id: Mapped[int] = mapped_column(index=True, primary_key=True, unique=True)
	github_username: Mapped[str] = mapped_column()
	encrypted_github_access_token: Mapped[str] = mapped_column()

class RefreshToken(Base):
	__tablename__ = "refresh_tokens"

	id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.github_id", ondelete="CASCADE"))
	token_hash: Mapped[str] = mapped_column()
	created_at: Mapped[datetime] = mapped_column(DateTime)
	expires_at: Mapped[datetime] = mapped_column(DateTime)
	is_revoked: Mapped[bool] = mapped_column()