import unittest
from database.repositories import ArticleRepository
from database.mongodb import MongoDBConnection

class TestDatabase(unittest.TestCase):
    def test_article_repository_init(self):
        repo = ArticleRepository()
        self.assertEqual(repo.collection_name, 'articles')

    def test_mongodb_connection_singleton(self):
        from database.mongodb import db_connection
        self.assertIsInstance(db_connection, MongoDBConnection)

if __name__ == '__main__':
    unittest.main()
