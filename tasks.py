import os

from celery import Celery

app = Celery('tasks',
    broker=os.environ.get('REDIS_URL'),
    backend=os.environ.get('REDIS_URL'))

@app.task
def add(x, y):
    return x + y

