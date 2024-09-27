from celery.utils.log import get_task_logger 
from celery import shared_task 
from .utils import mail_schedule


logger = get_task_logger(__name__)



@shared_task()
def task_mail_scheduling():
    mail_schedule()
    logger.info("Starting Task Mail Scheduling!")


# @shared_task()
# def process_battery_data(date_range, cumulative):
#     # Based on the date_range, use the appropriate manager
#     if date_range == 'today':
#         response = BatteryLiveStatus.today.prepare_consistent_response(cumulative)
#     elif date_range == 'month':
#         response = BatteryLiveStatus.month.get_cumulative_data_month(cumulative)
#     elif date_range == 'year':
#         response = BatteryLiveStatus.year.get_cumulative_data_year(cumulative)
#     return response