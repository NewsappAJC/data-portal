# Standard library imports
import os
import re

# Django imports
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings

# Third party imports
from mock import patch
import botocore

# Local module imports
from .views import write_to_db, categorize, check_task_status
# from .utils import TableFormatter
# from .tasks import load_infile
from .models import Table

# Constants
LOCAL_CSV = os.path.join(settings.BASE_DIR, 'upload', 'test_files', 'vote_data.csv')

# -----------------------------------------------------------------------------
# BEGIN MOCK CLASSES.
# Use these as patches if you want to mock a connection to S3 or the MySQL
# DB without actually connecting
# -----------------------------------------------------------------------------
class MockS3Bucket(object):
    """
    Mock a connection to an S3 bucket
    """
    def __init__(self, *args, **kwargs):
        pass

    def download_file(self, *args, **kwargs):
        # Return a path to the test CSV
        return LOCAL_CSV


class MockS3Object(object):
    """
    Mock a connection to a particular object in S3
    """
    def __init__(self, *args, **kwargs):
        pass

    def copy_from(self, **kwargs):
        pass

    def delete(self):
        pass


class MockS3Session(object):
    """
    Mock boto3.Session
    """
    def __init__(self, *args, **kwargs):
        pass

    def resource(self, *args, **kwargs):
        return {'Bucket': MockS3Bucket,
                'Object': MockS3Object}

class MockBoto(object):
    """
    Mock boto3.client
    """
    def __init__(self, *args, **kwargs):
        pass
    
    def head_object(self, Bucket, Key):
        if re.search(re.compile(r'\(3\)'), Key):
            raise botocore.exceptions.ClientError({'Error': {'Code': 404}}, 'error')
        else:
            pass

class MockS3Client(object):
    """
    Mock boto3.Session
    """
    def __init__(self, *args, **kwargs):
        pass

    def generate_presigned_url(self, *args, **kwargs):
        return 'http://test-url.com'


class MockDBConnection(object):
    """
    Mock a connection to a MySQL server and execute queries on it
    """
    def execute(self, query):
        if query.startswith('SELECT'):
            # Return mock table data for SELECT query
            mock_entries = [1, 2, 3]
            return [
                ['col_1', 'col_2'],
                {'col_1': mock_entries, 'col_2': mock_entries}
            ]

        elif query.startswith('SHOW TABLES'):
            # Return mock names of existing tables in the database
            [('existing_table1'), ('existing_table2')]

        # Return True for all other SQL queries
        return True


class MockSQLAlchemy(object):
    """
    Mocks sqlalchemy
    """
    def create_engine(self, *args, **kwargs):
        return {'connect': MockDBConnection()}

# -----------------------------------------------------------------------------
# END MOCK CLASSES
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# BEGIN TEST CLASSES
# -----------------------------------------------------------------------------

# class UtilsTestCase(TestCase):
#     """
#     Test helper functions that are each too small to justify creating their
#     own TestCase instance
#     """
#     @patch('upload.utils.boto3.client', MockBoto)
#     def test_check_duplicates(self):
#         """
#         Ensure that check_duplicates changes the name of the file to avoid name
#         collisions
#         """
#         duplicate_path = check_duplicates('tmp/test')
#         self.assertEqual(duplicate_path, 'tmp/test(3)')
# 
#     def test_clean(self):
#         """
#         Check handling of duplicate column names, names with illegal
#         characters, and names that exceed the length limit
#         """
#         test_names = ['duplicate', 'duplicate', 'test;column', 'a'*100]
#         clean_names = clean(test_names)
# 
#         for c in ['duplicate', 'duplicate1', 'testcolumn', 'a'*60]:
#             self.assertTrue(c in clean_names)


