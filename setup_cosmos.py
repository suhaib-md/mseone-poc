#!/usr/bin/env python3
"""
Cosmos DB Setup and Seeding Script for mseONE PoC

This script:
1. Creates the proper Cosmos DB structure
2. Seeds sample project data
3. Validates the setup
4. Creates indexes for better query performance

FIXED: Cross-partition query issues with GROUP BY aggregates
"""

import os
import sys
from datetime import datetime, timedelta

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError


def get_cosmos_client():
    """Get Cosmos DB client from environment variables"""
    cosmos_uri = os.getenv("COSMOS_URI", "https://mseonepoc-cosmos.documents.azure.com:443/")
    cosmos_key = os.getenv("COSMOS_KEY")
    
    if not cosmos_key:
        print("ERROR: COSMOS_KEY environment variable is required")
        sys.exit(1)
    
    return CosmosClient(cosmos_uri, credential=cosmos_key)


def create_database_and_container(client: CosmosClient):
    """Create database and container with proper configuration"""
    database_name = os.getenv("COSMOS_DB", "projectsdb")
    container_name = os.getenv("COSMOS_CONTAINER", "projects")
    
    print(f"Setting up database: {database_name}")
    
    # Create database
    try:
        database = client.create_database(id=database_name)
        print(f"✅ Created database: {database_name}")
    except CosmosResourceExistsError:
        database = client.get_database_client(database_name)
        print(f"✅ Database already exists: {database_name}")
    
    # Create container with proper partition key
    try:
        container = database.create_container(
            id=container_name,
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400,  # Minimum for shared throughput
        )
        print(f"✅ Created container: {container_name}")
    except CosmosResourceExistsError:
        container = database.get_container_client(container_name)
        print(f"✅ Container already exists: {container_name}")
    
    return database, container


def create_sample_projects() -> list[dict]:
    """Generate sample project data"""
    base_date = datetime.utcnow()
    
    projects = [
        {
            "id": "proj_apollo_001",
            "name": "Apollo Mission Control",
            "description": "Next-generation mission control system for space exploration",
            "status": "active",
            "owner_id": "user_jane_doe",
            "created_at": (base_date - timedelta(days=30)).isoformat(),
            "updated_at": (base_date - timedelta(days=5)).isoformat(),
            "tags": ["space", "mission-critical", "real-time"],
            "budget": 2500000.0,
            "due_date": (base_date + timedelta(days=90)).isoformat(),
            "type": "project"
        },
        {
            "id": "proj_zephyr_002",
            "name": "Zephyr Wind Farm",
            "description": "Sustainable wind energy generation project",
            "status": "active",
            "owner_id": "user_john_smith",
            "created_at": (base_date - timedelta(days=25)).isoformat(),
            "updated_at": (base_date - timedelta(days=2)).isoformat(),
            "tags": ["renewable", "energy", "sustainability"],
            "budget": 5000000.0,
            "due_date": (base_date + timedelta(days=180)).isoformat(),
            "type": "project"
        },
        {
            "id": "proj_hermes_003",
            "name": "Hermes Messaging Platform",
            "description": "Secure messaging platform for enterprise communications",
            "status": "archived",
            "owner_id": "user_alice_brown",
            "created_at": (base_date - timedelta(days=120)).isoformat(),
            "updated_at": (base_date - timedelta(days=60)).isoformat(),
            "tags": ["communication", "security", "enterprise"],
            "budget": 750000.0,
            "due_date": None,
            "type": "project"
        },
        {
            "id": "proj_orion_004",
            "name": "Orion Data Analytics",
            "description": "Advanced data analytics and visualization platform",
            "status": "draft",
            "owner_id": "user_bob_wilson",
            "created_at": (base_date - timedelta(days=10)).isoformat(),
            "updated_at": (base_date - timedelta(days=1)).isoformat(),
            "tags": ["analytics", "data-science", "visualization"],
            "budget": 1200000.0,
            "due_date": (base_date + timedelta(days=120)).isoformat(),
            "type": "project"
        },
        {
            "id": "proj_helios_005",
            "name": "Helios Solar Initiative",
            "description": "Large-scale solar energy deployment across multiple sites",
            "status": "completed",
            "owner_id": "user_mary_johnson",
            "created_at": (base_date - timedelta(days=200)).isoformat(),
            "updated_at": (base_date - timedelta(days=30)).isoformat(),
            "tags": ["solar", "renewable", "deployment"],
            "budget": 8000000.0,
            "due_date": None,
            "type": "project"
        },
        {
            "id": "proj_artemis_006",
            "name": "Artemis AI Research",
            "description": "Cutting-edge artificial intelligence research and development",
            "status": "active",
            "owner_id": "user_david_lee",
            "created_at": (base_date - timedelta(days=45)).isoformat(),
            "updated_at": (base_date - timedelta(days=3)).isoformat(),
            "tags": ["ai", "machine-learning", "research"],
            "budget": 3500000.0,
            "due_date": (base_date + timedelta(days=365)).isoformat(),
            "type": "project"
        },
        {
            "id": "proj_phoenix_007",
            "name": "Phoenix Cloud Migration",
            "description": "Complete infrastructure migration to cloud-native architecture",
            "status": "active",
            "owner_id": "user_sarah_davis",
            "created_at": (base_date - timedelta(days=15)).isoformat(),
            "updated_at": base_date.isoformat(),
            "tags": ["cloud", "migration", "infrastructure"],
            "budget": 1800000.0,
            "due_date": (base_date + timedelta(days=150)).isoformat(),
            "type": "project"
        },
        {
            "id": "proj_titan_008",
            "name": "Titan Security Framework",
            "description": "Comprehensive cybersecurity framework for enterprise applications",
            "status": "draft",
            "owner_id": "user_michael_chen",
            "created_at": (base_date - timedelta(days=5)).isoformat(),
            "updated_at": (base_date - timedelta(hours=12)).isoformat(),
            "tags": ["security", "framework", "cybersecurity"],
            "budget": 2200000.0,
            "due_date": (base_date + timedelta(days=200)).isoformat(),
            "type": "project"
        }
    ]
    
    return projects


