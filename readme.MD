# mseONE Proof of Concept API

This repository contains the source code for the mseONE Proof of Concept (PoC) API, a secure, scalable, and well-documented GraphQL API for managing project metadata. Built with Python, FastAPI, and Strawberry, and deployed on Microsoft Azure, this project demonstrates an end-to-end process of building, deploying, and automating a modern API.

## Project Overview

[cite\_start]The primary objective of this PoC is to showcase the ability to design, develop, and deploy APIs with secure integration to internal systems and Azure-based services[cite: 5502]. [cite\_start]It serves as a practical, hands-on guide covering the entire development lifecycle, from initial setup and local development to cloud deployment, security integration, and automated execution[cite: 5].

The project is divided into the following logical phases:

1.  [cite\_start]**Develop a GraphQL API**: An API built from scratch using Python to perform CRUD operations on project data, including advanced filtering and pagination[cite: 9].
2.  [cite\_start]**Connect to a Cloud Database**: The API connects to Azure Cosmos DB for persistent storage and retrieval of project information[cite: 10].
3.  [cite\_start]**Implement Security**: The API is secured using Azure Active Directory (Azure AD) to ensure that only authorized clients can access the data by validating JWT access tokens[cite: 11].
4.  [cite\_start]**Containerize the Application**: The Python application and all its dependencies are packaged into a Docker container for portability and consistent execution in any environment[cite: 12, 13].
5.  **Deploy to Azure**: The Docker container is deployed to the cloud using Azure Web App for Containers, making the API accessible over the internet. [cite\_start]Secrets and configuration are managed securely using Azure Key Vault[cite: 14, 15].
6.  [cite\_start]**Persist API Results**: The API is enhanced to automatically save the results of queries to Azure Blob Storage for logging, auditing, and persistence[cite: 16].
7.  [cite\_start]**Automate with Logic Apps**: An automated workflow is built using Azure Logic Apps that calls the API on a schedule, handles success and failure cases, logs results, and sends notifications[cite: 17].

## Architectural Flow

The following diagram illustrates the architectural flow of the mseONE PoC API:

A step-by-step walkthrough of how all the components work together in the final solution:

1.  **Development & CI**: A developer writes code for the API. [cite\_start]When the code is pushed to the repository, an Azure Pipeline is triggered, which automatically runs quality checks (linting) and executes the automated tests to ensure the code is valid[cite: 26, 27].
2.  **Containerization**: The application is packaged into a Docker image using the Dockerfile. [cite\_start]This image contains the Python application, its dependencies, and instructions on how to run it[cite: 28, 29].
3.  **Deployment**: The Docker image is pushed to the Azure Container Registry. [cite\_start]The Azure Web App service pulls this image and runs it, making the GraphQL API live and accessible on the internet[cite: 30, 31].
4.  **Orchestration (The Automated Workflow)**:
      * [cite\_start]An Azure Logic App is triggered on a recurring schedule (e.g., every day)[cite: 33].
      * [cite\_start]The Logic App first communicates with Azure Active Directory to request a secure access token, proving it has permission to call the API[cite: 34].
      * [cite\_start]With the token in hand, the Logic App sends a GraphQL query to the live API endpoint hosted on the Azure Web App[cite: 35].
      * The API receives the request. [cite\_start]The code in `api/auth_azure.py` validates the token against Azure AD to ensure the request is authorized[cite: 36].
      * [cite\_start]Once authorized, the API queries the Azure Cosmos DB to fetch the requested project data[cite: 37].
      * [cite\_start]Before returning the data, the API calls the Storage Service to save a JSON copy of the result into Azure Blob Storage[cite: 38].
      * [cite\_start]The API sends the data back to the Logic App[cite: 39].
      * The Logic App checks the response. If successful, it sends a success notification. [cite\_start]If it fails, it triggers a separate error-handling workflow that logs the failure and sends a detailed error alert[cite: 40, 41].

## Technologies Used

This project leverages a modern stack of tools and cloud services. The following table provides a description of each component and its role:

