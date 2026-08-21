from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import ForeignKey, UniqueConstraint
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.types import JSON
from typing import Any
from datetime import datetime

class Base(DeclarativeBase):
	#need to this specify what dict[str, Any] maps to in database
	type_annotation_map = {
        dict[str, Any]: JSON
    }

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

class EventData(Base):
	__tablename__ = "event_data"

	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
	payload: Mapped[dict[str, Any]] = mapped_column()
	user_id: Mapped[int] = mapped_column(ForeignKey("users.github_id"))
	repo_id: Mapped[int] = mapped_column()
	trigger_event: Mapped[str] = mapped_column()
	event_occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class TrackedRepo(Base):
	__tablename__ = "tracked_repo"

	id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
	repo_id: Mapped[int] = mapped_column()
	repo_name: Mapped[str] = mapped_column()
	user_id: Mapped[int] = mapped_column(ForeignKey("users.github_id"))

	__table_args__ = (
			UniqueConstraint("user_id", "repo_id", name="unq_user_repo"),
	)

#need the table for tracking number of open prs and issues
class ActiveRepoItems(Base):
	__tablename__ = "active_repo_items"

	id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.github_id", ondelete="CASCADE"))
	repo_id: Mapped[int] = mapped_column()
	item_num: Mapped[int] = mapped_column()
	event_type: Mapped[str] = mapped_column()
