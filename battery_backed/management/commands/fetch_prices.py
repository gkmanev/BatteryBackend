from django.core.management.base import BaseCommand
from battery_backed.get_price_service import GetPricesDam


class Command(BaseCommand):
    help = 'Get Prices from entsoe'

    def handle(self, *args, **kwargs):
        service = GetPricesDam()
        service.fetch_and_store_day_ahead_prices()
