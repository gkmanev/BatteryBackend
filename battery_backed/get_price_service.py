import requests
import xml.etree.ElementTree as ET
import pytz
from django.utils import timezone
from datetime import timedelta, datetime, timezone
from battery_backed.models import Price 


class GetPricesDam():

    def __init__(self) -> None:        
        self.url = 'https://web-api.tp.entsoe.eu/api?securityToken=6276342c-e10c-4d88-8688-cb0a1cf163ca'
        self.is_dst = None
        self.prepare_get()

    def prepare_get(self):
        timezone = pytz.timezone('Europe/Sofia')

        # Get the current date and time (naive, without timezone)
        now = datetime.now()

        # Localize the current date and time to the specified time zone using pytz
        localized_date = timezone.localize(now)

        # Check if the date is during daylight saving time
        self.is_dst = localized_date.dst() != timedelta(0)       

        start_time = (now).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        start = int(start_time.strftime("%Y%m%d%H%M"))
        end = int(end_time.strftime("%Y%m%d%H%M"))

        querystring = {"documentType":"A44","in_Domain":"10YCA-BULGARIA-R","out_Domain":"10YCA-BULGARIA-R","periodStart":start, "periodEnd":end}
        response = requests.get(self.url, params=querystring)

        if response.status_code == 200:
            self.parse_xml(response.text)
            #return response.text
        else:
            raise Exception(f"Failed to fetch data: {response.status_code}")
        
        
        
    def parse_xml(self, xml_data):
        # Namespace used in the XML
        ns = {'ns': 'urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3'}

        # Parse the XML response
        root = ET.fromstring(xml_data)

        # Extract TimeSeries data
        time_series = root.find('ns:TimeSeries', ns)
        if time_series is None:
            raise ValueError("TimeSeries element not found in the XML")

        period = time_series.find('ns:Period', ns)
        if period is None:
            raise ValueError("Period element not found in the XML")

        # Extract Points and prices
        points = period.findall('ns:Point', ns)
        prices = []
        for point in points:
            position = point.find('ns:position', ns).text
            price_amount = point.find('ns:price.amount', ns).text
            prices.append((position, price_amount))

        for position, price in prices:
            if self.is_dst:
                position = int(position) - 1
                now = datetime.now(timezone.utc)
                timestamp = (now).replace(hour=position, minute=0, second=0, microsecond=0)
                #date_to_str = date_time.strftime("%Y-%m-%dT%H:%M:00Z")
                
                price_entry, created = Price.objects.get_or_create(timestamp=timestamp, defaults={'price': price, 'currency':'EUR'})
                if created:
                    print(f"Inserted: {timestamp}: Price = {price} EUR")
                else:
                    print(f"Already exists: {timestamp}: Price = {price_entry.price} EUR")