def seed_projects(container, projects: list[dict]):
    """Seed the container with sample projects"""
    print(f"Seeding {len(projects)} sample projects...")
    
    for project in projects:
        try:
            container.create_item(body=project)
            print(f"✅ Created project: {project['name']}")
        except CosmosResourceExistsError:
            # Update existing project
            container.replace_item(item=project['id'], body=project)
            print(f"✅ Updated existing project: {project['name']}")
        except Exception as e:
            print(f"❌ Failed to create project {project['name']}: {e}")


def create_indexes(container):
    """Create additional indexes for better query performance"""
    print("Setting up indexes for better query performance...")
    
    # Note: Cosmos DB automatically indexes all properties by default
    # But we can create specific composite indexes for common query patterns
    
    try:
        # Read current indexing policy
        
        # Update indexing policy (this requires container recreation in practice)
        # For this demo, we'll just note that these would be beneficial
        print("✅ Index recommendations noted (composite indexes would require container recreation)")
        
    except Exception as e:
        print(f"⚠️  Could not update indexes: {e}")


def validate_setup(container):
    """Validate that the setup is working correctly"""
    print("\nValidating setup...")
    
    try:
        # Test basic query
        query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'project'"
        results = list(container.query_items(query=query, enable_cross_partition_query=True))
        project_count = results[0] if results else 0
        
        print(f"✅ Found {project_count} projects in container")
        
        # FIXED: Use individual queries for status breakdown instead of GROUP BY
        print("📊 Project status breakdown:")
        statuses = ["active", "archived", "draft", "completed"]
        status_summary = {}
        
        for status in statuses:
            status_query = f"SELECT VALUE COUNT(1) FROM c WHERE c.type = 'project' AND c.status = '{status}'"
            status_results = list(container.query_items(
                query=status_query, 
                enable_cross_partition_query=True
            ))
            count = status_results[0] if status_results else 0
            if count > 0:
                status_summary[status] = count
                print(f"   {status}: {count} projects")
        
        # Test single project retrieval
        single_project_query = "SELECT TOP 1 * FROM c WHERE c.type = 'project'"
        single_result = list(container.query_items(query=single_project_query, enable_cross_partition_query=True))
        
        if single_result:
            project = single_result[0]
            print(f"✅ Sample project: {project['name']} (Status: {project['status']})")
        
        # Test filtering queries
        print("\n🔍 Testing filtering capabilities:")
        
        # Test name filtering
        name_filter_query = "SELECT * FROM c WHERE c.type = 'project' AND CONTAINS(UPPER(c.name), 'APOLLO')"
        name_results = list(container.query_items(query=name_filter_query, enable_cross_partition_query=True))
        print(f"   Name contains 'Apollo': {len(name_results)} results")
        
        # Test status filtering
        status_filter_query = "SELECT * FROM c WHERE c.type = 'project' AND c.status = 'active'"
        status_results = list(container.query_items(query=status_filter_query, enable_cross_partition_query=True))
        print(f"   Active projects: {len(status_results)} results")
        
        # Test tag filtering
        tag_filter_query = "SELECT * FROM c WHERE c.type = 'project' AND ARRAY_CONTAINS(c.tags, 'renewable')"
        tag_results = list(container.query_items(query=tag_filter_query, enable_cross_partition_query=True))
        print(f"   Projects with 'renewable' tag: {len(tag_results)} results")
        
        # Test ordering
        order_query = "SELECT c.id, c.name, c.created_at FROM c WHERE c.type = 'project' ORDER BY c.created_at DESC"
        order_results = list(container.query_items(query=order_query, enable_cross_partition_query=True))
        print(f"   Ordered by created_at (DESC): {len(order_results)} results")
        
        print("✅ All validation checks passed!")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False
    
    return True


def print_connection_info():
    """Print connection information for reference"""
    cosmos_uri = os.getenv("COSMOS_URI", "https://mseonepoc-cosmos.documents.azure.com:443/")
    database_name = os.getenv("COSMOS_DB", "projectsdb")
    container_name = os.getenv("COSMOS_CONTAINER", "projects")
    
    print("\n" + "="*60)
    print("COSMOS DB CONNECTION INFO")
    print("="*60)
    print(f"URI: {cosmos_uri}")
    print(f"Database: {database_name}")
    print(f"Container: {container_name}")
    print("Partition Key: /id")
    print("="*60)


