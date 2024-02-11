import json
import datetime
from algo_modules import retrive_weeks52_date_analysis_dict

# weeks52_date_analysis

start_time = datetime.datetime.now()
print('start_time: ',start_time)

##############################################
largestocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('largestocks')
with open("largestocks_52_weeks_date_analysis.json", "w") as outfile: 
    json.dump(largestocks_52_weeks_date_analysis, outfile)

large_stock_completed = datetime.datetime.now()
print('large_stock_completed: ',large_stock_completed)

##############################################
midstocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('midstocks')
with open("midstocks_52_weeks_date_analysis.json", "w") as outfile: 
    json.dump(midstocks_52_weeks_date_analysis, outfile)

mids_stock_completed = datetime.datetime.now()
print('mids_stock_completed: ',mids_stock_completed)

##############################################
smallstocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('smallstocks')
with open("smallstocks_52_weeks_date_analysis.json", "w") as outfile: 
    json.dump(smallstocks_52_weeks_date_analysis, outfile)

small_stock_completed = datetime.datetime.now()
print('small_stock_completed: ',small_stock_completed)

##############################################


print(' time for large stock = ', large_stock_completed - start_time)
print(' time for mid stock = ', mids_stock_completed - large_stock_completed)
print(' time for small stock = ', small_stock_completed - mids_stock_completed)

print('total time of script run => ', small_stock_completed - start_time)