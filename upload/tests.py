# Standard library imports
import random
import csv
from mock import Mock

# Django imports
from django.test import TestCase, Client
from django.core.files import File
from django.urls import reverse
from django.contrib.auth.models import User

# Local module imports
from .tasks import load_infile
from .forms import DataForm

#----------------------------------------------------------------
# Form tests
#----------------------------------------------------------------
#class DataFormTestCase(TestCase):
#    def TestFormValid(self):
#        test_data = {
#            table_name: 'voter_dist_data_2016',
#            db_select: 'user_jcox',
#            source: 'Secretary of State',
#            topic: 'Elections',
#            press_contact: 'Secretary of State Dude',
#            press_contact_email: 'secretary@secretary.com',
#            press_contact_number: '123 456 7890',
#        }
#
#        # Generate a mock file for testing purposes.
#        test_file = Mock(spec=File)
#
#        form = DataForm(test_data, test_file)
#        assert form.is_valid()

#----------------------------------------------------------------
# View tests
#----------------------------------------------------------------
class UploadFileViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='jonathan',
            email='jonathan.cox.c@gmail.com',
            password='top_secret')

    def test_index_view_get(self):
        """
        Test that the index page loads and populates the list of databases in 
        the form
        """
        # Have to set a user or it will redirect to login/
        self.client.login(username='jonathan', password='top_secret')

        response = self.client.get(reverse('upload:index'))
        print 'Trying to get URL: ', reverse('upload:index')
        self.assertEqual(response.status_code, 200)


#----------------------------------------------------------------
# S3 tests
#----------------------------------------------------------------

