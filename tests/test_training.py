"""
Tests for the training and admin endpoints.
"""

from unittest.mock import patch

import pytest


class TestTrainingEndpoints:
    def test_start_training_requires_admin(self, client, auth_headers):
        """Regular users cannot start training."""
        resp = client.post(
            "/api/v1/training/start",
            json={"backbone": "cnn", "epochs": 5, "batch_size": 16},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_start_training_as_admin(self, client, admin_headers):
        """Admin can start a training job."""
        with patch("backend.routers.training._run_training_job"):
            resp = client.post(
                "/api/v1/training/start",
                json={"backbone": "cnn", "epochs": 5, "batch_size": 16},
                headers=admin_headers,
            )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        assert data["backbone"] == "cnn"

    def test_start_training_invalid_backbone(self, client, admin_headers):
        resp = client.post(
            "/api/v1/training/start",
            json={"backbone": "resnet50", "epochs": 5, "batch_size": 16},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_get_training_status(self, client, admin_headers, auth_headers):
        with patch("backend.routers.training._run_training_job"):
            start_resp = client.post(
                "/api/v1/training/start",
                json={"backbone": "cnn", "epochs": 5, "batch_size": 16},
                headers=admin_headers,
            )
        job_id = start_resp.json()["job_id"]

        resp = client.get(f"/api/v1/training/status/{job_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["job_id"] == job_id

    def test_get_training_status_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/training/status/nonexistent-id", headers=auth_headers)
        assert resp.status_code == 404

    def test_training_history(self, client, auth_headers):
        resp = client.get("/api/v1/training/history", headers=auth_headers)
        assert resp.status_code == 200
        assert "jobs" in resp.json()


class TestAdminEndpoints:
    def test_stats_requires_admin(self, client, auth_headers):
        resp = client.get("/api/v1/admin/stats", headers=auth_headers)
        assert resp.status_code == 403

    def test_stats_as_admin(self, client, admin_headers):
        resp = client.get("/api/v1/admin/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert "total_predictions" in data

    def test_list_users_as_admin(self, client, admin_headers):
        resp = client.get("/api/v1/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        assert "users" in resp.json()
        assert "total" in resp.json()

    def test_list_users_requires_admin(self, client, auth_headers):
        resp = client.get("/api/v1/admin/users", headers=auth_headers)
        assert resp.status_code == 403


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "model_loaded" in data
