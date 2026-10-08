"""Verified authentication identity models."""

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identity derived only from a cryptographically verified token."""

    user_id: str
    claims: Mapping[str, Any]
    role: Optional[str] = None

    @classmethod
    def from_claims(cls, claims: Mapping[str, Any]) -> "AuthenticatedUser":
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError("verified token is missing a valid subject")
        role = claims.get("role")
        return cls(
            user_id=subject.strip(),
            claims=dict(claims),
            role=role.strip() if isinstance(role, str) and role.strip() else None,
        )
