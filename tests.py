import unittest
from app import create_app
from app.database.db import db
from app.models.user import User

class DownloaderTestCase(unittest.TestCase):
    def setUp(self):
        self.app_instance = create_app()
        self.app_instance.config['TESTING'] = True
        self.app_instance.config['WTF_CSRF_ENABLED'] = False
        self.app_instance.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = self.app_instance.test_client()
        
        with self.app_instance.app_context():
            db.create_all()

    def tearDown(self):
        with self.app_instance.app_context():
            db.drop_all()

    def test_home_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Supercharge Your', response.data)
        self.assertIn(b'Video Downloads', response.data)

    def test_login_page_loading(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome Back', response.data)

    def test_signup_page_loading(self):
        response = self.app.get('/signup')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Get Started', response.data)

if __name__ == '__main__':
    unittest.main()
