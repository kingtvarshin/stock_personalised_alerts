import json
import datetime
from modules.algo_modules import retrive_weeks52_date_analysis_dict
from modules.indicators import indicators_response
import pandas as pd

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
    
############################################################################################################### 

# large_capstocksdictfile = open('./stocks_52_week_analysis/largestocks_52_weeks_date_analysis.json')
# large_capstocksdict = json.load(large_capstocksdictfile)
large_capstocksdict = largestocks_52_weeks_date_analysis
# mid_capstocksdictfile = open('./stocks_52_week_analysis/midstocks_52_weeks_date_analysis.json')
# mid_capstocksdict = json.load(mid_capstocksdictfile)
mid_capstocksdict = midstocks_52_weeks_date_analysis
# small_capstocksdictfile = open('./stocks_52_week_analysis/smallstocks_52_weeks_date_analysis.json')
# small_capstocksdict = json.load(small_capstocksdictfile)
small_capstocksdict = smallstocks_52_weeks_date_analysis


indicators_data = {
    "company":[],
    "cap":[],
    "closing_price":[],
    "sma":[],
    "ball":[],
    "rsi":[],
    "stoch":[],
    "super_trend":[]
    
}

def indicator_response_dict_creator(dict_file,cap):
    
    for key in dict_file.keys():
        print(key)
        closing_price,sma,ball,rsi,stoch,super_trend = indicators_response(key)
        indicators_data["company"].append(key)
        indicators_data["cap"].append(cap)
        indicators_data["closing_price"].append(closing_price)
        indicators_data["sma"].append(sma)
        indicators_data["ball"].append(ball)
        indicators_data["rsi"].append(rsi)
        indicators_data["stoch"].append(stoch)
        indicators_data["super_trend"].append(super_trend)

indicator_response_dict_creator(large_capstocksdict,'large_cap')
indicator_response_dict_creator(mid_capstocksdict,'mid_cap')
indicator_response_dict_creator(small_capstocksdict,'small_cap')

indicators_df = pd.DataFrame(indicators_data)
indicators_df.to_csv(f'./stock_indicators_csv/indicators_data.csv')