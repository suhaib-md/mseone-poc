import json
import os
from datetime import datetime

from azure.storage.blob import BlobServiceClient


class StorageService:
    def __init__(self):
        account = os.getenv("STORAGE_ACCOUNT")
        key = os.getenv("STORAGE_KEY")
        conn_str = f"DefaultEndpointsProtocol=https;AccountName={account};AccountKey={key};EndpointSuffix=core.windows.net"
        self.client = BlobServiceClient.from_connection_string(conn_str)

    def save_result(self, result: dict, container: str = "api-results"):
        today = datetime.utcnow().strftime("%Y%m%d")
        blob_name = f"{today}/{datetime.utcnow().isoformat()}.json"
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        blob_client.upload_blob(json.dumps(result), overwrite=True)
        return blob_name
