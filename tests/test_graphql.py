import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch, MagicMock
import os

from api.auth import LOCAL_DEV_TOKEN
from api.main import app
from api.repositories.projects import ProjectStatus

client = TestClient(app)

# Helper function to get auth headers
def get_auth_headers():
    return {"Authorization": f"Bearer {LOCAL_DEV_TOKEN}"}


class TestHealthEndpoint:
    def test_healthz(self):
        """Test health endpoint"""
        # Mock the environment variables and dependencies to avoid real connections
        with patch.dict(os.environ, {
            'APP_ENV': 'local',
            'COSMOS_KEY': 'fake_key',
            'STORAGE_KEY': 'fake_storage_key'
        }):
            with patch('api.repositories.projects.ProjectRepository') as mock_repo, \
                 patch('api.services.storage.StorageService') as mock_storage:
                
                # Configure mocks
                mock_repo.return_value = MagicMock()
                mock_storage.return_value = MagicMock()
                
                r = client.get("/healthz")
                assert r.status_code == 200
                response_data = r.json()
                assert "status" in response_data
                # The actual response contains more fields than just {"status": "ok"}
                assert response_data["status"] in ["ok", "degraded"]


class TestProjectQueries:
    def test_graphql_requires_auth(self):
        """Test that GraphQL requires authentication"""
        q = {"query": "{ project(id: \"1\") { id name status } }"}
        r = client.post("/graphql", json=q)  # no auth
        assert r.status_code == 401

    @patch('api.repositories.projects.ProjectRepository')
    def test_project_query_not_found(self, mock_repo_class):
        """Test querying non-existent project"""
        # Mock the repository
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None
        mock_repo_class.return_value = mock_repo
        
        # Mock storage service to avoid real storage calls
        with patch('api.services.storage.StorageService') as mock_storage:
            mock_storage.return_value.save_result.return_value = "fake-blob-name"
            
            q = {"query": "{ project(id: \"nonexistent\") { id name status } }"}
            r = client.post("/graphql", json=q, headers=get_auth_headers())
            assert r.status_code == 200
            data = r.json()
            assert data["data"]["project"] is None

    @patch('api.repositories.projects.ProjectRepository')
    def test_projects_list_empty(self, mock_repo_class):
        """Test listing projects when none exist or filters return empty"""
        # Mock the repository
        mock_repo = MagicMock()
        mock_repo.list_projects.return_value = ([], False)  # empty list, no next page
        mock_repo.get_project_count.return_value = 0
        mock_repo_class.return_value = mock_repo
        
        # Mock storage service
        with patch('api.services.storage.StorageService') as mock_storage:
            mock_storage.return_value.save_result.return_value = "fake-blob-name"
            
            q = {
                "query": """
                query($first: Int!) {
                    projects(first: $first) {
                        totalCount
                        edges { cursor node { id name status } }
                        pageInfo { hasNextPage endCursor }
                    }
                }
                """,
                "variables": {"first": 10}
            }
            r = client.post("/graphql", json=q, headers=get_auth_headers())
            assert r.status_code == 200
            data = r.json()["data"]["projects"]
            assert data["totalCount"] == 0
            assert isinstance(data["edges"], list)
            assert "pageInfo" in data

    @patch('api.repositories.projects.ProjectRepository')
    def test_project_summary(self, mock_repo_class):
        """Test project summary query"""
        # Mock the repository
        mock_repo = MagicMock()
        mock_repo.get_projects_by_status_summary.return_value = {
            "active": 2,
            "archived": 1,
            "draft": 3,
            "completed": 1
        }
        mock_repo_class.return_value = mock_repo
        
        # Mock storage service
        with patch('api.services.storage.StorageService') as mock_storage:
            mock_storage.return_value.save_result.return_value = "fake-blob-name"
            
            q = {
                "query": """
                {
                    projectSummary {
                        totalProjects
                        activeProjects
                        archivedProjects
                        draftProjects
                        completedProjects
                    }
                }
                """
            }
            r = client.post("/graphql", json=q, headers=get_auth_headers())
            assert r.status_code == 200
            data = r.json()["data"]["projectSummary"]
            assert "totalProjects" in data
            assert data["totalProjects"] == 7  # sum of all statuses


