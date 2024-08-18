import json
import datetime
from modules.algo_modules import retrive_weeks52_date_analysis_dict
from modules.indicators import indicators_response
from modules.notification_sending_module import mail_message
import pandas as pd
import threading

# time analysis
time_analysis = {}

# weeks52_date_analysis
start_time = datetime.datetime.now()
print('start_time: ',start_time)
time_analysis['start_time'] = str(start_time)

large_perc_var = 50
mid_perc_var   = 6
small_perc_var = 5
PE_ratio_max   = 25
PE_ratio_min   = 15

backdays = 0
largestocks_52_weeks_date_analysis = {}
midstocks_52_weeks_date_analysis = {}
smallstocks_52_weeks_date_analysis = {}
large_stock_completed = datetime.datetime.now()
mids_stock_completed = datetime.datetime.now()
small_stock_completed = datetime.datetime.now()

lock = threading.Lock()

def large():
    ##############################################
    global largestocks_52_weeks_date_analysis,large_stock_completed
    # with lock:
    largestocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('largestocks',large_perc_var,backdays)
    with open("./stocks_52_week_analysis/largestocks_52_weeks_date_analysis.json", "w") as outfile: 
        json.dump(largestocks_52_weeks_date_analysis, outfile)

    large_stock_completed = datetime.datetime.now()
    print('large_stock_completed: ',large_stock_completed)
    time_analysis['large_stock_completed'] = str(large_stock_completed)
def mid():
    ##############################################
    global midstocks_52_weeks_date_analysis,mids_stock_completed
    # with lock:
    midstocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('midstocks',mid_perc_var,backdays)
    with open("./stocks_52_week_analysis/midstocks_52_weeks_date_analysis.json", "w") as outfile: 
        json.dump(midstocks_52_weeks_date_analysis, outfile)

    mids_stock_completed = datetime.datetime.now()
    print('mids_stock_completed: ',mids_stock_completed)
    time_analysis['mids_stock_completed'] = str(mids_stock_completed)
def small():
    ##############################################
    global smallstocks_52_weeks_date_analysis,small_stock_completed
    # with lock:
    smallstocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('smallstocks',small_perc_var,backdays)
    with open("./stocks_52_week_analysis/smallstocks_52_weeks_date_analysis.json", "w") as outfile: 
        json.dump(smallstocks_52_weeks_date_analysis, outfile)

    small_stock_completed = datetime.datetime.now()
    print('small_stock_completed: ',small_stock_completed)
    time_analysis['small_stock_completed'] = str(small_stock_completed)


t1 = threading.Thread(target=large)
t2 = threading.Thread(target=mid)
t3 = threading.Thread(target=small)

t1.start()
t2.start()
t3.start()

t1.join() 
t2.join()
t3.join()
##############################################


print(' time for large stock = ', large_stock_completed - start_time)
print(' time for mid stock = ', mids_stock_completed - start_time)
print(' time for small stock = ', small_stock_completed - start_time)

print('total time of script run => ', small_stock_completed - start_time)

time_analysis['time_for_large_stock'] = str(large_stock_completed - start_time)
time_analysis['time_for_mid_stock'] = str(mids_stock_completed - start_time)
time_analysis['time_for_small_stock'] = str(small_stock_completed - start_time)
time_analysis['time_for_all_stocks'] = str(small_stock_completed - start_time)


with open("time_analysis_52_weeks.json", "w") as outfile: 
    json.dump(time_analysis, outfile)
    
    
#########################################################################################################

large_capstocksdict = largestocks_52_weeks_date_analysis
mid_capstocksdict = midstocks_52_weeks_date_analysis
small_capstocksdict = smallstocks_52_weeks_date_analysis

# for long term investment
# we will consider PE ratio, sma% and 52 weeks low

# for short term investment
# we will consider ball, rsi, stoch, supertrend along with sma

indicators_data = {
    "company":[],
    "cap":[],
    "closing_price":[],
    "sma":[],
    "sma100":[],
    "sma50":[],
    "sma20":[],
    "sma10":[],
    "ema%":[],
    "sma%":[],
    "PE_ratio":[],
    "ball":[],
    "rsi":[],
    "stoch":[],
    "super_trend":[]
}


def indicator_response_dict_creator(dict_file,cap,backdays=0):
    global indicators_data
    
    for key in dict_file.keys():
        print(key)
        closing_price,sma,sma100,sma50,sma20,sma10,ema,ball,rsi,stoch,super_trend = indicators_response(key,backdays)
        if sma and (stoch!='hold' and rsi!='hold'):
            indicators_data["company"].append(key)
            indicators_data["cap"].append(cap)
            indicators_data["closing_price"].append(closing_price)
            try:
                indicators_data["sma"].append(round(float(sma),2))
                indicators_data["sma%"].append(((closing_price-float(sma))/closing_price)*100)
                indicators_data["sma100"].append(round(sma100,2))
                indicators_data["sma50"].append(round(sma50,2))
                indicators_data["sma20"].append(round(sma20,2))
                indicators_data["sma10"].append(round(sma10,2))
                indicators_data["ema%"].append(((closing_price-float(ema))/closing_price)*100)
            except:
                indicators_data["sma"].append('')
                indicators_data["sma%"].append('')
                indicators_data["sma100"].append('')
                indicators_data["sma50"].append('')
                indicators_data["sma20"].append('')
                indicators_data["sma10"].append('')
                indicators_data["ema%"].append('')
            indicators_data["PE_ratio"].append(dict_file[key]["PE_ratio"])
            indicators_data["ball"].append(ball)
            indicators_data["rsi"].append(rsi)
            indicators_data["stoch"].append(stoch)
            indicators_data["super_trend"].append(super_trend)
        
t4 = threading.Thread(target=indicator_response_dict_creator, args=(large_capstocksdict,'large_cap',backdays,))
t5 = threading.Thread(target=indicator_response_dict_creator, args=(mid_capstocksdict,'mid_cap',backdays,))
t6 = threading.Thread(target=indicator_response_dict_creator, args=(small_capstocksdict,'small_cap',backdays,))

t4.start()
t5.start()
t6.start()

t4.join()
t5.join()
t6.join()

indicators_df = pd.DataFrame(indicators_data)
indicators_df['cap'] = pd.Categorical(indicators_df['cap'],categories = ["large_cap","mid_cap","small_cap"])
indicators_df = indicators_df.sort_values(by=["cap","sma%"])
print(indicators_df)
indicators_df.to_csv(f'./stock_indicators_csv/indicators_data.csv')
indicators_df[indicators_df['cap']=='large_cap'].to_csv(f'./stock_indicators_csv/indicators_data_large_cap.csv')
indicators_df[indicators_df['cap']=='mid_cap'].to_csv(f'./stock_indicators_csv/indicators_data_mid_cap.csv')
indicators_df[indicators_df['cap']=='small_cap'].to_csv(f'./stock_indicators_csv/indicators_data_small_cap.csv')

# sending message
mail_message()