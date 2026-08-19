import unittest
from app import create_app

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

if __name__ == '__main__':
    unittest.main()
