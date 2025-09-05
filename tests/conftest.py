# tests/conftest.py - Updated with proper base64 key
import base64
import os

import pytest

# Generate a proper fake base64 key for testing
fake_cosmos_key = base64.b64encode(b'fake_cosmos_key_for_testing_purposes_123456').decode('ascii')

# Set environment variables BEFORE any imports that might read them
os.environ.update({
    'APP_ENV': 'local',
    'COSMOS_URI': 'https://test.documents.azure.com:443/',
    'COSMOS_KEY': fake_cosmos_key,  # Proper base64 encoded key
    'COSMOS_DB': 'testdb',
    'COSMOS_CONTAINER': 'testcontainer',
    'STORAGE_ACCOUNT': 'testaccount',
    'STORAGE_KEY': base64.b64encode(b'fake_storage_key_for_testing').decode('ascii')
})

# Now the fixture for cleanup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure test environment stays consistent"""
    original_env = os.environ.copy()
    
    # Ensure these are set with proper base64 encoding
    test_env = {
        'APP_ENV': 'local',
        'COSMOS_URI': 'https://test.documents.azure.com:443/',
        'COSMOS_KEY': fake_cosmos_key,
        'COSMOS_DB': 'testdb',
        'COSMOS_CONTAINER': 'testcontainer',
        'STORAGE_ACCOUNT': 'testaccount',
        'STORAGE_KEY': base64.b64encode(b'fake_storage_key_for_testing').decode('ascii')
    }
    
    os.environ.update(test_env)
    
    yield
    
    # Cleanup (restore original environment)
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_cosmos_repo():
    """Mock the ProjectRepository to avoid real Cosmos DB connections"""
    from unittest.mock import MagicMock, patch
    
    with patch('api.repositories.projects.ProjectRepository') as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        yield mock_repo


@pytest.fixture
def mock_storage_service():
    """Mock the StorageService to avoid real Azure Storage connections"""
    from unittest.mock import MagicMock, patch
    
    with patch('api.services.storage.StorageService') as mock_storage_class:
        mock_storage = MagicMock()
        mock_storage.return_value.save_result.return_value = "fake-blob-name"
        mock_storage_class.return_value = mock_storage
        yield mock_storage