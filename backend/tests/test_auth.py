"""Unit tests for auth.py — password hashing and JWT utilities."""
import pytest
from datetime import timedelta, datetime, timezone

import auth


class TestPasswordHashing:
    def test_hash_password_returns_string(self):
        hashed = auth.hash_password("secret123")
        assert isinstance(hashed, str)
        assert hashed != "secret123"

    def test_hash_is_not_plaintext(self):
        hashed = auth.hash_password("mypassword")
        assert "mypassword" not in hashed

    def test_verify_correct_password(self):
        hashed = auth.hash_password("correct")
        assert auth.verify_password("correct", hashed) is True

    def test_verify_wrong_password(self):
        hashed = auth.hash_password("correct")
        assert auth.verify_password("wrong", hashed) is False

    def test_same_password_different_hashes(self):
        h1 = auth.hash_password("same")
        h2 = auth.hash_password("same")
        assert h1 != h2  # bcrypt salts are random


class TestTokenCreation:
    def test_create_access_token_returns_tuple(self):
        token, jti, expires_at = auth.create_access_token("alice", "admin")
        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert isinstance(expires_at, datetime)

    def test_create_refresh_token_returns_tuple(self):
        token, jti, expires_at = auth.create_refresh_token("bob", "viewer")
        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert isinstance(expires_at, datetime)

    def test_access_token_type_claim(self):
        token, _, _ = auth.create_access_token("alice", "admin")
        payload = auth.decode_token(token)
        assert payload["type"] == "access"

    def test_refresh_token_type_claim(self):
        token, _, _ = auth.create_refresh_token("alice", "admin")
        payload = auth.decode_token(token)
        assert payload["type"] == "refresh"

    def test_access_token_subject_claim(self):
        token, _, _ = auth.create_access_token("alice", "admin")
        payload = auth.decode_token(token)
        assert payload["sub"] == "alice"

    def test_access_token_role_claim(self):
        token, _, _ = auth.create_access_token("alice", "admin")
        payload = auth.decode_token(token)
        assert payload["role"] == "admin"

    def test_access_token_has_jti(self):
        token, jti, _ = auth.create_access_token("alice", "admin")
        payload = auth.decode_token(token)
        assert payload["jti"] == jti

    def test_access_token_expiry_is_future(self):
        _, _, expires_at = auth.create_access_token("alice", "admin")
        assert expires_at > datetime.now(timezone.utc)

    def test_refresh_token_expires_later_than_access(self):
        _, _, access_exp = auth.create_access_token("x", "viewer")
        _, _, refresh_exp = auth.create_refresh_token("x", "viewer")
        assert refresh_exp > access_exp

    def test_unique_jtis(self):
        _, jti1, _ = auth.create_access_token("x", "viewer")
        _, jti2, _ = auth.create_access_token("x", "viewer")
        assert jti1 != jti2


class TestDecodeToken:
    def test_decode_valid_token(self):
        token, _, _ = auth.create_access_token("charlie", "operador")
        payload = auth.decode_token(token)
        assert payload["sub"] == "charlie"

    def test_decode_invalid_token_raises_value_error(self):
        with pytest.raises(ValueError, match="Token invalido"):
            auth.decode_token("not.a.valid.token")

    def test_decode_tampered_token_raises_value_error(self):
        token, _, _ = auth.create_access_token("charlie", "operador")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(ValueError):
            auth.decode_token(tampered)

    def test_decode_expired_token_raises_value_error(self):
        token, _, _ = auth.create_token(
            subject="alice",
            role="viewer",
            token_type="access",
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(ValueError):
            auth.decode_token(token)
