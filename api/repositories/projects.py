from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import os
from azure.cosmos import CosmosClient, exceptions


@dataclass
class ProjectRecord:
    id: int
    name: str
    status: str  # e.g. "active" | "archived"


class ProjectRepository:
    def __init__(self):
        # Expect env vars for connection (best to store in Key Vault later)
        url = os.getenv("COSMOS_URI", "https://mseonepoc-cosmos.documents.azure.com:443/")
        key = os.getenv("COSMOS_KEY")  # you'll grab from `az cosmosdb keys list`
        database_name = os.getenv("COSMOS_DB", "projectsdb")
        container_name = os.getenv("COSMOS_CONTAINER", "projects")

        if not key:
            raise RuntimeError("COSMOS_KEY environment variable is required")

        self.client = CosmosClient(url, credential=key)
        self.db = self.client.get_database_client(database_name)
        self.container = self.db.get_container_client(container_name)

    def get_by_id(self, pid: int) -> Optional[ProjectRecord]:
        try:
            item = self.container.read_item(item=str(pid), partition_key=str(pid))
            return ProjectRecord(id=int(item["id"]), name=item["name"], status=item["status"])
        except exceptions.CosmosResourceNotFoundError:
            return None

    def list(
        self,
        name_contains: Optional[str] = None,
        status: Optional[str] = None,
        first: int = 10,
        after_id: Optional[int] = None,
    ) -> Tuple[List[ProjectRecord], bool]:
        query = "SELECT * FROM c"
        filters = []
        params = []

        if name_contains:
            filters.append("CONTAINS(c.name, @name)")
            params.append({"name": "@name", "value": name_contains})
        if status:
            filters.append("c.status = @status")
            params.append({"name": "@status", "value": status})
        if after_id:
            filters.append("c.id > @after_id")
            params.append({"name": "@after_id", "value": str(after_id)})

        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY c.id ASC"

        items_iter = self.container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        )

        results: List[ProjectRecord] = []
        for item in items_iter:
            results.append(ProjectRecord(id=int(item["id"]), name=item["name"], status=item["status"]))
            if len(results) >= first + 1:
                break

        has_next = len(results) > first
        return results[:first], has_next
