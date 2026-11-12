from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field

from banking_lab.api.dto import StrictDTO
from banking_lab.api.routes import Actor, admin
from banking_lab.application.beneficiaries import (
    beneficiaries,
    create_beneficiary,
    update_beneficiary,
)
from banking_lab.domain.rules import MAX_MINOR
from banking_lab.infrastructure.db import engine

router = APIRouter(prefix="/api/v1")
Admin = Annotated[dict[str, Any], Depends(admin)]


class BeneficiaryInput(StrictDTO):
    target_account_id: UUID
    alias: Annotated[str, Field(min_length=1, max_length=80)]


class BeneficiaryUpdate(StrictDTO):
    alias: Annotated[str, Field(min_length=1, max_length=80)]
    status: Literal["ACTIVE", "DISABLED"]


class LimitInput(StrictDTO):
    subject_type: Literal["ACCOUNT", "USER"]
    subject_id: UUID
    daily_minor: Annotated[int, Field(strict=True, gt=0, le=MAX_MINOR)]


@router.get("/beneficiaries")
def list_beneficiaries(actor: Actor) -> list[dict[str, Any]]:
    return beneficiaries(engine(), actor["id"])


@router.post("/beneficiaries", status_code=201)
def add_beneficiary(body: BeneficiaryInput, request: Request, actor: Actor) -> dict[str, Any]:
    return create_beneficiary(
        engine(), actor["id"], body.target_account_id, body.alias, request.state.request_id
    )


@router.patch("/beneficiaries/{beneficiary_id}")
def patch_beneficiary(
    beneficiary_id: UUID, body: BeneficiaryUpdate, request: Request, actor: Actor
) -> dict[str, Any]:
    return update_beneficiary(
        engine(), actor["id"], beneficiary_id, body.alias, body.status, request.state.request_id
    )


@router.put("/admin/transfer-limits")
def set_limit(body: LimitInput, request: Request, actor: Admin) -> dict[str, Any]:
    from banking_lab.application.operations import configure_limit

    return configure_limit(
        engine(),
        actor["id"],
        body.subject_type,
        body.subject_id,
        body.daily_minor,
        request.state.request_id,
    )


@router.get("/admin/outbox-events")
def outbox(actor: Admin, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[dict[str, Any]]:
    from banking_lab.application.operations import list_outbox

    return list_outbox(engine(), actor["id"], limit)


@router.post("/admin/outbox-events/{event_id}/retry")
def retry_event(event_id: UUID, request: Request, actor: Admin) -> dict[str, str]:
    from banking_lab.application.operations import retry_outbox

    retry_outbox(engine(), actor["id"], event_id, request.state.request_id)
    return {"status": "PENDING"}
