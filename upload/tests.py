# Standard library imports
import os
from importlib import import_module
# import pdb

# Django imports
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings

# Local module imports
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
        # without redirecting to /login/
        User.objects.create_user(username='jonathan',
                                 email='jonathan.cox.c@gmail.com',
                                 password='mock_pw')

        self.client.login(username='jonathan', password='mock_pw')

        headers = ['col1', 'col2', 'col3']
        session = self.client.session
        session['headers'] = headers

    def test_categorize_view_get(self):
        response = self.client.get(reverse('upload:categorize'))
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
        User.objects.create_user(username='jonathan',
                                 email='jonathan.cox.c@gmail.com',
                                 password='mock_pw')

        self.client.login(username='jonathan', password='mock_pw')

        # Generate some mock session data. WAY harder than it should be, what
        # the heck Django
        engine = import_module(settings.SESSION_ENGINE)
        self.client.session = engine.SessionStore()
        self.client.session.save()

        session_cookie = settings.SESSION_COOKIE_NAME

        self.client.cookies[session_cookie] = self.client.session.session_key
        cookie_data = {
            'max-age': None,
            'path': '/',
            'domain': settings.SESSION_COOKIE_DOMAIN,
            'secure': settings.SESSION_COOKIE_SECURE or None,
            'expires': None,
        }
        self.client.cookies[session_cookie].update(cookie_data)

        test_s3_path = write_tempfile_to_s3(LOCAL_CSV, 'test')
        test_table_params = {
            'topic': 'Test topic',
            'db_name': 'import_tool_test',
            'source': 'Test source',
            'table_name': 'test_table_name'
        }
        test_headers = ['total_income', 'precinct_id', 'tract_id', 'race',
                        'households']

        session_data = {
            'table_params': test_table_params,
            's3_path': test_s3_path,
            'headers': test_headers
        }

        for key in session_data:
            self.client.session[key] = session_data[key]

        self.client.session.save()

    def test_write_to_db_view_get(self):
        """
        GET requests should redirect to index
        """
        response = self.client.get('upload:write_to_db')
        self.assertEqual(response.status_code, 302)  # 302 = redirect code

    #def test_write_to_db_view_post(self):
    #    """
    #    POST requests should match the data types returned by the categorize
    #    view to the relevant header, then fire the load_infile task
    #    """
    #    test_data = {
    #        'total_income': None,
    #        'precinct_id': None,
    #        'tract_id': None,
    #        'race': None,
    #        'households': None,
    #    }
    #    response = self.client.post(reverse('upload:write_to_db'), test_data)
    #    self.assertEqual(response.status_code, 200)

    #    session = self.client.session
    #    self.assertFalse(not session['task_id'])

