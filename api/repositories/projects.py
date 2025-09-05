from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta  # FIXED: Moved import to top
from enum import Enum

from azure.cosmos import CosmosClient, PartitionKey, exceptions


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"
    COMPLETED = "completed"


@dataclass
class ProjectRecord:
    id: str
    name: str
    description: str | None
    status: ProjectStatus
    owner_id: str | None
    created_at: datetime
    updated_at: datetime
    tags: list[str]
    budget: float | None
    due_date: datetime | None
    
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
    def from_dict(cls, data: dict) -> ProjectRecord:
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
    description: str | None = None
    owner_id: str | None = None
    tags: list[str] = None
    budget: float | None = None
    due_date: datetime | None = None
    status: ProjectStatus = ProjectStatus.DRAFT
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class UpdateProjectRequest:
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    owner_id: str | None = None
    tags: list[str] | None = None
    budget: float | None = None
    due_date: datetime | None = None


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
        
        # Validate name is not empty
        if not request.name or not request.name.strip():
            raise ValueError("Project name cannot be empty")
        
        # Validate budget if provided
        if request.budget is not None and request.budget < 0:
            raise ValueError("Budget cannot be negative")
        
        project = ProjectRecord(
            id=project_id,
            name=request.name.strip(),
            description=request.description.strip() if request.description else None,
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
        except exceptions.CosmosResourceExistsError as e:
            raise ValueError(f"Project with ID {project_id} already exists") from e  # FIXED
        except Exception as e:
            raise RuntimeError(f"Failed to create project: {e}") from e  # FIXED

    def get_by_id(self, project_id: str) -> ProjectRecord | None:
        """Get project by ID"""
        try:
            item = self.container.read_item(item=project_id, partition_key=project_id)
            return ProjectRecord.from_dict(item)
        except exceptions.CosmosResourceNotFoundError:
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to get project {project_id}: {e}") from e  # FIXED

    def update_project(self, project_id: str, request: UpdateProjectRequest) -> ProjectRecord | None:
        """Update an existing project"""
        try:
            # Get existing project
            existing_item = self.container.read_item(item=project_id, partition_key=project_id)
            existing_project = ProjectRecord.from_dict(existing_item)
            
            # Update fields if provided
            if request.name is not None:
                if not request.name.strip():
                    raise ValueError("Project name cannot be empty")
                existing_project.name = request.name.strip()
            if request.description is not None:
                existing_project.description = request.description.strip() if request.description else None
            if request.status is not None:
                existing_project.status = request.status
            if request.owner_id is not None:
                existing_project.owner_id = request.owner_id
            if request.tags is not None:
                existing_project.tags = request.tags
            if request.budget is not None:
                if request.budget < 0:
                    raise ValueError("Budget cannot be negative")
                existing_project.budget = request.budget
            if request.due_date is not None:
                existing_project.due_date = request.due_date
            
            existing_project.updated_at = datetime.utcnow()
            
            # Update in database
            updated_item = self.container.replace_item(item=project_id, body=existing_project.to_dict())
            return ProjectRecord.from_dict(updated_item)
            
        except exceptions.CosmosResourceNotFoundError:
            return None
        except ValueError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise RuntimeError(f"Failed to update project {project_id}: {e}") from e  # FIXED

    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        try:
            self.container.delete_item(item=project_id, partition_key=project_id)
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False
        except Exception as e:
            raise RuntimeError(f"Failed to delete project {project_id}: {e}") from e  # FIXED

    def list_projects(
        self,
        name_contains: str | None = None,
        status: ProjectStatus | None = None,
        owner_id: str | None = None,
        tags: list[str] | None = None,
        first: int = 10,
        after_id: str | None = None,
        order_by: str = "created_at",
        order_direction: str = "DESC"
    ) -> tuple[list[ProjectRecord], bool]:
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

        # Handle pagination with cursor
        if after_id:
            # Use created_at for stable pagination instead of ID comparison
            try:
                after_project = self.container.read_item(item=after_id, partition_key=after_id)
                after_timestamp = after_project['created_at']
                
                if order_by == "created_at":
                    if order_direction.upper() == "DESC":
                        query += " AND c.created_at < @after_created_at"
                    else:
                        query += " AND c.created_at > @after_created_at"
                    parameters.append({"name": "@after_created_at", "value": after_timestamp})
                elif order_by == "updated_at":
                    after_timestamp = after_project['updated_at']
                    if order_direction.upper() == "DESC":
                        query += " AND c.updated_at < @after_updated_at"
                    else:
                        query += " AND c.updated_at > @after_updated_at"
                    parameters.append({"name": "@after_updated_at", "value": after_timestamp})
                else:
                    # Fallback to ID-based pagination for other fields
                    if order_direction.upper() == "DESC":
                        query += " AND c.id < @after_id"
                    else:
                        query += " AND c.id > @after_id"
                    parameters.append({"name": "@after_id", "value": after_id})
            except exceptions.CosmosResourceNotFoundError:
                # If after_id doesn't exist, ignore pagination
                pass

        # Add ordering
        if order_by == "created_at":
            query += f" ORDER BY c.created_at {order_direction.upper()}"
        elif order_by == "updated_at":
            query += f" ORDER BY c.updated_at {order_direction.upper()}"
        elif order_by == "name":
            query += f" ORDER BY UPPER(c.name) {order_direction.upper()}"
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
            raise RuntimeError(f"Failed to list projects: {e}") from e  # FIXED

    def get_project_count(
        self,
        name_contains: str | None = None,
        status: ProjectStatus | None = None,
        owner_id: str | None = None,
        tags: list[str] | None = None
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
            raise RuntimeError(f"Failed to get project count: {e}") from e  # FIXED

    def get_projects_by_status_summary(self) -> dict:
        """Get summary of projects by status using individual queries"""
        statuses = ["active", "archived", "draft", "completed"]
        summary = {}
        
        for status in statuses:
            try:
                query = f"SELECT VALUE COUNT(1) FROM c WHERE c.type = 'project' AND c.status = '{status}'"
                result = list(self.container.query_items(
                    query=query,
                    enable_cross_partition_query=True
                ))
                count = result[0] if result else 0
                if count > 0:
                    summary[status] = count
            except Exception as e:
                print(f"Warning: Failed to get count for status {status}: {e}")
                summary[status] = 0
        
        return summary

    def get_projects_by_owner(self, owner_id: str) -> list[ProjectRecord]:
        """Get all projects for a specific owner"""
        query = "SELECT * FROM c WHERE c.type = 'project' AND c.owner_id = @owner_id"
        parameters = [{"name": "@owner_id", "value": owner_id}]
        
        try:
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            return [ProjectRecord.from_dict(item) for item in items]
        except Exception as e:
            raise RuntimeError(f"Failed to get projects for owner {owner_id}: {e}") from e  # FIXED

    def get_projects_by_tag(self, tag: str) -> list[ProjectRecord]:
        """Get all projects containing a specific tag"""
        query = "SELECT * FROM c WHERE c.type = 'project' AND ARRAY_CONTAINS(c.tags, @tag)"
        parameters = [{"name": "@tag", "value": tag}]
        
        try:
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            return [ProjectRecord.from_dict(item) for item in items]
        except Exception as e:
            raise RuntimeError(f"Failed to get projects for tag {tag}: {e}") from e  # FIXED

    def search_projects(self, search_term: str, limit: int = 20) -> list[ProjectRecord]:
        """Search projects by name or description"""
        query = """
        SELECT * FROM c 
        WHERE c.type = 'project' 
        AND (CONTAINS(UPPER(c.name), UPPER(@search)) 
             OR CONTAINS(UPPER(c.description), UPPER(@search)))
        ORDER BY c.updated_at DESC
        """
        parameters = [{"name": "@search", "value": search_term}]
        
        try:
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
                max_item_count=limit
            ))
            return [ProjectRecord.from_dict(item) for item in items]
        except Exception as e:
            raise RuntimeError(f"Failed to search projects: {e}") from e  # FIXED

    def get_projects_due_soon(self, days: int = 7) -> list[ProjectRecord]:
        """Get projects due within specified days"""
        cutoff_date = (datetime.utcnow() + timedelta(days=days)).isoformat()
        
        query = """
        SELECT * FROM c 
        WHERE c.type = 'project' 
        AND c.status IN ('active', 'draft')
        AND c.due_date != null 
        AND c.due_date <= @cutoff_date
        ORDER BY c.due_date ASC
        """
        parameters = [{"name": "@cutoff_date", "value": cutoff_date}]
        
        try:
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            return [ProjectRecord.from_dict(item) for item in items]
        except Exception as e:
            raise RuntimeError(f"Failed to get projects due soon: {e}") from e  # FIXED

    def get_budget_summary(self) -> dict:
        """Get budget summary across all projects"""
        query = """
        SELECT 
            SUM(c.budget) as total_budget,
            AVG(c.budget) as average_budget,
            MAX(c.budget) as max_budget,
            MIN(c.budget) as min_budget
        FROM c 
        WHERE c.type = 'project' AND c.budget != null
        """
        
        try:
            result = list(self.container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            if result and result[0]:
                return {
                    "total_budget": result[0].get("total_budget", 0),
                    "average_budget": result[0].get("average_budget", 0),
                    "max_budget": result[0].get("max_budget", 0),
                    "min_budget": result[0].get("min_budget", 0)
                }
            return {
                "total_budget": 0,
                "average_budget": 0,
                "max_budget": 0,
                "min_budget": 0
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get budget summary: {e}") from e  # FIXED
