from datetime import datetime, timezone, timedelta

from fastapi import Request, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_signature, sha256_bytes, decrypt_secret
from app.core.exceptions import AuthenticationError, SignatureError, NonceExpiredError
from app.models.agent import Agent, AgentStatus
from app.models.credential import AgentCredential
from app.models.api_nonce import ApiNonce
from app.models.security_event_log import SecurityEventLog


REQUIRED_HEADERS = [
    "x-agent-id",
    "x-access-key",
    "x-timestamp",
    "x-nonce",
    "x-content-sha256",
    "x-signature",
]


async def compute_request_body_sha256(request: Request) -> str:
    body = await request.body()
    if body:
        return sha256_bytes(body)
    return sha256_bytes(b"")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _log_security_event(
    db: Session,
    event_type: str,
    agent_id: str | None,
    detail: str,
    source_ip: str,
) -> None:
    try:
        log = SecurityEventLog(
            event_type=event_type,
            agent_id=agent_id,
            detail=detail,
            source_ip=source_ip,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()  # 安全日志失败不影响主流程


async def get_current_agent(
    request: Request,
    db: Session = Depends(get_db),
) -> str:
    source_ip = _get_client_ip(request)
    missing_headers = [h for h in REQUIRED_HEADERS if h not in request.headers]
    if missing_headers:
        _log_security_event(
            db=db,
            event_type="AUTH_FAILED_MISSING_HEADERS",
            agent_id=None,
            detail=f"Missing headers: {missing_headers}",
            source_ip=source_ip,
        )
        raise AuthenticationError(f"Missing required headers: {missing_headers}")

    agent_id = request.headers["x-agent-id"]
    access_key = request.headers["x-access-key"]
    timestamp = request.headers["x-timestamp"]
    nonce = request.headers["x-nonce"]
    content_sha256 = request.headers["x-content-sha256"]
    signature = request.headers["x-signature"]

    try:
        request_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    except (ValueError, OSError):
        _log_security_event(
            db=db,
            event_type="AUTH_FAILED_TIMESTAMP",
            agent_id=agent_id,
            detail="Invalid timestamp format",
            source_ip=source_ip,
        )
        raise AuthenticationError("Invalid timestamp format")

    time_window = timedelta(seconds=settings.HMAC_TIME_WINDOW_SECONDS)
    now = datetime.now(timezone.utc)
    if abs((now - request_time).total_seconds()) > settings.HMAC_TIME_WINDOW_SECONDS:
        _log_security_event(
            db=db,
            event_type="AUTH_FAILED_TIMESTAMP",
            agent_id=agent_id,
            detail=f"Timestamp outside window: {timestamp}",
            source_ip=source_ip,
        )
        raise AuthenticationError("Request timestamp is outside the allowed time window")

    existing_nonce = db.query(ApiNonce).filter(
        ApiNonce.nonce == nonce,
        ApiNonce.expires_at > now,
    ).first()
    if existing_nonce:
        _log_security_event(
            db=db,
            event_type="AUTH_FAILED_NONCE_REUSED",
            agent_id=agent_id,
            detail=f"Nonce reused: {nonce}",
            source_ip=source_ip,
        )
        raise NonceExpiredError("Nonce has already been used")

    credential = (
        db.query(AgentCredential)
        .join(Agent)
        .filter(
            AgentCredential.access_key == access_key,
            Agent.id == agent_id,
            Agent.status == AgentStatus.ACTIVE,
            AgentCredential.status == "ACTIVE",
        )
        .first()
    )
    if not credential:
        _log_security_event(
            db=db,
            event_type="AUTH_FAILED_INVALID_CREDENTIALS",
            agent_id=agent_id,
            detail="Invalid access key or agent not active",
            source_ip=source_ip,
        )
        raise AuthenticationError("Invalid credentials")

    secret_key = decrypt_secret(credential.secret_key_encrypted)
    query = request.url.query or ""
    path = request.url.path

    body_for_signing = await compute_request_body_sha256(request)
    if body_for_signing != content_sha256:
        _log_security_event(
            db=db,
            event_type="AUTH_FAILED_CONTENT_MISMATCH",
            agent_id=agent_id,
            detail="Content SHA256 mismatch",
            source_ip=source_ip,
        )
        raise AuthenticationError("Content SHA256 does not match")

    if not verify_signature(
        secret_key=secret_key,
        method=request.method,
        path=path,
        query=query,
        timestamp=timestamp,
        nonce=nonce,
        content_sha256=content_sha256,
        signature=signature,
    ):
        _log_security_event(
            db=db,
            event_type="AUTH_FAILED_SIGNATURE",
            agent_id=agent_id,
            detail="Signature verification failed",
            source_ip=source_ip,
        )
        raise SignatureError("Signature verification failed")

    new_nonce = ApiNonce(
        agent_id=credential.agent_id,
        nonce=nonce,
        expires_at=now + time_window,
    )
    db.add(new_nonce)
    db.commit()

    credential.last_used_at = now
    db.commit()

    return agent_id
