"""Typed SQLAlchemy mappings for financial read models; migrations freeze actual DDL."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    owner_user_id: Mapped[UUID | None]
    account_type: Mapped[str]
    currency: Mapped[str]
    status: Mapped[str]
    balance_minor: Mapped[int] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Posting(Base):
    __tablename__ = "ledger_postings"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    journal_group_id: Mapped[UUID]
    account_id: Mapped[UUID]
    currency: Mapped[str]
    signed_amount_minor: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    entry_sequence: Mapped[int]
