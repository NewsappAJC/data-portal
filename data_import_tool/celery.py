from __future__ import absolute_import

import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_import_tool.settings')

from django.conf import settings

app = Celery('data_import_tool', broker=os.environ.get('REDIS_URL'), backend=os.environ.get('REDIS_URL'))

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))