"""FastAPI dependencies for verified authentication identity."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .jwt_verifier import AuthenticationError, JWTVerifier
from .models import AuthenticatedUser


bearer_scheme = HTTPBearer(auto_error=False)
_default_verifier = JWTVerifier()


def get_auth_verifier() -> JWTVerifier:
    return _default_verifier


def require_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    verifier: Annotated[JWTVerifier, Depends(get_auth_verifier)],
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verifier.verify_token(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


get_current_user = require_authenticated_user
