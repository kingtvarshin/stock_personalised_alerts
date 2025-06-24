from complete_stocks_list_extractor import complete_stocks_list_extractor
from fiftytwo_week_analysis_retriever import retrieve_52week_analysis
from indicator_response_generator import load_stocks_indicators_data
from notification_sending_module import mail_message

from constant_vars import  output_json, fiftytwo_weeks_analysis_json, time_analysis_json

import json, os, datetime
from dotenv import load_dotenv

load_dotenv()

# This script extracts stock data from an Excel file and categorizes stocks based on market capitalization.
# The output is saved as a JSON file.
if eval(os.getenv('NEW_EXCEL_FLAG')):
    print("New Excel file detected. Extracting stock data...")
    complete_stocks_list_extractor(os.getenv('EXCEL_NAME'), output_json)

# time analysis
time_analysis = {}

# weeks52_date_analysis
start_time = datetime.datetime.now()
time_analysis['start_time'] = str(start_time)

# Retrieve 52-week analysis for large, mid, and small stocks
retrieve_52week_analysis(output_json, float(os.getenv('LARGE_PERC_VAR')), float(os.getenv('MID_PERC_VAR')), float(os.getenv('SMALL_PERC_VAR')), int(os.getenv('BACKDAYS')))

# Record completion time for 52-week analysis
retrieve_52week_analysis_completed = datetime.datetime.now()
time_analysis['time_for_52week_analysis_completed'] = str(retrieve_52week_analysis_completed)
time_analysis['duration_for_52week_analysis_completed'] = str(retrieve_52week_analysis_completed - start_time)


# for long term investment
# we will consider PE ratio, sma% and 52 weeks low

# for short term investment
# we will consider ball, rsi, stoch, supertrend along with sma
load_stocks_indicators_data(fiftytwo_weeks_analysis_json,int(os.getenv('BACKDAYS')))

# Record completion time for 52-week analysis
retrieve_indicators_data_completed = datetime.datetime.now()
time_analysis['time_for_retrieve_indicators_data_completed'] = str(retrieve_indicators_data_completed)
time_analysis['duration_for_retrieve_indicators_data_completed'] = str(retrieve_indicators_data_completed - retrieve_52week_analysis_completed)
time_analysis['duration_for_compelte_script'] = str(retrieve_indicators_data_completed - start_time)

# Save the time analysis results to a JSON file
with open(time_analysis_json, "w") as outfile: 
    json.dump(time_analysis, outfile)

# sending message
mail_message()