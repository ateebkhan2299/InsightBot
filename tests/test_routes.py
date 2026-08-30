import os
import sys
os.environ['TESTING'] = 'true'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from app import create_app
from database.mongodb import db_connection
from database.repositories import article_repository, user_repository


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_login_page_renders(self):
        rv = self.client.get('/login')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Sign In', rv.data)

    def test_register_page_renders(self):
        rv = self.client.get('/register')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Create Account', rv.data)

    def test_unauthorized_redirects_to_login(self):
        rv = self.client.get('/dashboard')
        self.assertEqual(rv.status_code, 302)

    def test_logout_redirects(self):
        rv = self.client.get('/logout')
        self.assertEqual(rv.status_code, 302)

    def test_authenticated_explorer_and_language_filters(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = '64f000000000000000000001'
            sess['username'] = 'testuser'
            sess['is_admin'] = False

        rv_en = self.client.get('/explorer?lang=English')
        self.assertEqual(rv_en.status_code, 200)
        self.assertIn(b'News Feed', rv_en.data)

        rv_ar = self.client.get('/explorer?lang=Arabic')
        self.assertEqual(rv_ar.status_code, 200)

        rv_ru = self.client.get('/explorer?lang=Russian')
        self.assertEqual(rv_ru.status_code, 200)

    def test_user_allowed_pages(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = '64f000000000000000000001'
            sess['username'] = 'testuser'
            sess['is_admin'] = False

        allowed_pages = ['/dashboard', '/explorer', '/saved', '/languages', '/analytics', '/profile']
        for page in allowed_pages:
            rv = self.client.get(page)
            self.assertEqual(rv.status_code, 200, f"User should be able to access {page}")

    def test_user_restricted_from_admin_pages_and_apis(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = '64f000000000000000000001'
            sess['username'] = 'testuser'
            sess['is_admin'] = False

        restricted_pages = ['/admin', '/data', '/scraper', '/evaluation', '/patterns', '/scheduler', '/settings']
        for page in restricted_pages:
            rv = self.client.get(page)
            self.assertEqual(rv.status_code, 302, f"User should be redirected away from {page}")

        restricted_apis = [
            ('/api/admin/pending-users', 'GET'),
            ('/api/websites', 'GET'),
            ('/api/scraping/jobs', 'GET'),
            ('/scrape/realtime', 'POST'),
            ('/api/upload', 'POST')
        ]
        for api_path, method in restricted_apis:
            if method == 'GET':
                rv = self.client.get(api_path)
            else:
                rv = self.client.post(api_path, json={})
            self.assertEqual(rv.status_code, 403, f"User should get 403 for {api_path}")

    def test_admin_has_full_access(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = '64f000000000000000000002'
            sess['username'] = 'adminuser'
            sess['is_admin'] = True

        all_pages = ['/dashboard', '/explorer', '/saved', '/languages', '/analytics', '/profile',
                     '/admin', '/data', '/scraper', '/evaluation', '/patterns', '/scheduler', '/settings']
        for page in all_pages:
            rv = self.client.get(page)
            self.assertEqual(rv.status_code, 200, f"Admin should be able to access {page}")


if __name__ == '__main__':
    unittest.main()
