from __future__ import annotations

import builtins
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple
from enum import Enum

from azure.cosmos import CosmosClient, exceptions, PartitionKey
from azure.cosmos.container import ContainerProxy


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"
    COMPLETED = "completed"


@dataclass
class ProjectRecord:
    id: str
    name: str
    description: Optional[str]
    status: ProjectStatus
    owner_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    budget: Optional[float]
    due_date: Optional[datetime]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for Cosmos DB storage"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "budget": self.budget,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "type": "project"  # For potential multi-entity containers
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectRecord":
        """Create from Cosmos DB document"""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            status=ProjectStatus(data["status"]),
            owner_id=data.get("owner_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            tags=data.get("tags", []),
            budget=data.get("budget"),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None
        )


@dataclass
class CreateProjectRequest:
    name: str
    description: Optional[str] = None
    owner_id: Optional[str] = None
    tags: List[str] = None
    budget: Optional[float] = None
    due_date: Optional[datetime] = None
    status: ProjectStatus = ProjectStatus.DRAFT
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class UpdateProjectRequest:
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    owner_id: Optional[str] = None
    tags: Optional[List[str]] = None
    budget: Optional[float] = None
    due_date: Optional[datetime] = None


class ProjectRepository:
    def __init__(self):
        # Connection configuration
        self.cosmos_uri = os.getenv("COSMOS_URI", "https://mseonepoc-cosmos.documents.azure.com:443/")
        self.cosmos_key = os.getenv("COSMOS_KEY")
        self.database_name = os.getenv("COSMOS_DB", "projectsdb")
        self.container_name = os.getenv("COSMOS_CONTAINER", "projects")

        if not self.cosmos_key:
            raise RuntimeError("COSMOS_KEY environment variable is required")

        # Initialize clients
        self.client = CosmosClient(self.cosmos_uri, credential=self.cosmos_key)
        self.database = self.client.get_database_client(self.database_name)
        self.container = self.database.get_container_client(self.container_name)

    def ensure_container_exists(self):
        """Ensure the container exists with proper configuration"""
        try:
            # Try to get the container first
            self.container.read()
        except exceptions.CosmosResourceNotFoundError:
            # Container doesn't exist, create it
            print("Creating projects container...")
            container = self.database.create_container(
                id=self.container_name,
                partition_key=PartitionKey(path="/id"),
                offer_throughput=400
            )
            print(f"Container {self.container_name} created successfully")
            return container
        except Exception as e:
            print(f"Error checking container: {e}")
            raise

    def create_project(self, request: CreateProjectRequest) -> ProjectRecord:
        """Create a new project"""
        now = datetime.utcnow()
        project_id = f"proj_{int(now.timestamp() * 1000)}"  # Simple ID generation
        
        project = ProjectRecord(
            id=project_id,
            name=request.name,
            description=request.description,
            status=request.status,
            owner_id=request.owner_id,
            created_at=now,
            updated_at=now,
            tags=request.tags or [],
            budget=request.budget,
            due_date=request.due_date
        )
        
        try:
            self.container.create_item(body=project.to_dict())
            return project
        except exceptions.CosmosResourceExistsError:
            raise ValueError(f"Project with ID {project_id} already exists")
        except Exception as e:
            raise RuntimeError(f"Failed to create project: {e}")

    def get_by_id(self, project_id: str) -> Optional[ProjectRecord]:
        """Get project by ID"""
        try:
            item = self.container.read_item(item=project_id, partition_key=project_id)
            return ProjectRecord.from_dict(item)
        except exceptions.CosmosResourceNotFoundError:
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to get project {project_id}: {e}")

    def update_project(self, project_id: str, request: UpdateProjectRequest) -> Optional[ProjectRecord]:
        """Update an existing project"""
        try:
            # Get existing project
            existing_item = self.container.read_item(item=project_id, partition_key=project_id)
            existing_project = ProjectRecord.from_dict(existing_item)
            
            # Update fields if provided
            if request.name is not None:
                existing_project.name = request.name
            if request.description is not None:
                existing_project.description = request.description
            if request.status is not None:
                existing_project.status = request.status
            if request.owner_id is not None:
                existing_project.owner_id = request.owner_id
            if request.tags is not None:
                existing_project.tags = request.tags
            if request.budget is not None:
                existing_project.budget = request.budget
            if request.due_date is not None:
                existing_project.due_date = request.due_date
            
            existing_project.updated_at = datetime.utcnow()
            
            # Update in database
            updated_item = self.container.replace_item(item=project_id, body=existing_project.to_dict())
            return ProjectRecord.from_dict(updated_item)
            
        except exceptions.CosmosResourceNotFoundError:
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to update project {project_id}: {e}")

    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        try:
            self.container.delete_item(item=project_id, partition_key=project_id)
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False
        except Exception as e:
            raise RuntimeError(f"Failed to delete project {project_id}: {e}")

    def list_projects(
        self,
        name_contains: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        first: int = 10,
        after_id: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "DESC"
    ) -> Tuple[List[ProjectRecord], bool]:
        """List projects with filtering and pagination"""
        
        # Build query
        query = "SELECT * FROM c WHERE c.type = 'project'"
        parameters = []

        if name_contains:
            query += " AND CONTAINS(UPPER(c.name), UPPER(@name))"
            parameters.append({"name": "@name", "value": name_contains})

        if status:
            query += " AND c.status = @status"
            parameters.append({"name": "@status", "value": status.value})

        if owner_id:
            query += " AND c.owner_id = @owner_id"
            parameters.append({"name": "@owner_id", "value": owner_id})

        if tags:
            for i, tag in enumerate(tags):
                query += f" AND ARRAY_CONTAINS(c.tags, @tag{i})"
                parameters.append({"name": f"@tag{i}", "value": tag})

        if after_id:
            # Simple cursor pagination using ID comparison
            if order_direction.upper() == "DESC":
                query += " AND c.id < @after_id"
            else:
                query += " AND c.id > @after_id"
            parameters.append({"name": "@after_id", "value": after_id})

        # Add ordering
        if order_by == "created_at":
            query += f" ORDER BY c.created_at {order_direction.upper()}"
        elif order_by == "updated_at":
            query += f" ORDER BY c.updated_at {order_direction.upper()}"
        elif order_by == "name":
            query += f" ORDER BY c.name {order_direction.upper()}"
        else:
            query += f" ORDER BY c.id {order_direction.upper()}"

        try:
            # Execute query with limit
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
                max_item_count=first + 1  # Get one extra to check if there are more
            ))

            # Convert to ProjectRecord objects
            projects = [ProjectRecord.from_dict(item) for item in items[:first]]
            has_next_page = len(items) > first

            return projects, has_next_page

        except Exception as e:
            raise RuntimeError(f"Failed to list projects: {e}")

    def get_project_count(
        self,
        name_contains: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> int:
        """Get total count of projects matching filters"""
        
        query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'project'"
        parameters = []

        if name_contains:
            query += " AND CONTAINS(UPPER(c.name), UPPER(@name))"
            parameters.append({"name": "@name", "value": name_contains})

        if status:
            query += " AND c.status = @status"
            parameters.append({"name": "@status", "value": status.value})

        if owner_id:
            query += " AND c.owner_id = @owner_id"
            parameters.append({"name": "@owner_id", "value": owner_id})

        if tags:
            for i, tag in enumerate(tags):
                query += f" AND ARRAY_CONTAINS(c.tags, @tag{i})"
                parameters.append({"name": f"@tag{i}", "value": tag})

        try:
            result = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            return result[0] if result else 0
        except Exception as e:
            raise RuntimeError(f"Failed to get project count: {e}")

    def get_projects_by_status_summary(self) -> dict:
        """Get summary of projects by status"""
        query = """
        SELECT c.status, COUNT(1) as count
        FROM c 
        WHERE c.type = 'project'
        GROUP BY c.status
        """
        
        try:
            items = list(self.container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            return {item['status']: item['count'] for item in items}
        except Exception as e:
            raise RuntimeError(f"Failed to get status summary: {e}")