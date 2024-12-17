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
        start = now+timedelta(days=1)
        end = now+timedelta(days=2) 
        start_period = (start).replace(hour=0, minute=0, second=0, microsecond=0)
        start_period = int(start_period.strftime("%Y%m%d%H%M"))
        end_period = (end).replace(hour=0, minute=0, second=0, microsecond=0)
        end_period = int(end_period.strftime("%Y%m%d%H%M"))

        # Localize the current date and time to the specified time zone using pytz
        localized_date = timezone.localize(now)

        # Check if the date is during daylight saving time
        self.is_dst = localized_date.dst() != timedelta(0)      

        # start_period = 202412160000
        # end_period = 202412180000
        
        #start = int(now.strftime("%Y%m%d%H%M"))
        querystring = {"documentType":"A44","in_Domain":"10YPL-AREA-----S","out_Domain":"10YPL-AREA-----S","periodStart":start_period, "periodEnd":end_period}
        try:
            response = requests.get(self.url, params=querystring)   
            print(response.text)               
            if response.status_code == 200:
                self.parse_xml(response.text)
            else:
                raise Exception(f"Failed to fetch data: {response.status_code}")
        except Exception as e:
            print("Fetching Error!")


         
        # LOOP FOR YEARS
        # start_time = (now).replace(year=2024, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # init_time = start_time - timedelta(weeks=4)
        
        # end_time = start_time + timedelta(weeks=4)

        # while init_time <= now - timedelta(days=45):
        #     init_time = init_time + timedelta(weeks=4)
        #     end_time = init_time + timedelta(weeks=4)

        #     print(f"{init_time} || {end_time}")

        #     start = int(init_time.strftime("%Y%m%d%H%M"))
        #     end = int(end_time.strftime("%Y%m%d%H%M"))      

        #     querystring = {"documentType":"A44","in_Domain":"10YPL-AREA-----S","out_Domain":"10YPL-AREA-----S","periodStart":start, "periodEnd":end}
        #     response = requests.get(self.url, params=querystring)

        #     if response.status_code == 200:
        #         self.parse_xml(response.text)
        #         #return response.text
        #     else:
        #         raise Exception(f"Failed to fetch data: {response.status_code}")
        
        
    def parse_xml(self,xml_data):
        # Parse the XML
        root = ET.fromstring(xml_data)

        # Define the XML namespace
        ns = {'ns': 'urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3'}

        # Loop over each TimeSeries
        for time_series in root.findall('ns:TimeSeries', ns):
            # Extract the time interval
            period = time_series.find('ns:Period', ns)
            time_interval = period.find('ns:timeInterval', ns)
            start_str = time_interval.find('ns:start', ns).text

            # Convert start timestamp to a datetime object
            start_time = datetime.strptime(start_str, '%Y-%m-%dT%H:%MZ')            

            # Loop over each Point in the Period
            for point in period.findall('ns:Point', ns)[::1]:
                position = int(point.find('ns:position', ns).text)
                price_amount = point.find('ns:price.amount', ns).text
                
                # Calculate the timestamp by adding the position as hours to the start_time
                price_timestamp = start_time + timedelta(hours=(position)) 
                price_entry, created = Price.objects.update_or_create(
                    timestamp=price_timestamp,
                    defaults={'price': price_amount, 'currency': 'EUR'}
                )
                if created:
                    print(f"Inserted: {price_timestamp}: Price = {price_amount} EUR")
                else:
                    print(f"Updated: {price_timestamp}: Price = {price_amount} EUR (was {price_entry.price} EUR before update)")


