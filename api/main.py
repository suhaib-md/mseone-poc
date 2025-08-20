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

@app.get("/healthz")
def health():
    return {"status": "ok"}
