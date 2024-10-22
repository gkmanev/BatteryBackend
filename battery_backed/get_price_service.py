import requests
import xml.etree.ElementTree as ET


class GetPricesDam():

    def __init__(self) -> None:        
        self.url = 'https://web-api.tp.entsoe.eu/api?securityToken=6276342c-e10c-4d88-8688-cb0a1cf163ca'
        self.prepare_get()

    def prepare_get(self):
        start = 202410220000
        end = 202410230000
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
            print(f"Position {position}: Price = {price} EUR")


