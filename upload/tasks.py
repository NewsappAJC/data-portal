from __future__ import absolute_import
import os

from tasks.celery import app

@app.task
def fuck(x,y):
    logger.info('Added numbers beep boop')
    return x + y