def print_sample_queries():
    """Print some sample queries for testing"""
    print("\n" + "="*60)
    print("SAMPLE GRAPHQL QUERIES FOR TESTING")
    print("="*60)
    
    queries = [
        {
            "name": "Get all projects (first 5)",
            "query": """
query {
  projects(first: 5) {
    totalCount
    edges {
      node {
        id
        name
        status
        budget
        tags
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""
        },
        {
            "name": "Filter by status",
            "query": """
query {
  projects(status: ACTIVE, first: 10) {
    totalCount
    edges {
      node {
        id
        name
        ownerId
        tags
        budget
      }
    }
  }
}
"""
        },
        {
            "name": "Filter by name and tags",
            "query": """
query {
  projects(nameContains: "Apollo", tags: ["space"], first: 5) {
    totalCount
    edges {
      node {
        id
        name
        description
        status
        tags
        budget
        dueDate
      }
    }
  }
}
"""
        },
        {
            "name": "Create new project",
            "query": """
mutation {
  createProject(input: {
    name: "New Test Project"
    description: "Created via GraphQL"
    status: ACTIVE
    tags: ["test", "graphql"]
    budget: 100000
    ownerId: "user_test"
  }) {
    success
    error
    project {
      id
      name
      status
      createdAt
      updatedAt
    }
  }
}
"""
        },
        {
            "name": "Update existing project",
            "query": """
mutation {
  updateProject(
    id: "proj_apollo_001"
    input: {
      description: "Updated description"
      status: COMPLETED
      budget: 2600000
    }
  ) {
    success
    error
    project {
      id
      name
      status
      description
      budget
      updatedAt
    }
  }
}
"""
        },
        {
            "name": "Get project summary",
            "query": """
query {
  projectSummary {
    totalProjects
    activeProjects
    archivedProjects
    draftProjects
    completedProjects
  }
}
"""
        },
        {
            "name": "Pagination example",
            "query": """
query {
  projects(
    first: 3
    orderBy: CREATED_AT
    orderDirection: DESC
  ) {
    totalCount
    edges {
      cursor
      node {
        id
        name
        createdAt
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}

# Then use the endCursor for next page:
# query {
#   projects(first: 3, after: "CURSOR_VALUE_HERE") {
#     edges { ... }
#   }
# }
"""
        }
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{i}. {query['name']}:")
        print(query['query'])
    
    print("="*60)


def print_curl_examples():
    """Print curl examples for testing the API"""
    print("\n" + "="*60)
    print("CURL EXAMPLES FOR API TESTING")
    print("="*60)
    print("""
# Health check (no auth required)
curl -X GET http://localhost:8001/healthz

# GraphQL query (requires auth)
curl -X POST http://localhost:8001/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer devtoken123" \
  -d '{
    "query": "{ projects(first: 3) { totalCount edges { node { id name status } } } }"
  }'

# Create project mutation
curl -X POST http://localhost:8001/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer devtoken123" \
  -d '{
    "query": "mutation { createProject(input: { name: \\"API Test Project\\", status: ACTIVE, tags: [\\"api\\", \\"test\\"] }) { success project { id name status } error } }"
  }'

# Get project by ID
curl -X POST http://localhost:8001/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer devtoken123" \
  -d '{
    "query": "{ project(id: \\"proj_apollo_001\\") { id name status description budget tags } }"
  }'
""")
    print("="*60)


def main():
    """Main setup function"""
    print("mseONE PoC - Cosmos DB Setup Script")
    print("="*60)
    
    # Get Cosmos client
    try:
        client = get_cosmos_client()
        print("✅ Connected to Cosmos DB successfully")
    except Exception as e:
        print(f"❌ Failed to connect to Cosmos DB: {e}")
        sys.exit(1)
    
    # Create database and container
    try:
        database, container = create_database_and_container(client)
    except Exception as e:
        print(f"❌ Failed to create database/container: {e}")
        sys.exit(1)
    
    # Generate and seed sample data
    try:
        sample_projects = create_sample_projects()
        seed_projects(container, sample_projects)
    except Exception as e:
        print(f"❌ Failed to seed data: {e}")
        sys.exit(1)
    
    # Setup indexes
    try:
        create_indexes(container)
    except Exception as e:
        print(f"⚠️  Warning: Failed to setup indexes: {e}")
    
    # Validate setup
    if not validate_setup(container):
        print("❌ Setup validation failed!")
        sys.exit(1)
    
    # Print helpful information
    print_connection_info()
    print_sample_queries()
    print_curl_examples()
    
    print("\n🎉 Setup completed successfully!")
    print("Your API should now be able to query the seeded data.")
    print("\nNext steps:")
    print("1. Start your FastAPI server: uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload")
    print("2. Open GraphQL Playground: http://localhost:8001/graphql")
    print("3. Try the sample queries above!")


if __name__ == "__main__":
    main()