"""
Tests for the authentication endpoints.
"""

import pytest


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser", "email": "new@example.com", "password": "strongpass1"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "newuser"
        assert data["user"]["role"] == "user"

    def test_register_duplicate_email(self, client, registered_user):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "other", "email": "test@example.com", "password": "password123"},
        )
        assert resp.status_code == 409

    def test_register_duplicate_username(self, client, registered_user):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "testuser", "email": "other@example.com", "password": "password123"},
        )
        assert resp.status_code == 409

    def test_register_short_password(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "abc", "email": "abc@example.com", "password": "short"},
        )
        assert resp.status_code == 422

    def test_register_invalid_username(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "ab", "email": "short@example.com", "password": "password123"},
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client, registered_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, registered_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert resp.status_code == 401


class TestMe:
    def test_me_authenticated(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 403  # HTTPBearer returns 403 when no token


class TestRefresh:
    def test_refresh_success(self, client, registered_user):
        refresh_token = registered_user["refresh_token"]
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_invalid_token(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401
