from fastapi.testclient import TestClient

from api.auth import LOCAL_DEV_TOKEN
from api.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_graphql_requires_auth():
    q = {"query": "{ project(id: 1) { id name status } }"}
    r = client.post("/graphql", json=q)  # no auth
    assert r.status_code == 401


def test_project_query_ok():
    q = {"query": "{ project(id: 1) { id name status } }"}
    r = client.post("/graphql", json=q, headers={"Authorization": f"Bearer {LOCAL_DEV_TOKEN}"})
    assert r.status_code == 200
    data = r.json()["data"]["project"]
    assert data["id"] == "1"
    assert data["name"] == "Apollo"


def test_projects_pagination_and_filter():
    q = {
        "query": """
        query($first:Int!, $name:String){
          projects(first:$first, nameContains:$name){
            totalCount
            edges { cursor node { id name status } }
            pageInfo { hasNextPage endCursor }
          }
        }
        """,
        "variables": {"first": 2, "name": "o"},
    }
    r = client.post("/graphql", json=q, headers={"Authorization": f"Bearer {LOCAL_DEV_TOKEN}"})
    assert r.status_code == 200
    body = r.json()["data"]["projects"]
    assert body["totalCount"] >= 1
    assert len(body["edges"]) == 2
    end_cursor = body["pageInfo"]["endCursor"]
    assert end_cursor

    # Next page
    q2 = {
        "query": """
        query($first:Int!, $after:String, $name:String){
          projects(first:$first, after:$after, nameContains:$name){
            edges { node { id name status } }
            pageInfo { hasNextPage endCursor }
          }
        }
        """,
        "variables": {"first": 2, "after": end_cursor, "name": "o"},
    }
    r2 = client.post("/graphql", json=q2, headers={"Authorization": f"Bearer {LOCAL_DEV_TOKEN}"})
    assert r2.status_code == 200
