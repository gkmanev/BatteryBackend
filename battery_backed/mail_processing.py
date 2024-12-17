import os
import xlrd
import pytz
import pandas as pd
import mimetypes
import base64
from base64 import urlsafe_b64decode
from email.mime.application import MIMEApplication
from email import encoders
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
import openpyxl

#SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]

class GmailService:
    def __init__(self, token_file="token.json", credentials="credentials.json"):  

        self.scopes = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]
        self.credentials_file = os.path.join(os.getcwd(), credentials)        
        self.service = self.authenticate(token_file, self.credentials_file)
        self.files_names_array = []
        
    def authenticate(self, token_file, credentials_file):
        creds = None
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.scopes)
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

    def parse_parts(self, service, parts, folder_name, mail_date, message):
        if parts:
            for part in parts:
                filename = part.get("filename")
                mimeType = part.get("mimeType")
                body = part.get("body")
                data = body.get("data")
                file_size = body.get("size")
                part_headers = part.get("headers")
                

                if part.get("parts"):
                    self.parse_parts(service, part.get("parts"), folder_name, mail_date, message)
                else:                    
                    for part_header in part_headers:                        
                        part_header_name = part_header.get("name")
                        part_header_value = part_header.get("value")                        
                        if part_header_name == "Content-Disposition":
                            if "attachment" in part_header_value:                                
                                
                                attachment_id = body.get("attachmentId")
                                attachment = service.users().messages().attachments().get(id=attachment_id, userId='me', messageId=message['id']).execute()
                                data = attachment.get("data")                                
                                self.files_names_array.append({
                                    "filename":{
                                        "file_name":filename,
                                        "mail_date":mail_date,
                                        "data":data
                                        }
                                })                                                              
                                # if data:                                    
                                #     with open(filepath, "wb") as f:
                                #         f.write(urlsafe_b64decode(data))
            

    

    def read_message(self, message, price_clearing=False):
        
        msg = self.service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        payload = msg['payload']
        headers = payload.get("headers")
        parts = payload.get("parts")        
        folder_name = "email"
        mail_hour = None
        mail_date = None
        if headers: 
            for header in headers: 
                if header.get("name").lower() == "subject":
                    folder_name = "schedules"
                elif header.get("name").lower() == "date":
                    mail_date = header.get("value") 
                    #print(f"MAIL DATE IS: {date}")                  
                    local_tz = pytz.timezone('Europe/Sofia')
                    date_obj = datetime.strptime(mail_date, "%a, %d %b %Y %H:%M:%S %z")
                    date_obj = date_obj.astimezone(local_tz)
                    mail_hour = date_obj.hour               
        
        if price_clearing:
            if mail_hour and mail_hour >=13:  # Filter additional mails with clearings from EnPro
                self.parse_parts(self.service, parts, folder_name, mail_date, message)
                print("=" * 50)
        else:                                  
            self.parse_parts(self.service, parts, folder_name, mail_date, message)
            print("=" * 50)
    
    
    def create_message_with_attachment(self, sender, to, subject, message_text, file_path, file_name):
        # Create the base message
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject

        # Add the message body
        msg = MIMEText(message_text)
        message.attach(msg)

        # Add the attachment
        with open(file_path, 'rb') as f:
            mime_base = MIMEBase('application', 'octet-stream')
            mime_base.set_payload(f.read())
            encoders.encode_base64(mime_base)
            mime_base.add_header('Content-Disposition', f'attachment; filename="{file_name}"')
            message.attach(mime_base)

        # Encode the message in base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw_message}
    
    def send_message(self, user_id, message):
        try:
            message = self.service.users().messages().send(userId=user_id, body=message).execute()
            print(f'Message Id: {message["id"]}')
            return message
        except Exception as error:
            print(f'An error occurred: {error}')
            return None

