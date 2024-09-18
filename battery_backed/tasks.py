from celery.utils.log import get_task_logger 
from celery import shared_task 
from .utils import mail_schedule

logger = get_task_logger(__name__)



@shared_task()
def task_mail_scheduling():
    mail_schedule()
    logger.info("Starting Task Mail Scheduling!")