class TestProjectMutations:
    @patch('api.repositories.projects.ProjectRepository')
    def test_create_project_minimal(self, mock_repo_class):
        """Test creating project with minimal required fields"""
        from api.repositories.projects import ProjectRecord
        
        # Create a mock project record
        mock_project = ProjectRecord(
            id="proj_123",
            name="Test Project Minimal",
            description=None,
            status=ProjectStatus.DRAFT,
            owner_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=[],
            budget=None,
            due_date=None
        )
        
        # Mock the repository
        mock_repo = MagicMock()
        mock_repo.create_project.return_value = mock_project
        mock_repo_class.return_value = mock_repo
        
        # Mock storage service
        with patch('api.services.storage.StorageService') as mock_storage:
            mock_storage.return_value.save_result.return_value = "fake-blob-name"
            
            mutation = {
                "query": """
                mutation($input: CreateProjectInput!) {
                    createProject(input: $input) {
                        success
                        error
                        project {
                            id
                            name
                            status
                            description
                            tags
                            createdAt
                            updatedAt
                        }
                    }
                }
                """,
                "variables": {
                    "input": {
                        "name": "Test Project Minimal"
                    }
                }
            }
            
            r = client.post("/graphql", json=mutation, headers=get_auth_headers())
            assert r.status_code == 200
            
            data = r.json()["data"]["createProject"]
            assert data["success"] is True
            assert data["error"] is None
            assert data["project"] is not None
            
            project = data["project"]
            assert project["name"] == "Test Project Minimal"
            assert project["status"] == "DRAFT"  # Default status
            assert project["description"] is None
            assert project["tags"] == []

    @patch('api.repositories.projects.ProjectRepository')
    def test_create_project_validation_error(self, mock_repo_class):
        """Test creating project with validation error"""
        # Mock the repository to raise a validation error
        mock_repo = MagicMock()
        mock_repo.create_project.side_effect = ValueError("Project name cannot be empty")
        mock_repo_class.return_value = mock_repo
        
        # Mock storage service
        with patch('api.services.storage.StorageService') as mock_storage:
            mock_storage.return_value.save_result.return_value = "fake-blob-name"
            
            mutation = {
                "query": """
                mutation($input: CreateProjectInput!) {
                    createProject(input: $input) {
                        success
                        error
                        project {
                            id
                            name
                        }
                    }
                }
                """,
                "variables": {
                    "input": {
                        "name": ""  # Empty name should cause validation error
                    }
                }
            }
            
            r = client.post("/graphql", json=mutation, headers=get_auth_headers())
            assert r.status_code == 200
            
            data = r.json()["data"]["createProject"]
            assert data["success"] is False
            assert "Project name cannot be empty" in data["error"]
            assert data["project"] is None


class TestErrorHandling:
    def test_malformed_graphql_query(self):
        """Test handling of malformed GraphQL queries"""
        malformed_query = {
            "query": "{ malformed query without proper syntax"
        }
        
        r = client.post("/graphql", json=malformed_query, headers=get_auth_headers())
        # Should return 400 for syntax errors
        assert r.status_code == 400

    def test_invalid_field_query(self):
        """Test querying for non-existent fields"""
        invalid_query = {
            "query": "{ project(id: \"1\") { id name nonExistentField } }"
        }
        
        r = client.post("/graphql", json=invalid_query, headers=get_auth_headers())
        # GraphQL should return 400 for invalid field queries
        assert r.status_code == 400


# Simple test for the basic health endpoint
class TestBasicHealth:
    def test_root_endpoint(self):
        """Test root endpoint"""
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "message" in data
        assert "mseONE PoC API" in data["message"]