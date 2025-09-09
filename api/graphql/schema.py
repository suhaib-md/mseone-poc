from __future__ import annotations

import base64
from datetime import datetime
from enum import Enum

import strawberry

from api.repositories.projects import (
    CreateProjectRequest,
    ProjectRecord,
    ProjectRepository,
    ProjectStatus,
    UpdateProjectRequest,
)
from api.services.storage import StorageService


def encode_cursor(project_id: str) -> str:
    return base64.b64encode(f"pid:{project_id}".encode()).decode()


def decode_cursor(cursor: str | None) -> str | None:
    if not cursor:
        return None
    try:
        raw = base64.b64decode(cursor.encode()).decode()
        if raw.startswith("pid:"):
            return raw.split(":", 1)[1]
        return None
    except Exception:
        return None


@strawberry.enum
class ProjectStatusEnum(Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"
    COMPLETED = "completed"


@strawberry.enum
class OrderDirection(Enum):
    ASC = "ASC"
    DESC = "DESC"


@strawberry.enum
class OrderBy(Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NAME = "name"
    ID = "id"


# Helper function to convert between enum types
def convert_status_to_repo_enum(status: ProjectStatusEnum) -> ProjectStatus:
    """Convert GraphQL enum to repository enum"""
    return ProjectStatus(status.value)


def convert_status_from_repo_enum(status: ProjectStatus) -> ProjectStatusEnum:
    """Convert repository enum to GraphQL enum"""
    return ProjectStatusEnum(status.value)


# GraphQL Types
@strawberry.type
class Project:
    id: strawberry.ID
    name: str
    description: str | None
    status: ProjectStatusEnum
    owner_id: str | None
    created_at: str  # ISO format
    updated_at: str  # ISO format
    tags: list[str]
    budget: float | None
    due_date: str | None  # ISO format

    @staticmethod
    def from_record(rec: ProjectRecord) -> Project:
        return Project(
            id=rec.id,
            name=rec.name,
            description=rec.description,
            status=convert_status_from_repo_enum(rec.status),  # Convert enum
            owner_id=rec.owner_id,
            created_at=rec.created_at.isoformat(),
            updated_at=rec.updated_at.isoformat(),
            tags=rec.tags,
            budget=rec.budget,
            due_date=rec.due_date.isoformat() if rec.due_date else None,
        )


@strawberry.type
class ProjectSummary:
    total_projects: int
    active_projects: int
    archived_projects: int
    draft_projects: int
    completed_projects: int


@strawberry.type
class PageInfo:
    has_next_page: bool
    end_cursor: str | None


@strawberry.type
class ProjectEdge:
    cursor: str
    node: Project


@strawberry.type
class ProjectConnection:
    edges: list[ProjectEdge]
    page_info: PageInfo
    total_count: int


# Input Types for Mutations
@strawberry.input
class CreateProjectInput:
    name: str
    description: str | None = None
    owner_id: str | None = None
    tags: list[str] | None = None
    budget: float | None = None
    due_date: str | None = None  # ISO format
    status: ProjectStatusEnum | None = ProjectStatusEnum.DRAFT


@strawberry.input
class UpdateProjectInput:
    name: str | None = None
    description: str | None = None
    status: ProjectStatusEnum | None = None
    owner_id: str | None = None
    tags: list[str] | None = None
    budget: float | None = None
    due_date: str | None = None  # ISO format


# Response Types for Mutations
@strawberry.type
class CreateProjectResponse:
    success: bool
    project: Project | None
    error: str | None


@strawberry.type
class UpdateProjectResponse:
    success: bool
    project: Project | None
    error: str | None


@strawberry.type
class DeleteProjectResponse:
    success: bool
    project_id: str
    error: str | None


# GraphQL Query Class
@strawberry.type
class Query:
    @strawberry.field
    def project(self, id: strawberry.ID) -> Project | None:
        """Get a single project by ID"""
        repo = ProjectRepository()
        rec = repo.get_by_id(str(id))

        if rec:
            # Save result to Blob Storage
            storage = StorageService()
            try:
                storage.save_result(
                    {
                        "query": "project",
                        "project_id": str(id),
                        "result": {
                            "id": rec.id,
                            "name": rec.name,
                            "status": rec.status.value,
                            "created_at": rec.created_at.isoformat(),
                        },
                    }
                )
            except Exception as e:
                print(f"Failed to save result to storage: {e}")

            return Project.from_record(rec)
        return None

    @strawberry.field
    def projects(
        self,
        first: int = 10,
        after: str | None = None,
        name_contains: str | None = None,
        status: ProjectStatusEnum | None = None,
        owner_id: str | None = None,
        tags: list[str] | None = None,
        order_by: OrderBy = OrderBy.CREATED_AT,
        order_direction: OrderDirection = OrderDirection.DESC,
    ) -> ProjectConnection:
        """Get a paginated list of projects with filtering"""
        repo = ProjectRepository()
        after_id = decode_cursor(after)

        # Clamp pagination
        first = min(max(first, 1), 50)

        # Convert status enum if provided
        repo_status = convert_status_to_repo_enum(status) if status else None

        rows, has_next = repo.list_projects(
            name_contains=name_contains,
            status=repo_status,  # Use converted enum
            owner_id=owner_id,
            tags=tags,
            first=first,
            after_id=after_id,
            order_by=order_by.value,
            order_direction=order_direction.value,
        )

        edges = [ProjectEdge(cursor=encode_cursor(r.id), node=Project.from_record(r)) for r in rows]
        end_cursor = edges[-1].cursor if edges else None

        # Get total count
        total_count = repo.get_project_count(
            name_contains=name_contains,
            status=repo_status,  # Use converted enum
            owner_id=owner_id,
            tags=tags,
        )

        # Save result to Blob Storage
        try:
            storage = StorageService()
            storage.save_result(
                {
                    "query": "projects",
                    "filters": {
                        "name_contains": name_contains,
                        "status": status.value if status else None,
                        "owner_id": owner_id,
                        "tags": tags,
                    },
                    "pagination": {"first": first, "after": after},
                    "ordering": {
                        "order_by": order_by.value,
                        "order_direction": order_direction.value,
                    },
                    "result_count": len(rows),
                    "total_count": total_count,
                }
            )
        except Exception as e:
            print(f"Failed to save result to storage: {e}")

        return ProjectConnection(
            edges=edges,
            page_info=PageInfo(has_next_page=has_next, end_cursor=end_cursor),
            total_count=total_count,
        )

    @strawberry.field
    def project_summary(self) -> ProjectSummary:
        """Get summary statistics of all projects"""
        repo = ProjectRepository()
        summary = repo.get_projects_by_status_summary()
        total = sum(summary.values())

        # Save result to Blob Storage
        try:
            storage = StorageService()
            storage.save_result(
                {
                    "query": "project_summary",
                    "result": {"total_projects": total, "status_breakdown": summary},
                }
            )
        except Exception as e:
            print(f"Failed to save result to storage: {e}")

        return ProjectSummary(
            total_projects=total,
            active_projects=summary.get("active", 0),
            archived_projects=summary.get("archived", 0),
            draft_projects=summary.get("draft", 0),
            completed_projects=summary.get("completed", 0),
        )


# GraphQL Mutation Class
@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_project(self, input: CreateProjectInput) -> CreateProjectResponse:
        """Create a new project"""
        try:
            repo = ProjectRepository()

            # Parse due_date if provided
            due_date = None
            if input.due_date:
                try:
                    due_date = datetime.fromisoformat(input.due_date.replace("Z", "+00:00"))
                except ValueError:
                    return CreateProjectResponse(
                        success=False,
                        project=None,
                        error="Invalid due_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                    )

            # Convert status enum
            repo_status = (
                convert_status_to_repo_enum(input.status) if input.status else ProjectStatus.DRAFT
            )

            request = CreateProjectRequest(
                name=input.name,
                description=input.description,
                owner_id=input.owner_id,
                tags=input.tags or [],
                budget=input.budget,
                due_date=due_date,
                status=repo_status,  # Use converted enum
            )

            project = repo.create_project(request)

            # Save result to Blob Storage
            try:
                storage = StorageService()
                storage.save_result(
                    {
                        "mutation": "create_project",
                        "input": {"name": input.name, "status": repo_status.value},
                        "result": {"project_id": project.id, "success": True},
                    }
                )
            except Exception as e:
                print(f"Failed to save mutation result to storage: {e}")

            return CreateProjectResponse(
                success=True, project=Project.from_record(project), error=None
            )

        except ValueError as e:
            return CreateProjectResponse(success=False, project=None, error=str(e))
        except RuntimeError as e:
            return CreateProjectResponse(success=False, project=None, error=str(e))
        except Exception as e:
            return CreateProjectResponse(
                success=False, project=None, error=f"Unexpected error: {e}"
            )

    @strawberry.mutation
    def update_project(self, id: strawberry.ID, input: UpdateProjectInput) -> UpdateProjectResponse:
        """Update an existing project"""
        try:
            repo = ProjectRepository()

            # Parse due_date if provided
            due_date = None
            if input.due_date is not None:  # Allow clearing due_date with empty string
                if input.due_date:
                    try:
                        due_date = datetime.fromisoformat(input.due_date.replace("Z", "+00:00"))
                    except ValueError:
                        return UpdateProjectResponse(
                            success=False,
                            project=None,
                            error="Invalid due_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                        )

            # Convert status enum if provided
            repo_status = convert_status_to_repo_enum(input.status) if input.status else None

            request = UpdateProjectRequest(
                name=input.name,
                description=input.description,
                status=repo_status,  # Use converted enum
                owner_id=input.owner_id,
                tags=input.tags,
                budget=input.budget,
                due_date=due_date,
            )

            project = repo.update_project(str(id), request)

            if not project:
                return UpdateProjectResponse(
                    success=False, project=None, error=f"Project with ID {id} not found"
                )

            # Save result to Blob Storage
            try:
                storage = StorageService()
                storage.save_result(
                    {
                        "mutation": "update_project",
                        "project_id": str(id),
                        "input": {
                            "name": input.name,
                            "status": input.status.value if input.status else None,
                        },
                        "result": {"success": True, "updated_at": project.updated_at.isoformat()},
                    }
                )
            except Exception as e:
                print(f"Failed to save mutation result to storage: {e}")

            return UpdateProjectResponse(
                success=True, project=Project.from_record(project), error=None
            )

        except RuntimeError as e:
            return UpdateProjectResponse(success=False, project=None, error=str(e))
        except Exception as e:
            return UpdateProjectResponse(
                success=False, project=None, error=f"Unexpected error: {e}"
            )

    @strawberry.mutation
    def delete_project(self, id: strawberry.ID) -> DeleteProjectResponse:
        """Delete a project"""
        try:
            repo = ProjectRepository()
            success = repo.delete_project(str(id))

            if not success:
                return DeleteProjectResponse(
                    success=False, project_id=str(id), error=f"Project with ID {id} not found"
                )

            # Save result to Blob Storage
            try:
                storage = StorageService()
                storage.save_result(
                    {
                        "mutation": "delete_project",
                        "project_id": str(id),
                        "result": {"success": True, "deleted_at": datetime.utcnow().isoformat()},
                    }
                )
            except Exception as e:
                print(f"Failed to save mutation result to storage: {e}")

            return DeleteProjectResponse(success=True, project_id=str(id), error=None)

        except RuntimeError as e:
            return DeleteProjectResponse(success=False, project_id=str(id), error=str(e))
        except Exception as e:
            return DeleteProjectResponse(
                success=False, project_id=str(id), error=f"Unexpected error: {e}"
            )


# Create schema with mutations
schema = strawberry.Schema(query=Query, mutation=Mutation)