class UploadFileViewTestCase(TestCase):
    """
    Test the upload_file view to ensure that it blocks invalid POST data,
    adds the right values to session storage, and returns a page on GET
    """
    def setUp(self):
        # Create a mock user so that we can access restricted pages
        # without redirecting to /login/ + have access to session storage
        self.user = User.objects.create_user(username='jonathan',
                                             email='jonathan.cox.c@gmail.com',
                                             password='mock_pw')

        self.client.login(username='jonathan', password='mock_pw')
        
    def test_index_view_get(self):
        """
        Test that the index page loads
        """
        response = self.client.get(reverse('upload:index'))
        self.assertEqual(response.status_code, 200)

    @patch('upload.forms.sqlalchemy')
    @patch('upload.views.write_tempfile_to_s3', return_value=LOCAL_CSV)
    def test_index_view_post(self, MockSQLAlchemy, _upload_mock):
        """
        Test that a POST request populated with legal data succeeds.
        Ensure that the list of headers populated by the function also
        succeeds
        """
        test_data = {
            'table_name': 'voter_dist_data_2016',
            'db_select': 'user_jcox',
            'source': 'Secretary of State',
            'topic': 'Elections',
            'press_contact': 'Secretary of State Dude',
            'press_contact_email': 'secretary@secretary.com',
            'press_contact_number': '123 456 7890',
            'press_contact_type': 'pio'
        }

        path = LOCAL_CSV
        with open(path) as f:
            test_data['data_file'] = f
            response = self.client.post(reverse('upload:index'), test_data)

        # Check that the server responded with a success header
        self.assertEqual(response.status_code, 200)

        # Check that all the column headers are appended to the header list
        session = self.client.session
        rheaders = session.get('headers')
        headers = ['total_income', 'precinct_id', 'tract_id', 'race', 'households']

        self.assertTrue([x['name'] for x in rheaders] == headers)
        self.assertTrue(len(rheaders) == 5)

        # Check that sample data is correct
        self.assertTrue(re.match(re.compile(r'68810444'), rheaders[0]['sample_data'][0]))
        self.assertTrue(re.match(re.compile(r'131'), rheaders[1]['sample_data'][0]))
        self.assertTrue(re.match(re.compile(r'Census Tract 303.09'), rheaders[2]['sample_data'][0]))
        self.assertTrue(re.match(re.compile(r'white'), rheaders[3]['sample_data'][0]))
        self.assertTrue(re.match(re.compile(r'660'), rheaders[4]['sample_data'][0]))

    @patch('upload.forms.sqlalchemy')
    def test_index_view_post_illegal(self, MockSQLAlchemy):
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
        columns to the relevant header, then fires the load_infile task
        """

        test_s3_path = LOCAL_CSV

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

# class LoadInfileTestCase(TestCase):
#     @patch('upload.tasks.boto3.Session')
#     @patch('upload.tasks.sqlalchemy')
#     @patch('upload.tasks.copy_final_s3', return_value='http://test-url.com')
#     def test_load_infile(self, MockS3Session, MockDBConnection, _mock_copy):
#         cols = [
#             {'name': 'total_income'},
#             {'name': 'precinct_id'},
#             {'name': 'tract_id'},
#             {'name': 'race'},
#             {'name': 'households'}
#         ]
#         args = {
#             's3_path': LOCAL_CSV,
#             'db_name': 'test',
#             'table_name': 'test',
#             'columns': cols
#         }
# 
#         data = load_infile.delay(**args)

        # Check that the correct type of query is generated
#         query = 'CREATE TABLE test (total_income FLOAT, precinct_id VARCHAR(5), tract_id VARCHAR(20), race VARCHAR(8), households INTEGER);'
#         self.assertEqual(data.result['create_table_query'], query)

class CheckTaskStatusTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='jonathan',
                                 email='jonathan.cox.c@gmail.com',
                                 password='mock_pw')

    @patch('upload.views.AsyncResult')
    def test_generate_metadata_models(self, mock_response):
        # Create some mock data about the columns and add it to the session
        test_header_1 = {'name': 'company',
                         'category': 'organization_name',
                         'datatype': 'varchar',
                         'length': 10}

        test_header_2 = {'name': 'CEO',
                         'category': 'corp_or_person_name',
                         'datatype': 'varchar',
                         'length': 20}

        test_headers = [test_header_1, test_header_2]

        # Mock return values for AsyncResult
        mock_response.return_value.status = 'SUCCESS'
        mock_response.return_value.result = {'table': 'govt_contract_llcs',
                                             'url': 'http://test-url.com',
                                             'error': None,
                                             'final_s3_path': '/test/',
                                             'warnings': '',
                                             'headers': [test_header_1, test_header_2]}


        # Set some basic parameters for the request
        request = self.factory.get(reverse('upload:check_status'))
        request.user = self.user
        request.method = 'POST'

        test_headers = [test_header_1, test_header_2]

        test_table_params = {
            'topic': 'Companies with government contracts',
            'db_name': 'user_jcox',
            'source': 'FEC',
            'press_contact_type': 'pio',
            'press_contact': 'Brian Kemp',
            'press_contact_email': 'secretary@secretary-of-state.gov',
            'press_contact_number': '123 456 7890',
            'next_update': None
        }

        session_data = {
            'table_params': test_table_params,
            'headers': test_headers,
            'task_id': 000
        }

        request.session = session_data

        # Send the request to the view function so the models are generated and
        # ensure that the server returns a response as JSON
        response = check_task_status(request)
        self.assertEqual(response._headers['content-type'][1], 'application/json')

        # Check that the correct models are created
        x = Table.objects.get(table='govt_contract_llcs')
        y = x.column_set.get(column='company')

        self.assertEqual(x.source, 'FEC')
        self.assertEqual(x.topic, 'Companies with government contracts')
        self.assertEqual(len(x.column_set.all()), 2)
        self.assertEqual(y.information_type, 'organization_name')
        self.assertEqual(y.mysql_type, 'varchar')

