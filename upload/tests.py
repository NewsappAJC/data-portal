# Standard library imports
import os

# Django imports
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings

# Third party imports
from mock import patch

# Local module imports
from .views import write_to_db, categorize
from .utils import (write_tempfile_to_s3, check_duplicates, start_s3_session,
                    clean, copy_final_s3)

# Constants
LOCAL_CSV = os.path.join(settings.BASE_DIR,
                         'upload', 'test_files', 'vote_data.csv')


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
        Ensure that check_duplicates changes the name of the file to avoid name
        collisions
        """
        original_s3_path = write_tempfile_to_s3(LOCAL_CSV, 'test')
        duplicate_path = check_duplicates(original_s3_path)

        self.assertFalse(original_s3_path == duplicate_path)

    def test_s3_session_start(self):
        """
        Check that the app is able to connect to s3
        """
        start_s3_session()

    def test_clean(self):
        """
        Check handling of duplicate column names, names with illegal
        characters, and names that exceed the length limit
        """
        test_names = ['duplicate', 'duplicate', 'test;column', 'a'*100]
        clean_names = clean(test_names)

        for c in ['duplicate', 'duplicate1', 'testcolumn', 'a'*60]:
            self.assertTrue(c in clean_names)

    def test_copy_final_s3(self):
        """
        Test that the copy_final_s3 task successfully copies the temporary
        file to its final home on s3
        """
        tmp_path = write_tempfile_to_s3(LOCAL_CSV, 'test')
        db_name = 'test'
        table_name = 'test_table'

        url = copy_final_s3(tmp_path, db_name, table_name)
        self.assertFalse(not url)

class UploadFileViewTestCase(TestCase):
    """
    Test the upload_file view to ensure that it blocks invalid POST data,
    adds the right values to session storage, and returns a page on GET
    """
    def setUp(self):
        # Create a mock user so that we can access restricted pages
        # without redirecting to /login/ + have access to session storage
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
        Test that a POST request populated with legal data succeeds,
        and that the path to the S3 file is written to session storage
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

        session = self.client.session
        self.assertFalse(not session['s3_path'])

    def test_index_view_post_illegal(self):
        """
        Test that a POST requests populated with possible SQL injection
        characters (any non-alphanumeric character) fails
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


class CategorizeViewTestCase(TestCase):
    """
    Test that the categorize view renders correctly when passed headers through
    session storage
    """
    def setUp(self):
        # Create a mock user so that we can access restricted pages
        # without redirecting to /login/. Use RequestFactory to create a mock
        # request object
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='jonathan',
                                 email='jonathan.cox.c@gmail.com',
                                 password='mock_pw')

    def test_categorize_view_get(self):
        request = self.factory.get(reverse('upload:categorize'))
        request.user = self.user
        request.session = {'headers': ['col_1', 'col_2', 'col_3']}

        response = categorize(request)
        self.assertEqual(response.status_code, 200)


class WriteToDBTestCase(TestCase):
    """
    Test that the write_to_db view, when passed an array of header types,
    assigns the types to the correct headers, generates a DB schema, and starts
    a celery task that executes a LOAD DATA INFILE statement to add the data to
    the MySQL DB
    """
    def setUp(self):
        # Create a mock user so that we can access restricted pages
        # without redirecting to /login/
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='jonathan',
                                 email='jonathan.cox.c@gmail.com',
                                 password='mock_pw')

        self.client.login(username='jonathan', password='mock_pw')

    def _celery_task_mock(self):
        task = {'id': 1234}
        return task

    def test_write_to_db_view_get(self):
        """
        GET requests should redirect to index
        """
        response = self.client.get(reverse('upload:write_to_db'))
        self.assertEqual(response.status_code, 302)  # 302 = redirect code

    # Use mock to patch the load_infile function so that we don't actually fire
    # the celery task. Have to patch the namespace that the module is imported
    # into
    @patch('upload.views.load_infile.delay')
    def test_write_to_db_view_post(self, _celery_mock):
        """
        Test that POST requests match the data types the user chooses for the 
        columns to the relevant header, then fire the load_infile task
        """

        test_s3_path = write_tempfile_to_s3(LOCAL_CSV, 'test')

        test_table_params = {
            'topic': 'Test topic',
            'db_name': 'import_tool_test',
            'source': 'Test source',
            'table_name': 'test_table_name'
        }
        test_headers = [{'name': 'income', 'category': None}, 
                        {'name': 'precinct_id', 'category': None}]

        session_data = {
            'table_params': test_table_params,
            's3_path': test_s3_path,
            'headers': test_headers
        }

        # Create the request object manually, since session handling for
        # Client() is messed up see https://code.djangoproject.com/ticket/10899
        # Set the user, session, and method manually
        request = self.factory.get(reverse('upload:write_to_db'))
        request.user = self.user
        request.session = session_data
        request.method = 'POST'

        # Add the POST data (the categories that the user added to the columns)
        test_data = {
            'income': 'first_name',
            'precinct_id': 'last_name'
        }
        request.POST = test_data

        # Now that we've populated the request with data, pass it to the 
        # view
        response = write_to_db(request)

        # Check that the mock celery task was fired and that the page returned
        self.assertTrue(_celery_mock.called)
        self.assertEqual(response.status_code, 200)

