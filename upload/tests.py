import random
import csv

from django.test import TestCase, Client
from upload.tasks import load_infile

class CeleryTaskTestCase(TestCase):
    def test_upload_works(self):
        test_dict = {'name': 'Jonathan', 'age': 24, 'occupation': 'developer'}
        path = '/tmp/django_import_test.csv'

        with open(path, 'w') as f:
            w = csv.DictWriter(f, test_dict.keys())
            w.writeheader()
            w.writerow(test_dict)

        random_table = 'test'.format(int(random.random() * 1000))
        response = load_infile(db_name='user_cox',
            table_name=random_table,
            path='/Users/jcox/test7.csv', 
            delimiter=','
        )
        print 'task.py returned ', response

class UploadFileViewTestCase(TestCase):
    def test_file_upload_view_works(self):
        test_dict = {'name': 'Jonathan', 'age': 24, 'occupation': 'developer'}
        path = '/tmp/django_import_test.csv'

        with open(path, 'w') as f:
            w = csv.DictWriter(f, test_dict.keys())
            w.writeheader()
            w.writerow(test_dict)

        random_table = 'test{}'.format(int(random.random() * 1000))
        response = load_infile(db_name='user_cox',
            table_name=random_table,
            path='/Users/jcox/test7.csv', 
            delimiter=','
        )
        print 'task.py returned ', response
