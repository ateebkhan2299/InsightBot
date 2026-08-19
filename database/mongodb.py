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
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
            self.db = self.client[self.db_name]
            self.client.admin.command('ping')
            logging.info(f"Initialized MongoDB connection: {self.db_name}")
            return True
        except Exception as e:
            if self.uri != "mongodb://127.0.0.1:27017/":
                try:
                    logging.info("Primary MongoDB URI unreachable, attempting local fallback on 127.0.0.1:27017...")
                    self.client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=1000, connectTimeoutMS=1000)
                    self.db = self.client[self.db_name]
                    self.client.admin.command('ping')
                    logging.info(f"Connected successfully to local MongoDB: {self.db_name}")
                    return True
                except Exception as e2:
                    logging.error(f"MongoDB connection initialization failed: {e2}")
            else:
                logging.error(f"MongoDB connection initialization failed: {e}")
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
