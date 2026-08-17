from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config.config import config
import logging

class MongoDBConnection:
    def __init__(self):
        self.uri = config.MONGO_URI
        self.db_name = config.DATABASE_NAME
        self.client = None
        self.db = None
        
    def connect(self):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')  # Verify connection
            self.db = self.client[self.db_name]
            logging.info(f"Connected to MongoDB database: {self.db_name}")
            return True
        except ConnectionFailure as e:
            logging.error(f"MongoDB connection failed: {e}")
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
            logging.info("MongoDB connection closed.")

# Global instance for app usage
db_connection = MongoDBConnection()
