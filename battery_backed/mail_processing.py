import os
import xlrd
import pytz
import pandas as pd
from base64 import urlsafe_b64decode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from mimetypes import guess_type as guess_mime_type
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from datetime import datetime, date, timedelta
from .models import BatterySchedule

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

class GmailService:
    def __init__(self, token_file="token.json", credentials="credentials.json"):        
        
        self.credentials_file = os.path.join(os.getcwd(), credentials)        
        self.service = self.authenticate(token_file, self.credentials_file)
        
    def authenticate(self, token_file, credentials_file):
        creds = None
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_file, "w") as token:
                token.write(creds.to_json())
        return build('gmail', 'v1', credentials=creds)

    def search_messages(self, query):
        result = self.service.users().messages().list(userId='me', q=query).execute()
        messages = result.get('messages', [])
        while 'nextPageToken' in result:
            page_token = result['nextPageToken']
            result = self.service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
            messages.extend(result.get('messages', []))
        return messages

    def parse_parts(self, service, parts, folder_name, message):
        if parts:
            for part in parts:
                filename = part.get("filename")
                mimeType = part.get("mimeType")
                body = part.get("body")
                data = body.get("data")
                file_size = body.get("size")
                part_headers = part.get("headers")

                if part.get("parts"):
                    self.parse_parts(service, part.get("parts"), folder_name, message)
                else:
                    for part_header in part_headers:
                        part_header_name = part_header.get("name")
                        part_header_value = part_header.get("value")
                        if part_header_name == "Content-Disposition":
                            if "attachment" in part_header_value:
                                attachment_id = body.get("attachmentId")
                                attachment = service.users().messages().attachments().get(id=attachment_id, userId='me', messageId=message['id']).execute()
                                data = attachment.get("data")
                                filepath = os.path.join(folder_name, filename)
                                if data:
                                    with open(filepath, "wb") as f:
                                        f.write(urlsafe_b64decode(data))

    def read_message(self, message, price_clearing=False):
        msg = self.service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        payload = msg['payload']
        headers = payload.get("headers")
        parts = payload.get("parts")
        folder_name = "email"
        mail_hour = None
        if headers:
            for header in headers:
                if header.get("name").lower() == "subject":
                    folder_name = "schedules"
                elif header.get("name").lower() == "date":
                    date = header.get("value")
                    local_tz = pytz.timezone('Europe/Sofia')
                    date_obj = datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %z")
                    date_obj = date_obj.astimezone(local_tz)
                    mail_hour = date_obj.hour
               
        print(f"mail_hour:{mail_hour}")
        if price_clearing:
            if mail_hour and mail_hour >=13:  # Filter additional mails with clearings from EnPro
                self.parse_parts(self.service, parts, folder_name, message)
                print("=" * 50)
        else:
            self.parse_parts(self.service, parts, folder_name, message)
            print("=" * 50)

class FileManager:
    def __init__(self) -> None:
        self.devId = ""
        self.file_date = ""
    

    def get_file_name(self, file):
        tomorrow = date.today() - timedelta(days=5) # Use the schedule that is 2 days ago (should adjust it into the search query too)
        d1 = tomorrow.strftime("%Y-%m-%d")
        self.file_date = file.split("_")[1].split(".")[0]
        self.devId = file.split("_")[0]      
        print(f"Name Date: {self.file_date} || {d1}")
        return self.file_date == d1

    def process_files(self):
        try:           
            fn = "schedules"
            for root, dirs, files in os.walk(fn):               
                             
                xlsfiles = [f for f in files if f.endswith('.xls')]                
                for xlsfile in xlsfiles:                    
                    my_file = self.get_file_name(xlsfile)                                               
                    if my_file:                       
                        filepath = os.path.join(fn, xlsfile) 
                        print(f"Filepath is: {filepath}")                       
                        excel_workbook = xlrd.open_workbook(filepath)
                        excel_worksheet = excel_workbook.sheet_by_index(0)  
                        #Day ahead from file date!!!
                        date_obj = datetime.strptime(self.file_date, "%Y-%m-%d")
                        xl_date = date_obj + timedelta(days=1)
                        xl_date_time = str(xl_date) + "T01:15:00"
                        period = (24 * 4) 
                        schedule_list = []
                        i = 0
                        timeIndex = pd.date_range(start=xl_date_time, periods=period, freq="0h15min")
                        while i < period:
                            i += 1
                            xl_schedule = excel_worksheet.cell_value(10, 2 + i)  
                            schedule_list.append(xl_schedule)
                        df = pd.DataFrame(schedule_list, index=timeIndex)
                        df.columns = ['schedule']                        
                        self.save_to_db(df)

        except Exception as e:
            print(f"Error occurred while preparing the Excel file: {e}")
            
    def save_to_db(self, df):
        try:
            first_timestamp = df.index[0] - timedelta(minutes=15) # get the last datapoint before new schedule            
            last_before_new_schedule = BatterySchedule.objects.filter(timestamp__lt=first_timestamp).order_by('-timestamp').first()
            if last_before_new_schedule:
                soc = last_before_new_schedule.soc
            else:
                soc = 0
            for row in df.itertuples():
                invertor = row.schedule          
                flow = invertor/60*15
                soc += flow 
                exist = BatterySchedule.objects.filter(devId=self.devId, timestamp=row.Index)
                if exist:
                    exist.update(invertor=invertor,soc=soc,flow=flow)
                else:
                    BatterySchedule.objects.create(
                    devId=self.devId, 
                    timestamp=row.Index,
                    invertor=invertor,
                    flow=flow,
                    soc=soc
                )                    
        except Exception as e:
            print(f"Error saving status to DB: {e}")

        

class ForecastProcessor:
    def __init__(self):        
        self.gmail_service = GmailService()

    def proceed_forecast(self, clearing=False):
        now = datetime.now() - timedelta(days=5)
        temp_date = datetime.now() - timedelta(days=4)

        after_date = now.strftime("%Y/%m/%d")
        before_date = temp_date.strftime("%Y/%m/%d")
        sender_email = "verzhinia.ivanova@entra.energy"
        query_str = f"from:{sender_email} after:{after_date} before:{before_date}"        
        results = self.gmail_service.search_messages(query_str)
        print(f"Found {len(results)} results.")
        for msg in results:
            self.gmail_service.read_message(msg, price_clearing=clearing)

# if __name__ == "__main__":
#     #processor = ForecastProcessor()
#     file_manager = FileManager()
#     #processor.proceed_forecast(clearing=False)
#     file_manager.process_files()
