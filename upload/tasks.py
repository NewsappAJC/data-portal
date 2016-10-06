from __future__ import absolute_import

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task
def add(x,y):
    logger.info('Added numbers beep boop')
    return x + y
