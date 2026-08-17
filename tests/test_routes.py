import unittest
from app import create_app

class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_dashboard_renders(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'mock-user-id'
            sess['username'] = 'testuser'
            sess['is_admin'] = False
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'InsightBot', rv.data)
        self.assertIn(b'Understand More', rv.data)

    def test_news_explorer_renders(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'mock-user-id'
            sess['username'] = 'testuser'
            sess['is_admin'] = False
        rv = self.client.get('/explorer')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'News Explorer', rv.data)

    def test_language_filter_arabic(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'mock-user-id'
            sess['username'] = 'testuser'
            sess['is_admin'] = False
        rv = self.client.get('/explorer?lang=Arabic')
        self.assertEqual(rv.status_code, 200)

    def test_language_filter_russian(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'mock-user-id'
            sess['username'] = 'testuser'
            sess['is_admin'] = False
        rv = self.client.get('/explorer?lang=Russian')
        self.assertEqual(rv.status_code, 200)

    def test_scraper_view_renders(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'mock-user-id'
            sess['username'] = 'testuser'
            sess['is_admin'] = False
        rv = self.client.get('/scraper')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Data Ingestion', rv.data)

    def test_patterns_view_renders(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'mock-user-id'
            sess['username'] = 'testuser'
            sess['is_admin'] = False
        rv = self.client.get('/patterns')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'DOM Pattern Mining', rv.data)

    def test_analytics_view_renders(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'mock-user-id'
            sess['username'] = 'testuser'
            sess['is_admin'] = False
        rv = self.client.get('/analytics')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Tableau', rv.data)

    def test_evaluation_view_renders(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'mock-user-id'
            sess['username'] = 'testuser'
            sess['is_admin'] = False
        rv = self.client.get('/evaluation')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'10 Unseen Websites', rv.data)

    def test_scheduler_view_renders(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'mock-user-id'
            sess['username'] = 'testuser'
            sess['is_admin'] = False
        rv = self.client.get('/scheduler')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Automation Scheduler', rv.data)

    def test_data_management_renders(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'mock-user-id'
            sess['username'] = 'testuser'
            sess['is_admin'] = False
        rv = self.client.get('/data')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Data Management', rv.data)

    def test_login_page_renders(self):
        rv = self.client.get('/login')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Sign In', rv.data)

    def test_register_page_renders(self):
        rv = self.client.get('/register')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Create Account', rv.data)

if __name__ == '__main__':
    unittest.main()
