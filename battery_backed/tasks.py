from celery.utils.log import get_task_logger 
from celery import shared_task 
from .utils import mail_schedule, make_forecast, agg_for_year_endpoint, get_cumulative_data_year, fetch_prices_service


logger = get_task_logger(__name__)



@shared_task()
def task_mail_scheduling():
    mail_schedule()
    logger.info("Starting Task Mail Scheduling!")



@shared_task()
def task_forecast_schedule_populate():
    make_forecast()
    logger.info("Starting Task Mail Scheduling!")


@shared_task()
def task_year_agg():
    agg_for_year_endpoint()
    logger.info("Starting Task year agg!")

@shared_task()
def task_year_sum():
    get_cumulative_data_year()
    logger.info("Starting Task year SUM!")

@shared_task()
def task_fetch_prices():
    fetch_prices_service()
    logger.info("Starting Task Fetch Prices!")