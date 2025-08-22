from __future__ import annotations

import base64

import strawberry

from api.repositories.projects import ProjectRecord, ProjectRepository
from api.services.storage import StorageService


def encode_cursor(pid: int) -> str:
    return base64.b64encode(f"pid:{pid}".encode()).decode()


def decode_cursor(cursor: str | None) -> int | None:
    if not cursor:
        return None
    raw = base64.b64decode(cursor.encode()).decode()
    if raw.startswith("pid:"):
        return int(raw.split(":", 1)[1])
    return None


@strawberry.type
class Project:
    id: strawberry.ID
    name: str
    status: str

    @staticmethod
    def from_record(rec: ProjectRecord) -> Project:
        return Project(id=str(rec.id), name=rec.name, status=rec.status)


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


@strawberry.type
class Query:
    @strawberry.field
    def project(self, id: strawberry.ID) -> Project | None:
        repo = ProjectRepository()
        rec = repo.get_by_id(int(id))
        if rec:
            # Save result to Blob Storage
            storage = StorageService()
            storage.save_result({
                "query": "project", 
                "project_id": int(id),
                "result": {"id": rec.id, "name": rec.name, "status": rec.status}
            })
            return Project.from_record(rec)
        return None

    @strawberry.field
    def projects(
        self,
        name_contains: str | None = None,
        status: str | None = None,
        first: int = 10,
        after: str | None = None,
    ) -> ProjectConnection:
        repo = ProjectRepository()
        after_id = decode_cursor(after)
        rows, has_next = repo.list(
            name_contains=name_contains,
            status=status,
            first=min(max(first, 1), 50),  # clamp 1..50
            after_id=after_id,
        )
        edges = [ProjectEdge(cursor=encode_cursor(r.id), node=Project.from_record(r)) for r in rows]
        end_cursor = edges[-1].cursor if edges else None
        total = len([*repo.list(name_contains, status, 1000, None)][0])  # rough count
        
        # Save result to Blob Storage
        storage = StorageService()
        storage.save_result({
            "query": "projects",
            "filters": {"name_contains": name_contains, "status": status},
            "pagination": {"first": first, "after": after},
            "result_count": len(rows)
        })
        
        return ProjectConnection(
            edges=edges,
            page_info=PageInfo(has_next_page=has_next, end_cursor=end_cursor),
            total_count=total,
        )


schema = strawberry.Schema(query=Query)