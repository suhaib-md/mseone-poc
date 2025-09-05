import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "mseONE PoC API" in data["message"]


def test_healthz_endpoint():
    """Test health endpoint with mocked dependencies"""
    # Mock environment variables to avoid real Azure connections
    with patch.dict(os.environ, {
        'APP_ENV': 'local',
        'COSMOS_KEY': 'fake_key',
        'STORAGE_KEY': 'fake_storage_key'
    }):
        # Mock the repository and storage service classes
        with patch('api.repositories.projects.ProjectRepository') as mock_repo_class, \
             patch('api.services.storage.StorageService') as mock_storage_class:
            
            # Configure the mocks to return successful instances
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage
            
            # Make the health check request
            response = client.get("/healthz")
            assert response.status_code == 200
            
            data = response.json()
            assert "status" in data
            assert data["status"] in ["ok", "degraded"]
            assert "environment" in data