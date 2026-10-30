from datetime import datetime
from typing import Literal
from uuid import UUID

from advanced_alchemy.base import UUIDv7Base
from advanced_alchemy.extensions.litestar.session import SessionModelMixin
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

Role = Literal["manager", "volunteer"]


class User(UUIDv7Base):
    __tablename__ = "user_account"

    display_name: Mapped[str]
    # Stored lowercased, so uniqueness ignores case.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None]
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def has_account(self) -> bool:
        return self.password_hash is not None

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None


class Association(UUIDv7Base):
    __tablename__ = "association"

    name: Mapped[str]
    timezone: Mapped[str] = mapped_column(String(64), server_default="Europe/Paris")


class Membership(UUIDv7Base):
    __tablename__ = "membership"
    __table_args__ = (UniqueConstraint("user_id", "association_id"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"))
    association_id: Mapped[UUID] = mapped_column(ForeignKey("association.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))

    user: Mapped[User] = relationship(lazy="joined")
    association: Mapped[Association] = relationship(lazy="joined")


class EmailVerificationToken(UUIDv7Base):
    __tablename__ = "email_verification_token"

    # One pending confirmation per user: issuing a new one replaces it (R8).
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), unique=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserSession(SessionModelMixin):
    __tablename__ = "user_session"
