"""Cryptographic JWT verification for Supabase Auth access tokens."""

from typing import Any, Callable, Optional

import jwt
from jwt import InvalidTokenError, PyJWKClient

from config.auth_config import AuthConfig, load_auth_config

from .models import AuthenticatedUser


class AuthenticationError(ValueError):
    """Safe authentication failure that is suitable for a 401 response."""


class JWTVerifier:
    """Verify issuer, audience, expiry, subject, and signing algorithm."""

    def __init__(
        self,
        config: Optional[AuthConfig] = None,
        jwks_client: Any = None,
        signing_key_resolver: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.config = config or load_auth_config()
        self._jwks_client = jwks_client
        self._signing_key_resolver = signing_key_resolver

    def verify_token(self, token: str) -> AuthenticatedUser:
        if not isinstance(token, str) or not token.strip():
            raise AuthenticationError("missing bearer token")
        if not self.config.is_configured:
            raise AuthenticationError("authentication is not configured")

        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if not isinstance(algorithm, str) or algorithm.upper() == "NONE":
                raise AuthenticationError("unsupported signing algorithm")
            algorithm = algorithm.upper()
            if algorithm not in self.config.algorithms:
                raise AuthenticationError("unsupported signing algorithm")

            signing_key = self._get_signing_key(token, algorithm)
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=[algorithm],
                audience=self.config.audience,
                issuer=self.config.issuer,
                options={"require": ["exp", "sub", "iss", "aud"]},
            )
            return AuthenticatedUser.from_claims(claims)
        except AuthenticationError:
            raise
        except (InvalidTokenError, ValueError, TypeError, KeyError) as exc:
            raise AuthenticationError("invalid bearer token") from exc
        except Exception as exc:
            # Network/JWKS/provider failures must never expose internal details.
            raise AuthenticationError("unable to verify bearer token") from exc

    def _get_signing_key(self, token: str, algorithm: str) -> Any:
        if algorithm == "HS256":
            if not self.config.jwt_secret:
                raise AuthenticationError("symmetric token verification is not configured")
            return self.config.jwt_secret

        if self._signing_key_resolver:
            resolved = self._signing_key_resolver(token)
            return getattr(resolved, "key", resolved)

        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(self.config.jwks_url, cache_jwk_set=True, timeout=10)
        resolved = self._jwks_client.get_signing_key_from_jwt(token)
        return getattr(resolved, "key", resolved)
