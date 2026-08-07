from sqlalchemy import String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base

class User(Base):
    __tablename__ = "users"

    provider: Mapped[str] = mapped_column(String, default="github", index=True)
    provider_account_id: Mapped[str] = mapped_column(String, index=True, nullable=True)
    github_id: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    google_id: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    username: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str] = mapped_column(String, nullable=True)
    
    # OAuth token is retained server-side for user GitHub API calls.
    github_token: Mapped[str] = mapped_column(String, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<User {self.username}>"
