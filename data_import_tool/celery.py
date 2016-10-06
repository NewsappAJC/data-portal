from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_import_tool.settings')
app = Celery('data_import_tool', broker=settings.REDIS_URL, backend=settings.REDIS_URL)

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS) # Find tasks in subdirectories

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
