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
        if self.client is not None and self.db is not None:
            try:
                self.client.admin.command('ping')
                return True
            except Exception:
                pass

        try:
            tls_kwargs = {}
            try:
                import certifi
                tls_kwargs['tlsCAFile'] = certifi.where()
            except Exception:
                pass

            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                **tls_kwargs
            )
            self.db = self.client[self.db_name]
            self.client.admin.command('ping')
            return True
        except Exception as exc:
            logger.warning(f"Primary MongoDB connection attempt failed: {exc}")
            if self.uri != "mongodb://127.0.0.1:27017/":
                try:
                    self.client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
                    self.db = self.client[self.db_name]
                    self.client.admin.command('ping')
                    return True
                except Exception as exc2:
                    logger.error(f"Fallback local MongoDB connection failed: {exc2}")
            self.client = None
            self.db = None
            return False

    def get_collection(self, collection_name: str):
        if self.db is None:
            self.connect()
        if self.db is not None:
            return self.db[collection_name]
        return None

    def close(self):
        if self.client:
            self.client.close()


db_connection = MongoDBConnection()
