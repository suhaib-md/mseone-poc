import os
import pytest

# Set environment variables BEFORE any imports that might read them
os.environ.update({
    'APP_ENV': 'local',
    'COSMOS_URI': 'https://test.documents.azure.com:443/',
    'COSMOS_KEY': 'fake_key_for_testing',
    'COSMOS_DB': 'testdb',
    'COSMOS_CONTAINER': 'testcontainer',
    'STORAGE_ACCOUNT': 'testaccount',
    'STORAGE_KEY': 'fake_storage_key'
})

# Now the fixture for cleanup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure test environment stays consistent"""
    original_env = os.environ.copy()
    
    # Ensure these are set
    test_env = {
        'APP_ENV': 'local',
        'COSMOS_URI': 'https://test.documents.azure.com:443/',
        'COSMOS_KEY': 'fake_key_for_testing',
        'COSMOS_DB': 'testdb',
        'COSMOS_CONTAINER': 'testcontainer',
        'STORAGE_ACCOUNT': 'testaccount',
        'STORAGE_KEY': 'fake_storage_key'
    }
    
    os.environ.update(test_env)
    
    yield
    
    # Cleanup (restore original environment)
    os.environ.clear()
    os.environ.update(original_env)