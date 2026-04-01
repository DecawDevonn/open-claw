import json
import unittest
from app import create_app

class TestAPI(unittest.TestCase):
    def setUp(self):
        """Create a new app instance for each test case."""
        self.app = create_app()  # Adjust as per your application factory
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Destroy the app context after each test case."""
        self.app_context.pop()

    def test_endpoint(self):
        """Test an example API endpoint."""
        response = self.client.get('/api/example')  # Change the endpoint as needed
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'key': 'value'})  # Adjust the response as needed

if __name__ == '__main__':
    unittest.main()