import json
import re
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from opentelemetry.propagate import extract, inject
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from banking_lab.api.routes import router
from banking_lab.api.routes_operations import router as operations_router
from banking_lab.config import settings
from banking_lab.domain.rules import DomainError, error_body
from banking_lab.infrastructure.db import engine, ready, transient_database_error
from banking_lab.observability.telemetry import LATENCY, REQUESTS, logger
from banking_lab.observability.tracing import tracer

app = FastAPI(
    title="Banking RL Engineering Lab",
    version="0.1.0",
    docs_url="/docs" if settings().app_env in {"local", "test"} else None,
    redoc_url=None,
)
app.include_router(router)

app.include_router(operations_router)


def unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


async def context(request: Request, call_next: object) -> Response:
    from collections.abc import Awaitable, Callable
    from typing import cast

    start = time.monotonic()
    incoming = request.headers.get("x-request-id", "")
    request.state.request_id = (
        incoming if re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", incoming) else str(uuid4())
    )
    fields = {"request_id": request.state.request_id, "operation": "http"}
    logger.info("request.start", extra={"safe_fields": fields})
    try:
        if request.method in {"POST", "PUT", "PATCH"}:
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 65536:
                    raise DomainError("VALIDATION_ERROR", "Request exceeds 64 KiB.", 413)
            request._body = bytes(body)
            if body and "application/json" in request.headers.get("content-type", ""):
                try:
                    json.loads(body, object_pairs_hook=unique_keys)
                except (ValueError, UnicodeDecodeError, RecursionError) as exc:
                    raise DomainError(
                        "VALIDATION_ERROR", "Invalid JSON or duplicate keys.", 422
                    ) from exc
        response = await cast(Callable[[Request], Awaitable[Response]], call_next)(request)
    except DomainError as exc:
        response = JSONResponse(
            error_body(exc.code, exc.message, request.state.request_id), status_code=exc.status
        )
    except Exception as exc:
        logger.error(
            "request.failure",
            extra={"safe_fields": {**fields, "exception_type": type(exc).__name__}},
        )
        response = JSONResponse(
            error_body("INTERNAL_ERROR", "Unexpected server error.", request.state.request_id),
            status_code=500,
        )
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "no-store"
    route = getattr(request.scope.get("route"), "path", "unmatched")
    method = (
        request.method
        if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
        else "OTHER"
    )
    elapsed = time.monotonic() - start
    REQUESTS.labels(route, method, str(response.status_code // 100) + "xx").inc()
    LATENCY.labels(route).observe(elapsed)
    logger.info(
        "request.end",
        extra={
            "safe_fields": {
                **fields,
                "route": route,
                "duration_ms": round(elapsed * 1000, 2),
                "status": response.status_code,
            }
        },
    )
    return response


@app.middleware("http")
async def traced_request(request: Request, call_next: object) -> Response:
    with tracer.start_as_current_span(
        "http.request", context=extract(dict(request.headers))
    ) as span:
        response = await context(request, call_next)
        span.set_attribute("http.response.status_code", response.status_code)
        span.set_attribute("http.route", getattr(request.scope.get("route"), "path", "unmatched"))
        carrier: dict[str, str] = {}
        inject(carrier)
        response.headers.update(carrier)
        return response


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        error_body(exc.code, exc.message, request.state.request_id),
        status_code=exc.status,
        headers={"Retry-After": "1"} if exc.status in {429, 503} else {},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        error_body("VALIDATION_ERROR", "Invalid request fields.", request.state.request_id),
        status_code=422,
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        error_body(
            "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "VALIDATION_ERROR",
            "Request unavailable.",
            request.state.request_id,
        ),
        status_code=exc.status_code,
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    retryable = transient_database_error(exc)
    return JSONResponse(
        error_body(
            "TRANSIENT_DATABASE_ERROR" if retryable else "INTERNAL_ERROR",
            "Database unavailable; retry with the same key."
            if retryable
            else "Unexpected server error.",
            request.state.request_id,
        ),
        status_code=503 if retryable else 500,
        headers={"Retry-After": "1"} if retryable else {},
    )


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> JSONResponse:
    try:
        healthy = ready(engine())
    except SQLAlchemyError:
        healthy = False
    return JSONResponse(
        {"status": "ready" if healthy else "unavailable", "migration": "0002"},
        status_code=200 if healthy else 503,
    )


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
