from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse, Response

from banking_lab.api.dto import Login, Session, Transfer
from banking_lab.application.auth import AuthService
from banking_lab.application.history import HistoryService
from banking_lab.application.reconciliation import reconcile
from banking_lab.application.transfers import TransferService
from banking_lab.config import settings
from banking_lab.domain.rules import DomainError
from banking_lab.infrastructure.db import engine

router = APIRouter(prefix="/api/v1")


def auth() -> AuthService:
    return AuthService(engine(), settings())


def user(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise DomainError("AUTH_INVALID", "Bearer access token required.", 401)
    return auth().authenticate(authorization[7:])


Actor = Annotated[dict[str, Any], Depends(user)]


def admin(actor: Actor) -> dict[str, Any]:
    if actor["role"] != "ADMIN":
        raise DomainError("FORBIDDEN", "Admin role required.", 403)
    return actor


def history() -> HistoryService:
    return HistoryService(engine(), settings().jwt_secret)


@router.post("/auth/login")
def login(body: Login, request: Request) -> dict[str, Any]:
    return auth().login(body.email, body.password, request.state.request_id)


@router.post("/auth/refresh")
def refresh(body: Session, request: Request) -> dict[str, Any]:
    return auth().refresh(body.refresh_token, request.state.request_id)


@router.post("/auth/logout", status_code=204)
def logout(body: Session, request: Request) -> Response:
    auth().logout(body.refresh_token, request.state.request_id)
    return Response(status_code=204)


@router.get("/me")
def me(actor: Actor) -> dict[str, Any]:
    return actor


@router.get("/accounts")
def accounts(actor: Actor) -> list[dict[str, Any]]:
    return history().accounts(actor["id"])


@router.get("/accounts/{account_id}")
def account(account_id: UUID, actor: Actor) -> dict[str, Any]:
    return history().accounts(actor["id"], account_id)[0]


@router.get("/accounts/{account_id}/statement")
def statement(
    account_id: UUID,
    actor: Actor,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    return history().page(
        actor["id"], account=account_id, limit=limit, cursor=cursor, since=since, until=until
    )


@router.post("/transfers", status_code=201)
def create_transfer(
    body: Transfer,
    request: Request,
    actor: Actor,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    result = TransferService(engine()).create(
        actor["id"], body.command(), idempotency_key, request.state.request_id
    )
    return JSONResponse(
        result.body,
        status_code=result.status,
        headers={"Idempotent-Replayed": "true"} if result.replayed else {},
    )


@router.get("/transfers")
def transfers(
    actor: Actor,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
    status: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    return history().page(
        actor["id"], limit=limit, cursor=cursor, status=status, since=since, until=until
    )


@router.get("/transfers/{transfer_id}")
def transfer(transfer_id: UUID, actor: Actor) -> dict[str, Any]:
    return history().transfer(actor["id"], transfer_id, admin=actor["role"] == "ADMIN")


@router.post("/admin/reconciliation-runs", status_code=201)
def reconciliation(
    request: Request, actor: Annotated[dict[str, Any], Depends(admin)]
) -> dict[str, Any]:
    return reconcile(engine(), persist=True, actor=actor["id"], request_id=request.state.request_id)


@router.get("/admin/reconciliation-runs/{run_id}")
def reconciliation_run(
    run_id: UUID, actor: Annotated[dict[str, Any], Depends(admin)]
) -> dict[str, Any]:
    from banking_lab.application.operations import get_reconciliation

    return get_reconciliation(engine(), run_id, actor["id"])
