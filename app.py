import pandas as pd
import json
from nsepython import nse_eq,equity_history,nse_holidays

# importing the dictionary for stocks requirements
stocksdictfile = open('./stocksdict.json')
stocksdict = json.load(stocksdictfile)

start_date = "1-02-2024"
end_date ="12-02-2024"

# print(len(stocksdict['largestocks']),len(stocksdict['midstocks']),len(stocksdict['smallstocks']))

stock_52_weeks_date_analysis = {}

# iterating for each stock in the list
for stock in stocksdict['largestocks']:
    stock_code = list(stock.keys())[0]
    stock_full_name = list(stock.values())[0]
    print('running stock_code',stock_code)
    # stock_history = equity_history(stock_code,"EQ",start_date,end_date)
    try: 
        stock_history = equity_history(stock_code,"EQ",start_date,end_date).sort_values(
                by=['TIMESTAMP'],ascending=False,ignore_index=True)[
                    [
                        'CH_SYMBOL', 'CH_TRADE_HIGH_PRICE', 'CH_TRADE_LOW_PRICE', 'CH_OPENING_PRICE',
                        'CH_CLOSING_PRICE', 'CH_LAST_TRADED_PRICE', 'CH_PREVIOUS_CLS_PRICE',
                        'CH_52WEEK_HIGH_PRICE', 'CH_52WEEK_LOW_PRICE'
                    ]
                ]
        # print(stock_history)
        weeks52_high = stock_history['CH_52WEEK_HIGH_PRICE'].loc[0]
        weeks52_low = stock_history['CH_52WEEK_LOW_PRICE'].loc[0]
        todays_high = stock_history['CH_TRADE_HIGH_PRICE'].loc[0]
        todays_low = stock_history['CH_TRADE_LOW_PRICE'].loc[0]
        # print(weeks52_high,todays_high, weeks52_low,todays_low)
        perc_high = ((weeks52_high - todays_high)/weeks52_high)*100
        perc_low = ((todays_low - weeks52_low)/weeks52_low)*100
        # if perc_high < 1:
        #     stock_52_weeks_date_analysis[stock_code] = {'perc_high': perc_high}
        #     print('near high: ',stock_code)
        #     print('perc_high: ',perc_high)
        if perc_low < 1:
            print(stock_history)
            stock_52_weeks_date_analysis[stock_code] = {'perc_low': perc_low}
            print('near low: ',stock_code)
            print('perc_low: ',perc_low)
        # break
    except KeyError:
        stock_history = equity_history(stock_code,"EQ",start_date,end_date)
        print(stock_history.columns)
        print(KeyError)
    except json.JSONDecodeError:
        stock_history = equity_history(stock_code,"EQ",start_date,end_date)
        print(stock_history.columns)
        print(json.JSONDecodeError)
        

# print(stock_52_weeks_date_analysis)

with open("sample.json", "w") as outfile: 
    json.dump(stock_52_weeks_date_analysis, outfile)



# # print(nse_eq("JUSTDIAL"))
# a = json.dumps(nse_eq(stock_code), indent = 4)
# print(a)




#closing file
stocksdictfile.close()