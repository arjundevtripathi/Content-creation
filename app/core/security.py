import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.db import User, get_db

bearer = HTTPBearer(auto_error=False)
ALGO = "HS256"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.access_token_minutes)
    return jwt.encode({"sub": str(user_id), "exp": exp}, s.secret_key, algorithm=ALGO)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing token")
    if creds is None:
        raise err
    try:
        payload = jwt.decode(creds.credentials, get_settings().secret_key, algorithms=[ALGO])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise err
    if user is None:
        raise err
    return user
