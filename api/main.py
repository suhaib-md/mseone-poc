from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from strawberry.fastapi import GraphQLRouter

from api.graphql.schema import schema

ENV = os.getenv("APP_ENV", "azure")

if ENV == "local":
    from api.auth import require_bearer as auth_dep
else:
    from api.auth_azure import require_aad_bearer as auth_dep

# Create FastAPI app first
app = FastAPI(title="mseONE PoC API")

# Create GraphQL router
graphql_app = GraphQLRouter(schema)

# Mount GraphQL with dependency
app.include_router(graphql_app, prefix="/graphql", dependencies=[Depends(auth_dep)])

@app.get("/")
def root():
    """Root endpoint with basic API information"""
    return {
        "message": "mseONE PoC API",
        "version": "1.0.0",
        "environment": ENV,
        "graphql_endpoint": "/graphql",
        "health_check": "/healthz",
    }


@app.get("/healthz")
def health():
    """Enhanced health check endpoint"""
    try:
        # Test basic imports
        from api.repositories.projects import ProjectRepository
        from api.services.storage import StorageService
        
        health_info = {
            "status": "ok",
            "environment": ENV,
            "cosmos_configured": bool(os.getenv("COSMOS_KEY")),
            "storage_configured": bool(os.getenv("STORAGE_KEY")),
        }
        
        # Test Cosmos connection (lightweight check)
        try:
            repo = ProjectRepository()
            # Just test that we can initialize the client
            health_info["cosmos_connection"] = "ok"
        except Exception as e:
            health_info["cosmos_connection"] = f"error: {str(e)}"
            health_info["status"] = "degraded"
        
        return health_info
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "environment": ENV,
        }