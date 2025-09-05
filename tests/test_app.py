import os

# Set environment BEFORE importing the app
os.environ['APP_ENV'] = 'local'
os.environ['COSMOS_KEY'] = 'fake_key_for_testing'
os.environ['STORAGE_KEY'] = 'fake_storage_key'

from fastapi.testclient import TestClient

from api.main import app

# Create a test client with the properly configured app
test_client = TestClient(app)