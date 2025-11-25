from datetime import datetime, timedelta
from decimal import Decimal
import xml.etree.ElementTree as ET

import pytz
import requests
from django.utils import timezone

from battery_backed.models import Price


class GetPricesDam:
    """Service for fetching and persisting day-ahead market prices."""

    BASE_URL = "https://web-api.tp.entsoe.eu/api"
    DOMAIN = "10YPL-AREA-----S"
    SECURITY_TOKEN = "6276342c-e10c-4d88-8688-cb0a1cf163ca"

    def __init__(self) -> None:
        self.timezone = pytz.timezone("Europe/Sofia")

    def fetch_and_store_day_ahead_prices(self):
        """Fetch day-ahead prices and persist them into the Price model."""
        start_period, end_period = self._get_day_ahead_period()
        querystring = {
            "documentType": "A44",
            "in_Domain": self.DOMAIN,
            "out_Domain": self.DOMAIN,
            "periodStart": start_period,
            "periodEnd": end_period,
            "securityToken": self.SECURITY_TOKEN,
        }

        response = requests.get(self.BASE_URL, params=querystring)
        response.raise_for_status()

        prices = self._parse_xml(response.text)
        self._store_prices(prices)

    def _get_day_ahead_period(self):
        now = timezone.now().astimezone(self.timezone)
        start = now + timedelta(days=1)
        start_period = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_period = start_period + timedelta(days=1)

        return (
            int(start_period.strftime("%Y%m%d%H%M")),
            int(end_period.strftime("%Y%m%d%H%M")),
        )

    def _parse_xml(self, xml_data):
        root = ET.fromstring(xml_data)
        ns = {"ns": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3"}
        prices = []

        for time_series in root.findall("ns:TimeSeries", ns):
            period = time_series.find("ns:Period", ns)
            time_interval = period.find("ns:timeInterval", ns)
            start_str = time_interval.find("ns:start", ns).text
            start_time = datetime.strptime(start_str, "%Y-%m-%dT%H:%MZ").replace(tzinfo=pytz.utc)
            resolution_str = period.find("ns:resolution", ns)
            step = self._resolution_to_timedelta(resolution_str.text if resolution_str is not None else "PT60M")

            for point in period.findall("ns:Point", ns):
                position = int(point.find("ns:position", ns).text)
                price_amount = Decimal(point.find("ns:price.amount", ns).text)
                price_timestamp = start_time + step * (position - 1)
                prices.append({"timestamp": price_timestamp, "price": price_amount, "currency": "EUR"})

        return prices

    def _resolution_to_timedelta(self, resolution: str) -> timedelta:
        """Translate ENTSO-E resolution strings (e.g. PT15M, PT60M) to timedeltas."""

        # resolution format is expected to be PT{minutes}M or PT{hours}H
        if resolution.startswith("PT") and resolution.endswith("M"):
            minutes = int(resolution[2:-1])
            return timedelta(minutes=minutes)

        if resolution.startswith("PT") and resolution.endswith("H"):
            hours = int(resolution[2:-1])
            return timedelta(hours=hours)

        # Fallback to one hour if an unexpected resolution is encountered
        return timedelta(hours=1)

    def _store_prices(self, prices):
        for price_data in prices:
            price_entry, created = Price.objects.update_or_create(
                timestamp=price_data["timestamp"],
                defaults={"price": price_data["price"], "currency": price_data["currency"]},
            )
            if created:
                print(
                    f"Inserted: {price_entry.timestamp}: Price = {price_entry.price} {price_entry.currency}"
                )
            else:
                print(
                    f"Updated: {price_entry.timestamp}: Price = {price_entry.price} {price_entry.currency}"
                )
