from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from banking_lab.domain.rules import MAX_MINOR, TransferCommand


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(StrictDTO):
    email: Annotated[str, Field(min_length=3, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=1024)]


class Session(StrictDTO):
    refresh_token: Annotated[str, Field(min_length=32, max_length=256)]


class Transfer(StrictDTO):
    source_account_id: UUID
    destination_account_id: UUID
    amount_minor: Annotated[int, Field(strict=True, gt=0, le=MAX_MINOR)]
    currency: Literal["USD"] = "USD"
    reference: Annotated[str, Field(max_length=140)] | None = None

    def command(self) -> TransferCommand:
        return TransferCommand(**self.model_dump())
