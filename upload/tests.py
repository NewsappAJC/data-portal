# Standard library imports
import os

# Django imports
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings

# Local module imports
from .utils import write_tempfile_to_s3, check_duplicates

# Constants
LOCAL_CSV = os.path.join(settings.BASE_DIR,
                         'upload', 'test_files', 'vote_data.csv')


class UploadFileViewTestCase(TestCase):
    def setUp(self):
        # Create a mock user so that we can access restricted pages
        # without redirecting to /login/
        User.objects.create_user(username='jonathan',
                                 email='jonathan.cox.c@gmail.com',
                                 password='mock_pw')

        self.client.login(username='jonathan', password='mock_pw')

    def test_index_view_get(self):
        """
        Test that the index page loads
        """
        response = self.client.get(reverse('upload:index'))
        self.assertEqual(response.status_code, 200)

    def test_index_view_post(self):
        """
        Test that POST requests populated with correct type of data succeed
        """
        test_data = {
            'table_name': 'voter_dist_data_2016',
            'db_select': 'user_jcox',
            'source': 'Secretary of State',
            'topic': 'Elections',
            'press_contact': 'Secretary of State Dude',
            'press_contact_email': 'secretary@secretary.com',
            'press_contact_number': '123 456 7890',
        }

        path = LOCAL_CSV

        with open(path) as f:
            test_data['data_file'] = f
            response = self.client.post(reverse('upload:index'), test_data)

        self.assertEqual(response.status_code, 200)

    def test_index_view_(self):
        """
        Test that POST requests populated with possible SQL injection
        characters (any non-alphanumeric character) fail
        """
        test_data = {
            'table_name': 'DROP TABLE test_table;',
            'db_select': 'user_jcox',
            'source': 'Secretary of State',
            'topic': 'Elections',
            'press_contact': 'Secretary of State Dude',
            'press_contact_email': 'secretary@secretary-of-state.gov',
            'press_contact_number': '123 456 7890',
        }

        path = LOCAL_CSV

        with open(path) as f:
            test_data['data_file'] = f
            response = self.client.post(reverse('upload:index'), test_data)

        self.assertEqual(response.status_code, 400)


class UtilsTestCase(TestCase):
    """
    Test helper functions that are each too small to justify creating their
    own TestCase instance
    """
    def test_write_tempfile(self):
        s3_path = write_tempfile_to_s3(LOCAL_CSV, 'test')
        self.assertTrue(s3_path.startswith('tmp/test'))

    def test_check_duplicates(self):
        """
        Ensure that check_duplicates changes the name of the file to avoid
        collisions
        """
        original_s3_path = write_tempfile_to_s3(LOCAL_CSV, 'test')
        duplicate_path = check_duplicates(original_s3_path)

        self.assertFalse(original_s3_path == duplicate_path)

