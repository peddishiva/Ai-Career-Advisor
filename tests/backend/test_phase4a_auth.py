"""Phase 4A authentication, profile API, and ownership regressions."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from api.v1.profile import ProfileResponse  # noqa: E402
from auth.dependencies import get_auth_verifier, require_authenticated_user  # noqa: E402
from auth.jwt_verifier import AuthenticationError, JWTVerifier  # noqa: E402
from config.auth_config import AuthConfig  # noqa: E402
from db.base import Base  # noqa: E402
from db.session import get_db  # noqa: E402
from main import app  # noqa: E402
from services.ownership_service import OwnershipError, ensure_user_scope  # noqa: E402


class TestPhase4AAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.config = AuthConfig(
            issuer="https://phase4a-test.supabase.co/auth/v1",
            audience="authenticated",
            jwks_url="https://phase4a-test.supabase.co/auth/v1/.well-known/jwks.json",
            algorithms=("RS256",),
        )
        cls.verifier = JWTVerifier(config=cls.config, signing_key_resolver=lambda _token: cls.private_key.public_key())

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.engine = create_engine(f"sqlite:///{Path(self.temp_dir.name) / 'profiles.db'}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

        def override_db():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_auth_verifier] = lambda: self.verifier
        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def token(self, user_id="user-one", private_key=None, **overrides):
        now = datetime.now(timezone.utc)
        claims = {
            "sub": user_id,
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "role": "authenticated",
        }
        claims.update(overrides)
        return jwt.encode(claims, private_key or self.private_key, algorithm="RS256")

    def test_valid_token_is_verified(self):
        user = self.verifier.verify_token(self.token())
        self.assertEqual("user-one", user.user_id)

    def test_missing_malformed_expired_issuer_audience_signature_and_algorithm_are_rejected(self):
        with self.assertRaises(AuthenticationError):
            self.verifier.verify_token("")
        with self.assertRaises(AuthenticationError):
            self.verifier.verify_token("not-a-jwt")
        with self.assertRaises(AuthenticationError):
            self.verifier.verify_token(self.token(exp=int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())))
        with self.assertRaises(AuthenticationError):
            self.verifier.verify_token(self.token(iss="https://wrong.example/auth/v1"))
        with self.assertRaises(AuthenticationError):
            self.verifier.verify_token(self.token(aud="wrong-audience"))
        with self.assertRaises(AuthenticationError):
            self.verifier.verify_token(self.token(private_key=self.other_private_key))
        hs256 = jwt.encode(
            {"sub": "user-one", "iss": self.config.issuer, "aud": self.config.audience, "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())},
            "not-a-production-secret-0123456789",
            algorithm="HS256",
        )
        with self.assertRaises(AuthenticationError):
            self.verifier.verify_token(hs256)

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/v1/profile")
        self.assertEqual(401, response.status_code)
        self.assertEqual("Bearer", response.headers.get("www-authenticate"))

    def test_profile_uses_verified_subject_and_ignores_client_user_id(self):
        response = self.client.get(
            "/api/v1/profile?user_id=someone-else",
            headers={"Authorization": f"Bearer {self.token('user-one')}", "Origin": "http://localhost:3000"},
        )
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual("user-one", body["user_id"])
        self.assertIsNone(body["display_name"])
        self.assertEqual("http://localhost:3000", response.headers.get("access-control-allow-origin"))
        self.assertEqual("true", response.headers.get("access-control-allow-credentials"))

    def test_disallowed_origin_does_not_receive_cors_access(self):
        response = self.client.options(
            "/api/v1/profile",
            headers={
                "Origin": "https://not-allowed.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        self.assertNotEqual("https://not-allowed.example", response.headers.get("access-control-allow-origin"))

    def test_allowed_origins_and_private_network_preflight(self):
        for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
            response = self.client.options(
                "/api/v1/profile",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "PATCH",
                    "Access-Control-Request-Headers": "authorization,content-type",
                    "Access-Control-Request-Private-Network": "true",
                },
            )
            self.assertEqual(200, response.status_code)
            self.assertEqual(origin, response.headers.get("access-control-allow-origin"))
            self.assertEqual("true", response.headers.get("access-control-allow-credentials"))
            self.assertEqual("true", response.headers.get("access-control-allow-private-network"))

    def test_profile_update_and_cross_user_scope(self):
        headers = {"Authorization": f"Bearer {self.token('user-one')}"}
        response = self.client.patch("/api/v1/profile", headers=headers, json={"display_name": "One"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("One", response.json()["display_name"])

        second_response = self.client.get("/api/v1/profile", headers={"Authorization": f"Bearer {self.token('user-two') }"})
        self.assertEqual(200, second_response.status_code)
        self.assertEqual("user-two", second_response.json()["user_id"])
        self.assertIsNone(second_response.json()["display_name"])

    def test_ownership_helper_rejects_other_user(self):
        user = self.verifier.verify_token(self.token("user-one"))
        ensure_user_scope(user, "user-one")
        with self.assertRaises(OwnershipError):
            ensure_user_scope(user, "user-two")


if __name__ == "__main__":
    unittest.main()
