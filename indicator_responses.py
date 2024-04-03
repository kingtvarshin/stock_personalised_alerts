import json
from modules.indicators import indicators_response
import pandas as pd

large_capstocksdictfile = open('./stocks_52_week_analysis/largestocks_52_weeks_date_analysis.json')
large_capstocksdict = json.load(large_capstocksdictfile)
mid_capstocksdictfile = open('./stocks_52_week_analysis/midstocks_52_weeks_date_analysis.json')
mid_capstocksdict = json.load(mid_capstocksdictfile)
small_capstocksdictfile = open('./stocks_52_week_analysis/smallstocks_52_weeks_date_analysis.json')
small_capstocksdict = json.load(small_capstocksdictfile)


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
