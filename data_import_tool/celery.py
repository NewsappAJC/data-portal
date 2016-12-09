# Have to use absolute_import so interpreter doesn't get confused by the
# celery.py file
from __future__ import absolute_import

# Python standard lib imports
import os

# Third-party imports
from celery import Celery

# Django imports
# set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_import_tool.settings')

from django.conf import settings

app = Celery('data_import_tool')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
