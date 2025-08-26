import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

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
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestProjectQueries:
    def test_graphql_requires_auth(self):
        """Test that GraphQL requires authentication"""
        q = {"query": "{ project(id: \"1\") { id name status } }"}
        r = client.post("/graphql", json=q)  # no auth
        assert r.status_code == 401

    def test_project_query_not_found(self):
        """Test querying non-existent project"""
        q = {"query": "{ project(id: \"nonexistent\") { id name status } }"}
        r = client.post("/graphql", json=q, headers=get_auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert data["data"]["project"] is None

    def test_projects_list_empty(self):
        """Test listing projects when none exist or filters return empty"""
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
        assert data["totalCount"] >= 0
        assert isinstance(data["edges"], list)
        assert "pageInfo" in data

    def test_project_summary(self):
        """Test project summary query"""
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
        assert data["totalProjects"] >= 0


class TestProjectMutations:
    def test_create_project_minimal(self):
        """Test creating project with minimal required fields"""
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
        assert project["id"] is not None
        assert project["createdAt"] is not None
        assert project["updatedAt"] is not None

    def test_create_project_full(self):
        """Test creating project with all fields"""
        due_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
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
                        ownerId
                        tags
                        budget
                        dueDate
                    }
                }
            }
            """,
            "variables": {
                "input": {
                    "name": "Test Project Full",
                    "description": "A comprehensive test project",
                    "status": "ACTIVE",
                    "ownerId": "user123",
                    "tags": ["test", "api", "graphql"],
                    "budget": 50000.0,
                    "dueDate": due_date
                }
            }
        }
        
        r = client.post("/graphql", json=mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        data = r.json()["data"]["createProject"]
        assert data["success"] is True
        assert data["error"] is None
        
        project = data["project"]
        assert project["name"] == "Test Project Full"
        assert project["description"] == "A comprehensive test project"
        assert project["status"] == "ACTIVE"
        assert project["ownerId"] == "user123"
        assert project["tags"] == ["test", "api", "graphql"]
        assert project["budget"] == 50000.0
        assert project["dueDate"] is not None

    def test_create_project_invalid_due_date(self):
        """Test creating project with invalid due date format"""
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
                    "name": "Test Invalid Date",
                    "dueDate": "invalid-date-format"
                }
            }
        }
        
        r = client.post("/graphql", json=mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        data = r.json()["data"]["createProject"]
        assert data["success"] is False
        assert "Invalid due_date format" in data["error"]
        assert data["project"] is None

    def test_update_project(self):
        """Test updating a project"""
        # First create a project
        create_mutation = {
            "query": """
            mutation($input: CreateProjectInput!) {
                createProject(input: $input) {
                    success
                    project { id }
                }
            }
            """,
            "variables": {
                "input": {
                    "name": "Project to Update",
                    "status": "DRAFT"
                }
            }
        }
        
        r = client.post("/graphql", json=create_mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        project_id = r.json()["data"]["createProject"]["project"]["id"]
        
        # Now update it
        update_mutation = {
            "query": """
            mutation($id: ID!, $input: UpdateProjectInput!) {
                updateProject(id: $id, input: $input) {
                    success
                    error
                    project {
                        id
                        name
                        status
                        description
                        tags
                    }
                }
            }
            """,
            "variables": {
                "id": project_id,
                "input": {
                    "name": "Updated Project Name",
                    "status": "ACTIVE",
                    "description": "Updated description",
                    "tags": ["updated", "test"]
                }
            }
        }
        
        r = client.post("/graphql", json=update_mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        data = r.json()["data"]["updateProject"]
        assert data["success"] is True
        assert data["error"] is None
        
        project = data["project"]
        assert project["name"] == "Updated Project Name"
        assert project["status"] == "ACTIVE"
        assert project["description"] == "Updated description"
        assert project["tags"] == ["updated", "test"]

    def test_update_nonexistent_project(self):
        """Test updating a project that doesn't exist"""
        update_mutation = {
            "query": """
            mutation($id: ID!, $input: UpdateProjectInput!) {
                updateProject(id: $id, input: $input) {
                    success
                    error
                    project {
                        id
                    }
                }
            }
            """,
            "variables": {
                "id": "nonexistent_project_id",
                "input": {
                    "name": "Should not work"
                }
            }
        }
        
        r = client.post("/graphql", json=update_mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        data = r.json()["data"]["updateProject"]
        assert data["success"] is False
        assert "not found" in data["error"]
        assert data["project"] is None

    def test_delete_project(self):
        """Test deleting a project"""
        # First create a project
        create_mutation = {
            "query": """
            mutation($input: CreateProjectInput!) {
                createProject(input: $input) {
                    success
                    project { id }
                }
            }
            """,
            "variables": {
                "input": {
                    "name": "Project to Delete"
                }
            }
        }
        
        r = client.post("/graphql", json=create_mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        project_id = r.json()["data"]["createProject"]["project"]["id"]
        
        # Now delete it
        delete_mutation = {
            "query": """
            mutation($id: ID!) {
                deleteProject(id: $id) {
                    success
                    projectId
                    error
                }
            }
            """,
            "variables": {
                "id": project_id
            }
        }
        
        r = client.post("/graphql", json=delete_mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        data = r.json()["data"]["deleteProject"]
        assert data["success"] is True
        assert data["projectId"] == project_id
        assert data["error"] is None

    def test_delete_nonexistent_project(self):
        """Test deleting a project that doesn't exist"""
        delete_mutation = {
            "query": """
            mutation($id: ID!) {
                deleteProject(id: $id) {
                    success
                    projectId
                    error
                }
            }
            """,
            "variables": {
                "id": "nonexistent_project_id"
            }
        }
        
        r = client.post("/graphql", json=delete_mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        data = r.json()["data"]["deleteProject"]
        assert data["success"] is False
        assert data["projectId"] == "nonexistent_project_id"
        assert "not found" in data["error"]


class TestProjectFiltering:
    def test_projects_with_status_filter(self):
        """Test filtering projects by status"""
        q = {
            "query": """
            query($status: ProjectStatusEnum!) {
                projects(status: $status, first: 10) {
                    totalCount
                    edges {
                        node {
                            id
                            status
                        }
                    }
                }
            }
            """,
            "variables": {"status": "ACTIVE"}
        }
        
        r = client.post("/graphql", json=q, headers=get_auth_headers())
        assert r.status_code == 200
        
        data = r.json()["data"]["projects"]
        # All returned projects should have ACTIVE status
        for edge in data["edges"]:
            assert edge["node"]["status"] == "ACTIVE"

    def test_projects_with_name_filter(self):
        """Test filtering projects by name"""
        q = {
            "query": """
            query($nameContains: String!) {
                projects(nameContains: $nameContains, first: 10) {
                    totalCount
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
            """,
            "variables": {"nameContains": "Test"}
        }
        
        r = client.post("/graphql", json=q, headers=get_auth_headers())
        assert r.status_code == 200
        
        data = r.json()["data"]["projects"]
        # All returned projects should contain "Test" in name (case insensitive)
        for edge in data["edges"]:
            assert "test" in edge["node"]["name"].lower()

    def test_projects_with_tags_filter(self):
        """Test filtering projects by tags"""
        q = {
            "query": """
            query($tags: [String!]) {
                projects(tags: $tags, first: 10) {
                    totalCount
                    edges {
                        node {
                            id
                            name
                            tags
                        }
                    }
                }
            }
            """,
            "variables": {"tags": ["test"]}
        }
        
        r = client.post("/graphql", json=q, headers=get_auth_headers())
        assert r.status_code == 200
        
        data = r.json()["data"]["projects"]
        # All returned projects should contain the "test" tag
        for edge in data["edges"]:
            assert "test" in edge["node"]["tags"]

    def test_projects_with_pagination(self):
        """Test pagination functionality"""
        # First request
        q1 = {
            "query": """
            query($first: Int!) {
                projects(first: $first, orderBy: CREATED_AT, orderDirection: ASC) {
                    totalCount
                    edges {
                        cursor
                        node { id name }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
            """,
            "variables": {"first": 2}
        }
        
        r1 = client.post("/graphql", json=q1, headers=get_auth_headers())
        assert r1.status_code == 200
        
        data1 = r1.json()["data"]["projects"]
        if data1["pageInfo"]["hasNextPage"]:
            # Second request with cursor
            end_cursor = data1["pageInfo"]["endCursor"]
            
            q2 = {
                "query": """
                query($first: Int!, $after: String!) {
                    projects(first: $first, after: $after, orderBy: CREATED_AT, orderDirection: ASC) {
                        edges {
                            cursor
                            node { id name }
                        }
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
                """,
                "variables": {"first": 2, "after": end_cursor}
            }
            
            r2 = client.post("/graphql", json=q2, headers=get_auth_headers())
            assert r2.status_code == 200
            
            data2 = r2.json()["data"]["projects"]
            
            # Results should be different (unless there are exactly 2 total projects)
            first_page_ids = {edge["node"]["id"] for edge in data1["edges"]}
            second_page_ids = {edge["node"]["id"] for edge in data2["edges"]}
            
            # Should have no overlap if pagination is working correctly
            assert len(first_page_ids.intersection(second_page_ids)) == 0


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

    def test_missing_required_arguments(self):
        """Test missing required arguments in mutations"""
        mutation = {
            "query": """
            mutation {
                createProject(input: {}) {
                    success
                    error
                }
            }
            """
        }
        
        r = client.post("/graphql", json=mutation, headers=get_auth_headers())
        # Should handle missing required fields gracefully
        assert r.status_code == 400


# Integration test for full CRUD workflow
class TestCRUDWorkflow:
    def test_complete_project_lifecycle(self):
        """Test complete lifecycle: create -> read -> update -> delete"""
        # 1. Create project
        create_mutation = {
            "query": """
            mutation($input: CreateProjectInput!) {
                createProject(input: $input) {
                    success
                    project {
                        id
                        name
                        status
                        description
                    }
                }
            }
            """,
            "variables": {
                "input": {
                    "name": "Lifecycle Test Project",
                    "description": "Testing full CRUD lifecycle",
                    "status": "DRAFT"
                }
            }
        }
        
        r = client.post("/graphql", json=create_mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        create_data = r.json()["data"]["createProject"]
        assert create_data["success"] is True
        project_id = create_data["project"]["id"]
        
        # 2. Read project
        read_query = {
            "query": """
            query($id: ID!) {
                project(id: $id) {
                    id
                    name
                    status
                    description
                }
            }
            """,
            "variables": {"id": project_id}
        }
        
        r = client.post("/graphql", json=read_query, headers=get_auth_headers())
        assert r.status_code == 200
        
        read_data = r.json()["data"]["project"]
        assert read_data["id"] == project_id
        assert read_data["name"] == "Lifecycle Test Project"
        assert read_data["status"] == "DRAFT"
        
        # 3. Update project
        update_mutation = {
            "query": """
            mutation($id: ID!, $input: UpdateProjectInput!) {
                updateProject(id: $id, input: $input) {
                    success
                    project {
                        id
                        name
                        status
                        description
                    }
                }
            }
            """,
            "variables": {
                "id": project_id,
                "input": {
                    "name": "Updated Lifecycle Project",
                    "status": "ACTIVE",
                    "description": "Updated during lifecycle test"
                }
            }
        }
        
        r = client.post("/graphql", json=update_mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        update_data = r.json()["data"]["updateProject"]
        assert update_data["success"] is True
        assert update_data["project"]["name"] == "Updated Lifecycle Project"
        assert update_data["project"]["status"] == "ACTIVE"
        
        # 4. Delete project
        delete_mutation = {
            "query": """
            mutation($id: ID!) {
                deleteProject(id: $id) {
                    success
                    projectId
                }
            }
            """,
            "variables": {"id": project_id}
        }
        
        r = client.post("/graphql", json=delete_mutation, headers=get_auth_headers())
        assert r.status_code == 200
        
        delete_data = r.json()["data"]["deleteProject"]
        assert delete_data["success"] is True
        assert delete_data["projectId"] == project_id
        
        # 5. Verify project is deleted
        r = client.post("/graphql", json=read_query, headers=get_auth_headers())
        assert r.status_code == 200
        
        final_read_data = r.json()["data"]["project"]
        assert final_read_data is None