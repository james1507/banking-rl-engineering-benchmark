import hashlib
import secrets
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import Connection, Engine, text

from banking_lab.application.transfers import audit, utc_now
from banking_lab.config import Settings
from banking_lab.domain.rules import DomainError

hasher = PasswordHasher()
DUMMY = hasher.hash(secrets.token_hex(32))


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, db: Engine, config: Settings) -> None:
        self.db, self.config = db, config

    def _issue(
        self, c: Connection, user: dict[str, Any], family: UUID | None = None
    ) -> dict[str, Any]:
        now, token, session_id = utc_now(), secrets.token_urlsafe(48), uuid4()
        c.execute(
            text(
                "INSERT INTO refresh_sessions(id,user_id,token_hash,family_id,issued_at,expires_at) VALUES(:id,:user,:hash,:family,:now,:expires)"
            ),
            {
                "id": session_id,
                "user": user["id"],
                "hash": digest(token),
                "family": family or uuid4(),
                "now": now,
                "expires": now + timedelta(seconds=self.config.refresh_seconds),
            },
        )
        access = jwt.encode(
            {
                "sub": str(user["id"]),
                "iss": self.config.jwt_issuer,
                "aud": self.config.jwt_audience,
                "iat": now,
                "exp": now + timedelta(seconds=self.config.access_seconds),
                "jti": str(uuid4()),
            },
            self.config.jwt_secret,
            algorithm="HS256",
        )
        return {
            "access_token": access,
            "refresh_token": token,
            "token_type": "bearer",
            "expires_in": self.config.access_seconds,
            "session_id": str(session_id),
        }

    def login(self, email: str, password: str, request_id: str) -> dict[str, Any]:
        normalized = email.strip().lower()
        with self.db.begin() as c:
            bucket = c.execute(
                text("""INSERT INTO login_buckets(bucket,attempts,reset_at) VALUES(:key,1,:reset)
                ON CONFLICT(bucket) DO UPDATE SET attempts=CASE WHEN login_buckets.reset_at<:now THEN 1 ELSE login_buckets.attempts+1 END,
                reset_at=CASE WHEN login_buckets.reset_at<:now THEN :reset ELSE login_buckets.reset_at END RETURNING attempts"""),
                {
                    "key": digest(normalized),
                    "now": utc_now(),
                    "reset": utc_now() + timedelta(minutes=5),
                },
            ).scalar_one()
        if bucket > 10:
            raise DomainError("AUTH_THROTTLED", "Try again later.", 429)
        with self.db.begin() as c:
            row = (
                c.execute(
                    text("SELECT * FROM users WHERE email=:email FOR UPDATE"), {"email": normalized}
                )
                .mappings()
                .one_or_none()
            )
            try:
                valid: bool = hasher.verify(row["password_hash"] if row else DUMMY, password)
            except VerificationError:
                valid = False
            if not row or not valid or row["status"] != "ACTIVE":
                audit(c, None, "LOGIN", None, "DENIED", request_id)
                result = None
            else:
                result = self._issue(c, dict(row))
                audit(c, row["id"], "LOGIN", row["id"], "SUCCESS", request_id)
        if result is None:
            raise DomainError("AUTH_INVALID", "Invalid credentials.", 401)
        return result

    def refresh(self, token: str, request_id: str) -> dict[str, Any]:
        result = None
        with self.db.begin() as c:
            initial = c.execute(
                text("SELECT user_id FROM refresh_sessions WHERE token_hash=:hash"),
                {"hash": digest(token)},
            ).scalar_one_or_none()
            if initial is None:
                raise DomainError("AUTH_INVALID", "Invalid session.", 401)
            user = dict(
                c.execute(text("SELECT * FROM users WHERE id=:id FOR UPDATE"), {"id": initial})
                .mappings()
                .one()
            )
            row = (
                c.execute(
                    text("SELECT * FROM refresh_sessions WHERE token_hash=:hash FOR UPDATE"),
                    {"hash": digest(token)},
                )
                .mappings()
                .one()
            )
            if row["rotated_at"] is not None or row["revoked_at"] is not None:
                c.execute(
                    text(
                        "UPDATE refresh_sessions SET revoked_at=coalesce(revoked_at,:now) WHERE family_id=:family"
                    ),
                    {"now": utc_now(), "family": row["family_id"]},
                )
                audit(c, initial, "REFRESH_REPLAY", row["id"], "FAMILY_REVOKED", request_id)
            elif row["expires_at"] > utc_now() and user["status"] == "ACTIVE":
                result = self._issue(c, user, row["family_id"])
                c.execute(
                    text(
                        "UPDATE refresh_sessions SET rotated_at=:now,revoked_at=:now,replaced_by=:next WHERE id=:id"
                    ),
                    {"now": utc_now(), "next": UUID(result["session_id"]), "id": row["id"]},
                )
                audit(c, initial, "REFRESH", row["id"], "ROTATED", request_id)
        if result is None:
            raise DomainError("AUTH_INVALID", "Invalid session.", 401)
        return result

    def logout(self, token: str, request_id: str) -> None:
        with self.db.begin() as c:
            row = (
                c.execute(
                    text("SELECT user_id,family_id FROM refresh_sessions WHERE token_hash=:hash"),
                    {"hash": digest(token)},
                )
                .mappings()
                .one_or_none()
            )
            if row:
                c.execute(
                    text("SELECT id FROM users WHERE id=:id FOR UPDATE"), {"id": row["user_id"]}
                )
                c.execute(
                    text(
                        "UPDATE refresh_sessions SET revoked_at=coalesce(revoked_at,:now) WHERE family_id=:family"
                    ),
                    {"now": utc_now(), "family": row["family_id"]},
                )
                audit(c, row["user_id"], "LOGOUT", None, "REVOKED", request_id)

    def authenticate(self, token: str) -> dict[str, Any]:
        try:
            claims = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=["HS256"],
                issuer=self.config.jwt_issuer,
                audience=self.config.jwt_audience,
                options={"require": ["sub", "exp", "iat", "iss", "aud", "jti"]},
            )
            user_id = UUID(claims["sub"])
        except jwt.ExpiredSignatureError as exc:
            raise DomainError("AUTH_EXPIRED", "Access token expired.", 401) from exc
        except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
            raise DomainError("AUTH_INVALID", "Invalid access token.", 401) from exc
        with self.db.connect() as c:
            row = (
                c.execute(
                    text("SELECT id,email,role,status FROM users WHERE id=:id AND status='ACTIVE'"),
                    {"id": user_id},
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise DomainError("AUTH_INVALID", "Active user required.", 401)
        return dict(row)
