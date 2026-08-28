import logging
from pymongo import MongoClient
from config.config import config

logger = logging.getLogger(__name__)


class MongoDBConnection:
    def __init__(self):
        self.uri = config.MONGO_URI
        self.db_name = config.DATABASE_NAME
        self.client = None
        self.db = None

    def connect(self) -> bool:
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
            self.db = self.client[self.db_name]
            self.client.admin.command('ping')
            return True
        except Exception:
            if self.uri != "mongodb://127.0.0.1:27017/":
                try:
                    self.client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=1000, connectTimeoutMS=1000)
                    self.db = self.client[self.db_name]
                    self.client.admin.command('ping')
                    return True
                except Exception as exc:
                    logger.error(f"MongoDB connection failed: {exc}")
            else:
                logger.error("MongoDB connection failed.")
            self.client = None
            self.db = None
            return False

    def get_collection(self, collection_name: str):
        if self.db is not None:
            return self.db[collection_name]
        return None

    def close(self):
        if self.client:
            self.client.close()


db_connection = MongoDBConnection()
