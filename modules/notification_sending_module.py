import smtplib
import datetime
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

def mail_message():
    try:
        load_dotenv()
        EMAIL_ID_LIST = eval(os.getenv('EMAIL_ID_LIST'))
        SENDER_EMAIL = os.getenv('SENDER_EMAIL')
        print(EMAIL_ID_LIST)
        SENDER_EMAIL_PASSWORD = os.getenv('SENDER_EMAIL_PASSWORD')
        INDICATORS_RESULT_CSV_PATH = os.getenv('INDICATORS_RESULT_CSV_PATH')
        
        df=pd.read_csv(INDICATORS_RESULT_CSV_PATH)
        htmltable=df.to_html(index=False)
        htmltable=htmltable.replace('border="1"','border="1" style="border-collapse:collapse"')
        htmlheader='''<html>
            <head>
            <style>
            table.dataframe {
            border: 1px solid #1C6EA4;
            background-color: #EEEEEE;
            text-align: left;
            border-collapse: collapse;
            }
            table.dataframe td, table.dataframe th {
            border: 1px solid #AAAAAA;
            padding: 3px 2px;
            }
            table.dataframe tbody td {
            font-size: 13px;
            }
            table.dataframe tr:nth-child(even) {
            background: #D0E4F5;
            }
            table.dataframe thead {
            background: #1C6EA4;
            background: -moz-linear-gradient(top, #5592bb 0%, #327cad 66%, #1C6EA4 100%);
            background: -webkit-linear-gradient(top, #5592bb 0%, #327cad 66%, #1C6EA4 100%);
            background: linear-gradient(to bottom, #5592bb 0%, #327cad 66%, #1C6EA4 100%);
            border-bottom: 2px solid #444444;
            }
            table.dataframe thead th {
            font-size: 15px;
            font-weight: bold;
            color: #FFFFFF;
            border-left: 2px solid #D0E4F5;
            }
            table.dataframe thead th:first-child {
            border-left: none;
            }

            table.dataframe tfoot {
            font-size: 14px;
            font-weight: bold;
            color: #FFFFFF;
            background: #D0E4F5;
            background: -moz-linear-gradient(top, #dcebf7 0%, #d4e6f6 66%, #D0E4F5 100%);
            background: -webkit-linear-gradient(top, #dcebf7 0%, #d4e6f6 66%, #D0E4F5 100%);
            background: linear-gradient(to bottom, #dcebf7 0%, #d4e6f6 66%, #D0E4F5 100%);
            border-top: 2px solid #444444;
            }
            table.dataframe tfoot td {
            font-size: 14px;
            }
            table.dataframe tfoot .links {
            text-align: right;
            }
            table.dataframe tfoot .links a{
            display: inline-block;
            background: #1C6EA4;
            color: #FFFFFF;
            padding: 2px 8px;
            border-radius: 5px;
            }

            </style>
        '''
        emailfinal= htmlheader + htmltable

        message = MIMEMultipart("alternative")
        message['Subject'] = f"Personlised Stock Alert : {datetime.datetime.now()}"
        message['Mime-Version'] = "1.0"
        message['Content-Type'] = "text/html"

        csv_part = MIMEText(emailfinal, "html")
        message.attach(csv_part)
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(SENDER_EMAIL, SENDER_EMAIL_PASSWORD)
        s.sendmail(SENDER_EMAIL, EMAIL_ID_LIST, message.as_string())
        print('sent message')
        s.quit()
    except smtplib.SMTPServerDisconnected:
        raise smtplib.SMTPServerDisconnected
    except smtplib.SMTPResponseException:
        raise smtplib.SMTPResponseException
    except smtplib.SMTPRecipientsRefused:
        raise smtplib.SMTPRecipientsRefused
    except smtplib.SMTPNotSupportedError:
        raise smtplib.SMTPNotSupportedError
