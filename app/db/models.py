from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

class User(Base):
    __tablename__="users"

    id: Mapped[int]=mapped_column(primary_key=True)
    email: Mapped[str]=mapped_column(
        String(200),
        nullable=False,
        unique=True
    )
    username: Mapped[str]=mapped_column(
        String(50),
        nullable=True,
        unique=True
    )
    password_hash: Mapped[str]=mapped_column(
        String(255),
        nullable=False
    )
    polls: Mapped[list["Poll"]]= relationship(
        back_populates="user"
    )

class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    options: Mapped[list["PollOption"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",
    )
    userId: Mapped[int|None]= mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )
    user: Mapped["User|None"]= relationship(
        back_populates="polls"
    )


class PollOption(Base):
    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    poll_id: Mapped[int] = mapped_column(
        ForeignKey("polls.id"),
        nullable=False,
    )

    poll: Mapped["Poll"] = relationship(
        back_populates="options",
    )


