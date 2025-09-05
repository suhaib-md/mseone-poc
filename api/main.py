from __future__ import annotations

import os
import sys

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from api.graphql.schema import schema

if 'pytest' in sys.modules or 'PYTEST_CURRENT_TEST' in os.environ:
    os.environ['APP_ENV'] = 'local'
    print("🧪 Test mode detected - forcing local environment")

ENV = os.getenv("APP_ENV", "azure").lower()
print(f"🌍 Running in environment: {ENV}")

if ENV == "local":
    print("🔓 Using local dev token authentication")
    from api.auth import require_bearer as auth_dep
else:
    print("🔐 Using Azure AD authentication") 
    from api.auth_azure import require_aad_bearer as auth_dep

# Create FastAPI app first
app = FastAPI(title="mseONE PoC API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ENV == "local" else [
        "https://pocapi-web.azurewebsites.net",  # Replace with your production domains
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://127.0.0.1:5500"  # Live Server default port
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

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
        
        health_info = {
            "status": "ok",
            "environment": ENV,
            "cosmos_configured": bool(os.getenv("COSMOS_KEY")),
            "storage_configured": bool(os.getenv("STORAGE_KEY")),
        }
        
        # Test Cosmos connection (lightweight check)
        try:
            # FIXED: Removed unused variable 'repo'
            ProjectRepository()
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