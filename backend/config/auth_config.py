"""Environment-backed Supabase Auth verification configuration."""

from dataclasses import dataclass, field
import os
from typing import Optional, Tuple
from urllib.parse import urlparse


SUPPORTED_JWT_ALGORITHMS = frozenset({"ES256", "RS256", "HS256"})


@dataclass(frozen=True)
class AuthConfig:
    supabase_url: str = ""
    issuer: str = ""
    audience: str = "authenticated"
    jwks_url: str = ""
    algorithms: Tuple[str, ...] = ("ES256", "RS256")
    jwt_secret: Optional[str] = field(default=None, repr=False)

    @property
    def is_configured(self) -> bool:
        asymmetric_configured = bool(self.issuer and self.jwks_url)
        symmetric_configured = "HS256" in self.algorithms and bool(self.jwt_secret)
        issuer_url = urlparse(self.issuer)
        jwks_url = urlparse(self.jwks_url)
        valid_urls = all(parsed.scheme in {"http", "https"} and parsed.netloc for parsed in (issuer_url, jwks_url))
        return bool(valid_urls and self.audience and (asymmetric_configured or symmetric_configured))


def load_auth_config() -> AuthConfig:
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    configured_issuer = os.getenv("SUPABASE_JWT_ISSUER", "").strip().rstrip("/")
    issuer = configured_issuer or (f"{supabase_url}/auth/v1" if supabase_url else "")
    jwks_url = os.getenv("SUPABASE_JWKS_URL", "").strip() or (
        f"{issuer}/.well-known/jwks.json" if issuer else ""
    )
    raw_algorithms = os.getenv("SUPABASE_JWT_ALGORITHMS", "ES256,RS256")
    algorithms = tuple(
        algorithm.strip().upper()
        for algorithm in raw_algorithms.split(",")
        if algorithm.strip() and algorithm.strip().upper() in SUPPORTED_JWT_ALGORITHMS
    )
    if not algorithms:
        algorithms = ("ES256", "RS256")

    # Reject obviously malformed public configuration early without logging values.
    parsed_url = urlparse(supabase_url) if supabase_url else None
    if parsed_url and parsed_url.scheme not in {"http", "https"}:
        supabase_url = ""

    return AuthConfig(
        supabase_url=supabase_url,
        issuer=issuer,
        audience=os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated").strip() or "authenticated",
        jwks_url=jwks_url,
        algorithms=algorithms,
        jwt_secret=os.getenv("SUPABASE_JWT_SECRET") or None,
    )
