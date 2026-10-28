from datetime import date, time
from uuid import UUID

from advanced_alchemy.base import UUIDv7Base
from sqlalchemy import ForeignKey, Index, SmallInteger, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gilda.core.models import User


class Slot(UUIDv7Base):
    __tablename__ = "slot"
    __table_args__ = (UniqueConstraint("association_id", "weekday", "start", "end"),)

    association_id: Mapped[UUID] = mapped_column(ForeignKey("association.id", ondelete="CASCADE"))
    # 0 for Monday to 6 for Sunday, as date.weekday().
    weekday: Mapped[int] = mapped_column(SmallInteger)
    start: Mapped[time]
    end: Mapped[time]


class Closure(UUIDv7Base):
    __tablename__ = "closure"

    association_id: Mapped[UUID] = mapped_column(ForeignKey("association.id", ondelete="CASCADE"))
    first: Mapped[date]
    last: Mapped[date]
    label: Mapped[str | None]


class Registration(UUIDv7Base):
    __tablename__ = "registration"
    __table_args__ = (
        # R4, also under concurrent requests.
        Index(
            "uq_registration_live_occurrence",
            "association_id",
            "date",
            "start",
            "end",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
        ),
    )

    association_id: Mapped[UUID] = mapped_column(ForeignKey("association.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"))
    date: Mapped[date]
    start: Mapped[time]
    end: Mapped[time]
    status: Mapped[str] = mapped_column(String(16))

    user: Mapped[User] = relationship(lazy="joined")
