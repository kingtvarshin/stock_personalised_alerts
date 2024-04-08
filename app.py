import json
import datetime
from modules.algo_modules import retrive_weeks52_date_analysis_dict

# time analysis
time_analysis = {}

# weeks52_date_analysis
start_time = datetime.datetime.now()
print('start_time: ',start_time)
time_analysis['start_time'] = str(start_time)

perc_var = 5

##############################################
largestocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('largestocks',perc_var)
with open("./stocks_52_week_analysis/largestocks_52_weeks_date_analysis.json", "w") as outfile: 
    json.dump(largestocks_52_weeks_date_analysis, outfile)

large_stock_completed = datetime.datetime.now()
print('large_stock_completed: ',large_stock_completed)
time_analysis['large_stock_completed'] = str(large_stock_completed)

##############################################
midstocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('midstocks',perc_var)
with open("./stocks_52_week_analysis/midstocks_52_weeks_date_analysis.json", "w") as outfile: 
    json.dump(midstocks_52_weeks_date_analysis, outfile)

mids_stock_completed = datetime.datetime.now()
print('mids_stock_completed: ',mids_stock_completed)
time_analysis['mids_stock_completed'] = str(mids_stock_completed)

##############################################
smallstocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('smallstocks',perc_var)
with open("./stocks_52_week_analysis/smallstocks_52_weeks_date_analysis.json", "w") as outfile: 
    json.dump(smallstocks_52_weeks_date_analysis, outfile)

small_stock_completed = datetime.datetime.now()
print('small_stock_completed: ',small_stock_completed)
time_analysis['small_stock_completed'] = str(small_stock_completed)

##############################################


print(' time for large stock = ', large_stock_completed - start_time)
print(' time for mid stock = ', mids_stock_completed - large_stock_completed)
print(' time for small stock = ', small_stock_completed - mids_stock_completed)

print('total time of script run => ', small_stock_completed - start_time)

time_analysis['time_for_large_stock'] = str(large_stock_completed - start_time)
time_analysis['time_for_mid_stock'] = str(mids_stock_completed - large_stock_completed)
time_analysis['time_for_small_stock'] = str(small_stock_completed - mids_stock_completed)
time_analysis['time_for_all_stocks'] = str(small_stock_completed - start_time)


with open("time_analysis_52_weeks.json", "w") as outfile: 
    json.dump(time_analysis, outfile)
