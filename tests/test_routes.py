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

    def test_admin_notifications_and_approval(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = '64f000000000000000000002'
            sess['username'] = 'adminuser'
            sess['is_admin'] = True

        rv_dash = self.client.get('/dashboard')
        self.assertEqual(rv_dash.status_code, 200)
        self.assertIn(b'Latest Intelligence', rv_dash.data)

        rv_pending = self.client.get('/api/admin/pending-users')
        self.assertEqual(rv_pending.status_code, 200)
        json_data = rv_pending.get_json()
        self.assertTrue(json_data['success'])
        self.assertIn('count', json_data)


if __name__ == '__main__':
    unittest.main()
