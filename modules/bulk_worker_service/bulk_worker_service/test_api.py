import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from bulk_worker_service.app import app
from bulk_worker_service.container import reset_container
from bulk_worker_service.domain import StartRequest, StartOptions


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup clean test environment for each test."""
    reset_container()
    yield
    reset_container()


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert response.json() == {"ok": True}


class TestJobManagement:
    """Test job management endpoints."""
    
    def test_list_jobs_empty(self, client):
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_job_status_not_found(self, client):
        response = client.get("/api/v1/jobs/non-existent-job/status")
        
        assert response.status_code == 500  # Will be 404 with proper error handling
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_stop_job_success(self, mock_orchestrator, client):
        mock_orchestrator.stop_job.return_value = asyncio.create_task(asyncio.coroutine(lambda: True)())
        
        response = client.post("/api/v1/jobs/test-job/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job"
        assert data["stopped"] is True
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_delete_job_success(self, mock_orchestrator, client):
        mock_orchestrator.delete_job.return_value = asyncio.create_task(asyncio.coroutine(lambda: True)())
        
        response = client.delete("/api/v1/jobs/test-job")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job"
        assert data["deleted"] is True


class TestTaskStartEndpoints:
    """Test task start endpoints."""
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_start_bulk_login(self, mock_orchestrator, client):
        mock_orchestrator.start_bulk_login.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: "test-job-id")()
        )
        
        response = client.post("/api/v1/bulk-login/start?task_id=123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job-id"
        assert data["accepted"] is True
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_start_warmup(self, mock_orchestrator, client):
        mock_orchestrator.start_warmup.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: "warmup-job-id")()
        )
        
        response = client.post("/api/v1/warmup/start?task_id=456")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "warmup-job-id"
        assert data["accepted"] is True
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_start_avatar(self, mock_orchestrator, client):
        mock_orchestrator.start_avatar.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: "avatar-job-id")()
        )
        
        response = client.post("/api/v1/avatar/start?task_id=789")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "avatar-job-id"
        assert data["accepted"] is True
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_start_bio(self, mock_orchestrator, client):
        mock_orchestrator.start_bio.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: "bio-job-id")()
        )
        
        response = client.post("/api/v1/bio/start?task_id=101")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "bio-job-id"
        assert data["accepted"] is True
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_start_follow(self, mock_orchestrator, client):
        mock_orchestrator.start_follow.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: "follow-job-id")()
        )
        
        response = client.post("/api/v1/follow/start?task_id=202")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "follow-job-id"
        assert data["accepted"] is True
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_start_proxy_diagnostics(self, mock_orchestrator, client):
        mock_orchestrator.start_proxy_diagnostics.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: "proxy-job-id")()
        )
        
        response = client.post("/api/v1/proxy-diagnostics/start?task_id=303")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "proxy-job-id"
        assert data["accepted"] is True
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_start_media_uniq(self, mock_orchestrator, client):
        mock_orchestrator.start_media_uniq.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: "media-job-id")()
        )
        
        response = client.post("/api/v1/media-uniq/start?task_id=404")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "media-job-id"
        assert data["accepted"] is True
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_start_cookie_robot(self, mock_orchestrator, client):
        mock_orchestrator.start_cookie_robot.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: "cookie-job-id")()
        )
        
        response = client.post("/api/v1/cookie-robot/start?task_id=505")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "cookie-job-id"
        assert data["accepted"] is True


class TestErrorHandling:
    """Test error handling in API endpoints."""
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_start_task_with_worker_service_error(self, mock_orchestrator, client):
        from bulk_worker_service.exceptions import InvalidTaskTypeError
        
        async def raise_error():
            raise InvalidTaskTypeError("Invalid task type")
        
        mock_orchestrator.start_warmup.return_value = asyncio.create_task(raise_error())
        
        response = client.post("/api/v1/warmup/start?task_id=123")
        
        assert response.status_code == 400
        assert "Invalid task type" in response.json()["detail"]
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_start_task_with_generic_error(self, mock_orchestrator, client):
        async def raise_error():
            raise Exception("Generic error")
        
        mock_orchestrator.start_avatar.return_value = asyncio.create_task(raise_error())
        
        response = client.post("/api/v1/avatar/start?task_id=123")
        
        assert response.status_code == 500
        assert "Generic error" in response.json()["detail"]
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_stop_job_not_found(self, mock_orchestrator, client):
        from bulk_worker_service.exceptions import JobNotFoundError
        
        async def raise_error():
            raise JobNotFoundError("Job not found")
        
        mock_orchestrator.stop_job.return_value = asyncio.create_task(raise_error())
        
        response = client.post("/api/v1/jobs/non-existent/stop")
        
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]


class TestMetricsEndpoint:
    """Test metrics endpoint."""
    
    @patch('bulk_worker_service.app._orchestrator_v2')
    def test_get_metrics(self, mock_orchestrator, client):
        expected_metrics = {
            "total_jobs": 5,
            "completed_jobs": 3,
            "failed_jobs": 1,
            "running_jobs_count": 1,
            "jobs_by_type": {"bulk_upload": 2, "warmup": 3}
        }
        
        mock_orchestrator.get_metrics.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: expected_metrics)()
        )
        
        response = client.get("/api/v1/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 5
        assert data["completed_jobs"] == 3
        assert data["running_jobs_count"] == 1


class TestBulkTasksBackwardCompatibility:
    """Test backward compatibility with legacy bulk tasks endpoint."""
    
    @patch('bulk_worker_service.app._orchestrator')
    def test_start_bulk_task_pull_mode(self, mock_orchestrator, client):
        mock_orchestrator.start_pull.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: "bulk-job-id")()
        )
        
        request_data = {
            "mode": "pull",
            "task_id": 123,
            "options": {"concurrency": 2}
        }
        
        response = client.post("/api/v1/bulk-tasks/start", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "bulk-job-id"
        assert data["accepted"] is True
    
    def test_start_bulk_task_pull_mode_missing_task_id(self, client):
        request_data = {
            "mode": "pull",
            "options": {"concurrency": 2}
        }
        
        response = client.post("/api/v1/bulk-tasks/start", json=request_data)
        
        assert response.status_code == 400
        assert "task_id is required" in response.json()["detail"]
    
    @patch('bulk_worker_service.app._orchestrator')
    def test_start_bulk_task_push_mode(self, mock_orchestrator, client):
        mock_orchestrator.start.return_value = asyncio.create_task(
            asyncio.coroutine(lambda: "push-job-id")()
        )
        
        request_data = {
            "mode": "push",
            "aggregate": {
                "id": 123,
                "accounts": [],
                "videos": []
            },
            "options": {"concurrency": 2}
        }
        
        response = client.post("/api/v1/bulk-tasks/start", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "push-job-id"
        assert data["accepted"] is True
    
    def test_start_bulk_task_push_mode_missing_aggregate(self, client):
        request_data = {
            "mode": "push",
            "options": {"concurrency": 2}
        }
        
        response = client.post("/api/v1/bulk-tasks/start", json=request_data)
        
        assert response.status_code == 400
        assert "aggregate is required" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])