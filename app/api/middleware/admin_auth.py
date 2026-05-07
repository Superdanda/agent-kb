from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from werkzeug.security import generate_password_hash, check_password_hash
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.admin_user import AdminUser


ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


class TokenData(BaseModel):
    admin_id: int
    username: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return check_password_hash(hashed_password, plain_password)


def get_password_hash(password: str) -> str:
    return generate_password_hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminUser:
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        admin_id: int = payload.get("admin_id")
        username: str = payload.get("username")
        if admin_id is None or username is None:
            raise credentials_exception
        token_data = TokenData(admin_id=admin_id, username=username)
    except JWTError:
        raise credentials_exception

    admin = db.query(AdminUser).filter(AdminUser.id == token_data.admin_id).first()
    if admin is None:
        raise credentials_exception
    if admin.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin user is inactive",
        )

    return admin