| Technology | Description |
| :--- | :--- |
| **Python** | The core programming language used to build the API. [cite\_start]Its simplicity and extensive libraries make it ideal for web development[cite: 21]. |
| **GraphQL** | A query language for APIs. [cite\_start]Instead of having multiple fixed endpoints like in traditional REST APIs, GraphQL exposes a single endpoint where clients can request exactly the data they need, making it highly efficient[cite: 21]. |
| **FastAPI** | A high-performance Python web framework used to build the API. [cite\_start]It's known for its speed, ease of use, and automatic interactive documentation[cite: 21]. |
| **Strawberry** | A Python library for creating GraphQL APIs. [cite\_start]It allows us to define our GraphQL schema using modern Python syntax and data classes, integrating seamlessly with FastAPI[cite: 21]. |
| **Docker** | A platform for containerization. [cite\_start]We use it to package our FastAPI application and its dependencies into a standardized unit (a container) for easy deployment and scaling[cite: 21]. |
| **Microsoft Azure** | [cite\_start]The cloud platform providing all the necessary services for hosting, data storage, security, and automation[cite: 21]. |
| **Azure Web App for Containers** | A fully managed service for hosting containerized applications. [cite\_start]It handles the underlying infrastructure, allowing us to simply run our Docker container in the cloud[cite: 21]. |
| **Azure Cosmos DB** | A globally distributed, multi-model NoSQL database service. We use it as our primary database to store and query project metadata with high performance and availability. [cite\_start]The `ProjectRepository` class directly interacts with it[cite: 22]. |
| **Azure Blob Storage** | A service for storing large amounts of unstructured data, like files. We use it to store the JSON results of our API queries for auditing and persistence purposes. [cite\_start]This is handled by the `StorageService` class[cite: 22]. |
| **Azure Active Directory (AAD)** | A cloud-based identity and access management service. We use it to secure our API, authenticating clients and ensuring that only requests with a valid access token are processed. [cite\_start]The validation logic is in `api/auth_azure.py`[cite: 22]. |
| **Azure Logic Apps** | A service for creating automated workflows that integrate apps, data, and services. [cite\_start]We use it to orchestrate calls to our API, handle errors, and send notifications, all without writing extra code[cite: 22]. |
| **Azure Pipelines** | A continuous integration and continuous delivery (CI/CD) service. [cite\_start]The `azure-pipelines.yml` file defines a pipeline that automatically installs dependencies, runs linting checks, and executes tests on every code change[cite: 22]. |

## Getting Started

### Prerequisites

  * Python 3.11 or later
  * Docker
  * Azure CLI
  * An Azure subscription

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/mseone-poc.git
    cd mseone-poc
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**

    Create a `.env` file in the root of the project and add the following variables:

    ```
    APP_ENV=local
    COSMOS_URI=<your_cosmos_db_uri>
    COSMOS_KEY=<your_cosmos_db_key>
    STORAGE_ACCOUNT=<your_storage_account_name>
    STORAGE_KEY=<your_storage_account_key>
    AZURE_TENANT_ID=<your_azure_tenant_id>
    AZURE_AUDIENCE=<your_azure_audience>
    ```

### Running the API Locally

1.  **Run the FastAPI application:**

    ```bash
    uvicorn api.main:app --reload --port 8001
    ```

2.  **Access the API documentation:**

    Open your browser and navigate to `http://localhost:8001/docs` to see the Swagger UI documentation.

### Running with Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t mseone-poc .
    ```
2.  **Run the Docker container:**
    ```bash
    docker run -p 8001:8001 --env-file .env mseone-poc
    ```

## API Usage

### Authentication

All requests to `/graphql` require a Bearer token. For local development, use: `Authorization: Bearer devtoken123`.

### Endpoints

  * **Health Check**: `GET /healthz`
  * **GraphQL**: `POST /graphql`

### Sample Queries

**Get a project by ID:**

```graphql
{
  project(id: "1") {
    id
    name
    status
  }
}
```

**Get a list of projects with filtering and pagination:**

```graphql
query($first: Int!, $name: String) {
  projects(first: $first, nameContains: $name) {
    totalCount
    edges {
      node {
        id
        name
        status
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

**Variables:**

```json
{
  "first": 2,
  "name": "o"
}
```

## Testing

To run the automated tests, use the following command:

```bash
pytest
```

## Deployment

This project includes a CI/CD pipeline defined in `azure-pipelines.yml` for automated deployment to Azure Web App for Containers. The pipeline is triggered on pushes to the `main` and `feature/*` branches.

## Contributing

Contributions are welcome\! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.