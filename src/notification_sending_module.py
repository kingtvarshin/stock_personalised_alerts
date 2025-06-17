import smtplib
import datetime
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from constant_vars import indicators_result_csv_path_large, indicators_result_csv_path_mid, indicators_result_csv_path_small, indicators_result_csv_path_full
from dotenv import load_dotenv
import os

def mail_message():
    try:
        load_dotenv()
        EMAIL_ID_LIST = eval(os.getenv('EMAIL_ID_LIST'))
        SENDER_EMAIL = os.getenv('SENDER_EMAIL')
        SENDER_EMAIL_PASSWORD = os.getenv('SENDER_EMAIL_PASSWORD')
        
        df_large=pd.read_csv(indicators_result_csv_path_large)
        df_mid=pd.read_csv(indicators_result_csv_path_mid)
        df_small=pd.read_csv(indicators_result_csv_path_small)
        htmltable_large=df_large.to_html(index=False)
        htmltable_large=htmltable_large.replace('border="1"','border="1" style="border-collapse:collapse"')
        htmltable_mid=df_mid.to_html(index=False)
        htmltable_mid=htmltable_mid.replace('border="1"','border="1" style="border-collapse:collapse"')
        htmltable_small=df_small.to_html(index=False)
        htmltable_small=htmltable_small.replace('border="1"','border="1" style="border-collapse:collapse"')
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
        emailfinal= htmlheader + htmltable_large + htmltable_mid + htmltable_small

        message = MIMEMultipart("alternative")
        message['Subject'] = f"Personlised Stock Alert : {datetime.datetime.now()}"
        message['Mime-Version'] = "1.0"
        message['Content-Type'] = "text/html"

        csv_part = MIMEText(emailfinal, "html")
        message.attach(csv_part)
        
        with open(indicators_result_csv_path_full,'rb') as file:
            # Attach the file with filename to the email
            message.attach(MIMEApplication(file.read(), Name="indicators_data.csv"))
        
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
