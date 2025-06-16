from complete_stocks_list_extractor import complete_stocks_list_extractor
from fiftytwo_week_analysis_retriever import retrieve_52week_analysis
from constant_vars import excel_name, output_json, large_perc_var, mid_perc_var, small_perc_var, PE_ratio_max, PE_ratio_min, backdays, time_analysis_json

import datetime
import json

new_excel_flag = False

# This script extracts stock data from an Excel file and categorizes stocks based on market capitalization.
# The output is saved as a JSON file.
if new_excel_flag:
    print("New Excel file detected. Extracting stock data...")
    complete_stocks_list_extractor(excel_name, output_json)

# time analysis
time_analysis = {}

# weeks52_date_analysis
start_time = datetime.datetime.now()
time_analysis['start_time'] = str(start_time)

# Retrieve 52-week analysis for large, mid, and small stocks
retrieve_52week_analysis(output_json, large_perc_var, mid_perc_var, small_perc_var, backdays)

# Record completion time for 52-week analysis
retrieve_52week_analysis_completed = datetime.datetime.now()
time_analysis['time_for_52week_analysis_completed'] = str(retrieve_52week_analysis_completed)
time_analysis['duration_for_52week_analysis_completed'] = str(retrieve_52week_analysis_completed - start_time)


# for long term investment
# we will consider PE ratio, sma% and 52 weeks low

# for short term investment
# we will consider ball, rsi, stoch, supertrend along with sma
# indicator_response_dict_creator(dict_file,cap,backdays=0)

# Save the time analysis results to a JSON file
with open(time_analysis_json, "w") as outfile: 
    json.dump(time_analysis, outfile)