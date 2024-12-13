from celery.utils.log import get_task_logger 
from celery import shared_task 
from .utils import mail_schedule, make_forecast, agg_for_year_endpoint, get_cumulative_data_year, fetch_prices_service, prepare_optimized_battery_schedule, send_optimized_schedule_to_mail, make_price_forecast, calculate_cumulative_revenue


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

@shared_task()
def task_prepare_optimized_schedule_xlsx():
    prepare_optimized_battery_schedule()
    logger.info("Prepare Optimized Schedule xlsx file!")

@shared_task()
def task_send_schedule_to_email():
    send_optimized_schedule_to_mail()
    logger.info("Send Schedule to Mail!")

@shared_task()
def task_create_dam_price():
    make_price_forecast()
    logger.info("Create Price Forecast!")

# @shared_task()
# def task_cumulaticve_revenue():
#     calculate_cumulative_revenue()
#     logger.info("revenue cache set!")