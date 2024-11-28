from django.core.management.base import BaseCommand
from datetime import timedelta
from battery_backed.models import BatterySchedule
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
import openpyxl
from battery_backed.mail_processing import GmailService, FileManager, ForecastProcessor

class Command(BaseCommand):
    help = 'Empty db'

    def handle(self, *args, **kwargs):
        
        processor = ForecastProcessor()
        processor.proceed_forecast(clearing=False)
        file_manager = FileManager()
        file_manager.process_files()       

        self.stdout.write(self.style.SUCCESS('Command RUN'))
