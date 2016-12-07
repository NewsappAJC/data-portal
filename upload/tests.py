# Standard library imports
import os

# Django imports
from django.test import TestCase
# from django.core.files import File
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings

# Third-party imports
# from mock import Mock

# Local module imports
# from .forms import DataForm


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
        Test that the index page loads and populates the list of databases in
        the form
        """
        response = self.client.get(reverse('upload:index'))
        self.assertEqual(response.status_code, 200)

    def test_index_view_post(self):
        test_data = {
            'table_name': 'voter_dist_data_2016',
            'db_select': 'user_jcox',
            'source': 'Secretary of State',
            'topic': 'Elections',
            'press_contact': 'Secretary of State Dude',
            'press_contact_email': 'secretary@secretary.com',
            'press_contact_number': '123 456 7890',
        }

        path = os.path.join(settings.BASE_DIR,
                            'upload', 'test_files', 'vote_data.csv')

        with open(path) as f:
            test_data['data_file'] = f
            self.client.post(reverse('upload:index'), test_data)
