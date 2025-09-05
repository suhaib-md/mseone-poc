import os
# Set environment BEFORE importing the app
os.environ['APP_ENV'] = 'local'
os.environ['COSMOS_KEY'] = 'fake_key_for_testing'
os.environ['STORAGE_KEY'] = 'fake_storage_key'

from api.main import app
from fastapi.testclient import TestClient

# Create a test client with the properly configured app
test_client = TestClient(app)