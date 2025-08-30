# mseONE PoC API

A modern FastAPI-based GraphQL API for project management with Azure Cosmos DB integration, authentication, and comprehensive CI/CD pipeline.

## 🚀 Features

- **GraphQL API** with full CRUD operations for projects
- **Azure Cosmos DB** integration for scalable data storage
- **Dual Authentication** - Local dev tokens and Azure AD JWT validation
- **Docker Support** with multi-stage builds for production
- **Azure DevOps CI/CD** with automated testing and deployment
- **Comprehensive Testing** with pytest and coverage reporting
- **Code Quality** with Ruff linting and Black formatting
- **Health Checks** and monitoring endpoints
- **Blob Storage** integration for API result logging

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Development](#development)
- [GraphQL Schema](#graphql-schema)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Deployment](#deployment)
- [Docker](#docker)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🔧 Prerequisites

### Local Development
- Python 3.11+
- pip or poetry
- Azure Cosmos DB account
- Azure Storage account (optional, for logging)

### Production Deployment
- Azure Container Registry (ACR)
- Azure Web App for Containers
- Azure DevOps with service connections

## ⚡ Quick Start

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd mseone-poc

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root:

```bash
# Application
APP_ENV=local

# Cosmos DB (Required)
COSMOS_URI=https://your-cosmos-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-primary-key
COSMOS_DB=projectsdb
COSMOS_CONTAINER=projects

# Azure Storage (Optional - for API logging)
STORAGE_ACCOUNT=your-storage-account
STORAGE_KEY=your-storage-key

# Azure AD (Production only)
AZURE_TENANT_ID=your-tenant-id
AZURE_AUDIENCE=api://your-app-id
```

### 3. Initialize Database

Run the setup script to create the database structure and seed sample data:

```bash
python setup_cosmos.py
```

### 4. Start the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

The API will be available at:
- **Root**: http://localhost:8001
- **GraphQL Playground**: http://localhost:8001/graphql
- **Health Check**: http://localhost:8001/healthz

## 📁 Project Structure

```
mseone-poc/
├── api/                          # Main API package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── auth.py                   # Local development authentication
│   ├── auth_azure.py             # Azure AD JWT authentication
│   ├── graphql/
│   │   └── schema.py             # GraphQL schema definitions
│   ├── repositories/
│   │   └── projects.py           # Cosmos DB data access layer
│   └── services/
│       └── storage.py            # Azure Blob Storage service
├── tests/                        # Test suite
│   ├── test_graphql.py           # GraphQL API tests
│   └── test_health.py            # Health endpoint tests
├── Dockerfile                    # Multi-stage Docker build
├── azure-pipelines.yml           # Azure DevOps CI/CD pipeline
├── requirements.txt              # Python dependencies
├── setup_cosmos.py               # Database initialization script
├── pyproject.toml               # Tool configuration
├── pytest.ini                   # Test configuration
└── .gitignore                   # Git ignore patterns
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | No | `azure` | Environment: `local` or `azure` |
| `COSMOS_URI` | Yes | - | Cosmos DB endpoint URL |
| `COSMOS_KEY` | Yes | - | Cosmos DB primary key |
| `COSMOS_DB` | No | `projectsdb` | Database name |
| `COSMOS_CONTAINER` | No | `projects` | Container name |
| `STORAGE_ACCOUNT` | No | - | Azure Storage account name |
| `STORAGE_KEY` | No | - | Azure Storage access key |
| `AZURE_TENANT_ID` | No | - | Azure AD tenant ID (production) |
| `AZURE_AUDIENCE` | No | - | Azure AD application audience (production) |

### Authentication Modes

#### Local Development
- Uses fixed bearer token: `devtoken123`
- Set `APP_ENV=local` in environment

#### Production (Azure)
- Uses Azure AD JWT token validation
- Set `APP_ENV=azure` in environment
- Configure `AZURE_TENANT_ID` and `AZURE_AUDIENCE`

## 🛠️ Development

### Code Quality Tools

The project uses modern Python development tools:

```bash
# Linting with Ruff
ruff check .
ruff check . --fix  # Auto-fix issues

# Formatting with Black
black .

# Type checking with mypy
mypy api/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_graphql.py -v

# Run with live logging
pytest -s --log-cli-level=INFO
```

### Database Management

```bash
# Initialize/reset database with sample data
python setup_cosmos.py

# The script will:
# - Create database and container
# - Seed sample projects
# - Validate setup
# - Show sample queries
```

## 🔍 GraphQL Schema

### Types

```graphql
type Project {
  id: ID!
  name: String!
  description: String
  status: ProjectStatusEnum!
  ownerId: String
  createdAt: String!
  updatedAt: String!
  tags: [String!]!
  budget: Float
  dueDate: String
}

enum ProjectStatusEnum {
  ACTIVE
  ARCHIVED
  DRAFT
  COMPLETED
}

type ProjectConnection {
  edges: [ProjectEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}
```

### Sample Queries

#### Get All Projects
```graphql
query {
  projects(first: 10) {
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
```

#### Filter by Status
```graphql
query {
  projects(status: ACTIVE, first: 5) {
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
```

#### Create Project
```graphql
mutation {
  createProject(input: {
    name: "New Project"
    description: "Project description"
    status: ACTIVE
    tags: ["development", "api"]
    budget: 100000
    ownerId: "user123"
  }) {
    success
    error
    project {
      id
      name
      status
      createdAt
    }
  }
}
```

#### Update Project
```graphql
mutation {
  updateProject(
    id: "proj_apollo_001"
    input: {
      name: "Updated Project Name"
      status: COMPLETED
      budget: 150000
    }
  ) {
    success
    project {
      id
      name
      status
      updatedAt
    }
  }
}
```

## 🌐 API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | API information | No |
| GET | `/healthz` | Health check with service status | No |
| POST | `/graphql` | GraphQL endpoint | Yes |

### Health Check Response
```json
{
  "status": "ok",
  "environment": "local",
  "cosmos_configured": true,
  "storage_configured": true,
  "cosmos_connection": "ok"
}
```

## 🧪 Testing

### Test Categories

1. **Health Tests** - Basic service availability
2. **GraphQL Tests** - Full API functionality
3. **Authentication Tests** - Security validation
4. **CRUD Tests** - Complete lifecycle testing
5. **Error Handling** - Edge cases and failures

### Test Examples

```bash
# Health check
curl -X GET http://localhost:8001/healthz

# GraphQL query with auth
curl -X POST http://localhost:8001/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer devtoken123" \
  -d '{"query": "{ projects(first: 3) { totalCount edges { node { id name status } } } }"}'

# Create project
curl -X POST http://localhost:8001/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer devtoken123" \
  -d '{"query": "mutation { createProject(input: { name: \"API Test\", status: ACTIVE }) { success project { id name } error } }"}'
```

## 🚀 Deployment

### Azure DevOps Pipeline

The project includes a comprehensive CI/CD pipeline (`azure-pipelines.yml`) with:

1. **Build and Test Stage**
   - Python setup and dependency installation
   - Code linting with Ruff
   - Unit tests with pytest
   - Code coverage reporting

2. **Build Image Stage**
   - Docker image build and push to ACR
   - Artifact publishing

3. **Deploy Production Stage**
   - Azure Web App deployment
   - Health checks with retry logic
   - GraphQL functional testing

4. **Post-Deployment Stage**
   - Deployment notifications
   - Cleanup tasks

### Required Azure DevOps Variables

Create a variable group named `poc-variables` with:

```
WEBAPP_NAME=your-webapp-name
RESOURCE_GROUP=your-resource-group
ACR_LOGIN_SERVER=your-acr.azurecr.io
COSMOS_URI=https://your-cosmos.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key
COSMOS_DB=projectsdb
COSMOS_CONTAINER=projects
STORAGE_ACCOUNT=your-storage-account
STORAGE_KEY=your-storage-key
AZURE_TENANT_ID=your-tenant-id
AZURE_AUDIENCE=api://your-app-id
```

### Service Connections

Create these service connections in Azure DevOps:
- `azure-connection` - Azure Resource Manager
- `acr-connection` - Docker Registry (Azure Container Registry)

## 🐳 Docker

### Local Development
```bash
# Build image
docker build -t mseone-poc .

# Run container
docker run -p 8080:8080 \
  -e COSMOS_URI="your-uri" \
  -e COSMOS_KEY="your-key" \
  mseone-poc
```

### Multi-stage Build
The Dockerfile uses multi-stage builds for optimization:
- **Builder stage**: Installs dependencies
- **Runtime stage**: Copies only necessary files for smaller image

## 🔧 Troubleshooting

### Common Issues

#### 1. Cosmos DB Connection Issues
```
Error: Failed to connect to Cosmos DB
```
**Solution**: Verify `COSMOS_URI` and `COSMOS_KEY` are correct and the Cosmos DB account is accessible.

#### 2. Authentication Failures
```
HTTP 401: Missing bearer token
```
**Solution**: 
- **Local**: Use `Authorization: Bearer devtoken123`
- **Production**: Ensure valid Azure AD JWT token

#### 3. Container Creation Errors
```
Error: Container 'projects' not found
```
**Solution**: Run `python setup_cosmos.py` to initialize the database structure.

#### 4. GraphQL Query Errors
```
Error: Cross-partition query requires enabling cross-partition queries
```
**Solution**: The application automatically enables cross-partition queries. Check Cosmos DB configuration.

### Debug Mode

Enable detailed logging by setting environment variables:
```bash
export PYTHONPATH=.
export LOG_LEVEL=DEBUG
uvicorn api.main:app --log-level debug
```

### Health Check Debugging

The health endpoint provides detailed service status:
```bash
curl -s http://localhost:8001/healthz | jq .
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Install dev dependencies**: `pip install -r requirements.txt`
4. **Run tests**: `pytest`
5. **Check code quality**: `ruff check . && black --check .`
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Code Standards
- Follow PEP 8 style guide
- Add type hints for new functions
- Include docstrings for public methods
- Write tests for new features
- Update documentation as needed

## 📄 License

This project is part of the mseONE PoC initiative.

## 🆘 Support

For questions and support:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review the health check endpoint output
3. Check Azure DevOps pipeline logs for deployment issues
4. Review Cosmos DB metrics in Azure Portal

---

**Built with ❤️ using FastAPI, GraphQL, and Azure services**