class FileManager:
    def __init__(self) -> None:
        self.devId = ""
        self.file_date = ""
    

    def get_file_name(self, file):
        # tomorrow = date.today() + timedelta(days=1) #- timedelta(days=5) # Use the schedule that is # days ago (should adjust it into the search query too)
        # d1 = tomorrow.strftime("%Y-%m-%d")
        # self.file_date = file.split("_")[1].split(".")[0]
        # self.devId = file.split("_")[0]      
        # print(f"Name Date: {self.file_date} || {d1}")
        # return self.file_date == d1
        print(file)
        today = date.today()
        today_date = today.strftime("%Y-%m-%d")       
        try:
            self.file_date = file.split("_")[1].split(".")[0]
            batt_number_part = file.split("_")[0].split("batt")[1]
            self.devId = f"batt-000{batt_number_part}" 
            if self.file_date >= today_date:            
                return True
            else:
                return False
        except Exception as e:
            print(f"There is a file with not valid name!:{e}")


    def process_files(self):
        try:
            fn = "schedules"
            for root, dirs, files in os.walk(fn):
                xlsfiles = [f for f in files if f.endswith(('.xls', '.xlsx'))]  # Include .xlsx files as well
                
                for xlsfile in xlsfiles:                    
                    my_file = self.get_file_name(xlsfile)
                    
                    if my_file:
                        
                        filepath = os.path.join(fn, xlsfile)
                        
                        # Determine file format and use appropriate library
                        if xlsfile.endswith('.xlsx'):
                            excel_workbook = openpyxl.load_workbook(filepath)
                            excel_worksheet = excel_workbook.active
                            # Use openpyxl cell access syntax
                            get_cell_value = lambda row, col: excel_worksheet.cell(row=row, column=col).value
                        else:
                            excel_workbook = xlrd.open_workbook(filepath)
                            excel_worksheet = excel_workbook.sheet_by_index(0)
                            # Use xlrd cell access syntax
                            get_cell_value = lambda row, col: excel_worksheet.cell_value(row - 1, col - 1)  # 0-indexed

                        # Process the worksheet as before...
                        date_obj = datetime.strptime(self.file_date, "%Y-%m-%d")
                        xl_date = date_obj
                        xl_date_time = str(xl_date)# + "T01:15:00"
                        period = (24 * 4)  # 4 periods per day (every 15 minutes)
                        schedule_list = []
                        timeIndex = pd.date_range(start=xl_date_time, periods=period, freq="0h15min", tz="UTC")
                        
                        for i in range(1, period + 1):
                            xl_schedule = get_cell_value(11, 3 + i)  # Adjust row/column as needed
                            schedule_list.append(xl_schedule)                        
                        df = pd.DataFrame(schedule_list, index=timeIndex)
                        df.columns = ['schedule']                        
                        self.save_to_db(df)

        except Exception as e:
            print(f"Error occurred while preparing the Excel file: {e}")
                
    def save_to_db(self, df):
        try:
            # first_timestamp = df.index[0] - timedelta(minutes=15) # get the last datapoint before new schedule            
            # last_before_new_schedule = BatterySchedule.objects.filter(timestamp__lt=first_timestamp).order_by('-timestamp').first()
            # if last_before_new_schedule:
            #     soc = last_before_new_schedule.soc
            # else:
            soc = 0
            existing_soc = 0
            for row in df.itertuples():
                invertor = row.schedule          
                flow = invertor/60*15
                soc += flow 
                exist = BatterySchedule.objects.filter(devId=self.devId, timestamp=row.Index)
                if exist:                    
                    now = datetime.now(tz=pytz.UTC)                 
                    # if row.Index > now:
                    existing_flow = invertor/60*15
                    existing_soc += existing_flow
                    print(f"Exist Found: {row.Index} || Invertor: {invertor} || DevId: {self.devId} || TimeNow: {now}")
                    exist.update(invertor=invertor,soc=existing_soc,flow=existing_flow)
                else:
                    print(f"Exist NOT Found: {row.Index}")
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

    def create_files_from_attachments(self):
        # Create files from the collected attachment data in files_names_array
        for file_info in self.gmail_service.files_names_array:
            file_data = file_info['filename']['data']
            file_name = file_info['filename']['file_name']
            mail_date = file_info['filename']['mail_date']
            
            # Define the file path where the attachment should be saved
            folder_name = "schedules"
            filepath = os.path.join(folder_name, file_name)

            # Ensure folder exists
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)

            # Write the decoded data to a file
            with open(filepath, "wb") as f:
                f.write(urlsafe_b64decode(file_data))

            print(f"Attachment saved: {filepath}")

    def proceed_forecast(self, clearing=False):
        now = datetime.now() - timedelta(days=1)
        #temp_date = datetime.now() - timedelta(days=4)

        after_date = now.strftime("%Y/%m/%d")
        #before_date = temp_date.strftime("%Y/%m/%d")
        sender_email = "grid.elasticity@entra.energy"
        query_str = f"from:{sender_email} after:{after_date}"        
        results = self.gmail_service.search_messages(query_str)
        print(f"Found {len(results)} results.")
        for msg in reversed(results):            
            self.gmail_service.read_message(msg, price_clearing=clearing)

        print(f"There are {len(self.gmail_service.files_names_array)} attachements ")
        self.create_files_from_attachments()

# if __name__ == "__main__":
#     #processor = ForecastProcessor()
#     file_manager = FileManager()
#     #processor.proceed_forecast(clearing=False)
#     file_manager.process_files()
