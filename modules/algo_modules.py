import json
from requests import JSONDecodeError
from nsepython import equity_history,nse_eq
import datetime

def retrive_weeks52_date_analysis_dict(stock_type_key,perc_var=5,backdays=0):
    # importing the dictionary for stocks requirements
    stocksdictfile = open('./one_time_scripts/stocksdict.json')
    stocksdict = json.load(stocksdictfile)
    weeks52_date_analysis = {}
    
    # iterating for each stock in the list
    for stock in stocksdict[stock_type_key]:
        stock_code = list(stock.keys())[0]
        print('running stock_code',stock_code)
        try: 
            stock_data     = nse_eq(stock_code)
            if backdays != 0 :
                series         = "EQ"
                end_datetime   = datetime.datetime.now() - datetime.timedelta(days=backdays)
                start_datetime = end_datetime - datetime.timedelta(days=2)
                end_date       = f'{end_datetime.day}-{end_datetime.month}-{end_datetime.year}'
                start_date     = f'{start_datetime.day}-{start_datetime.month}-{start_datetime.year}'
                eh             = equity_history(stock_code,series,start_date,end_date).sort_values(by=['CH_TIMESTAMP'], ascending=False, ignore_index=True).iloc[0]
                weeks52_high   = eh['CH_52WEEK_HIGH_PRICE'] 
                weeks52_low    = eh['CH_52WEEK_LOW_PRICE']
                todays_high    = eh['CH_TRADE_HIGH_PRICE']
                todays_low     = eh['CH_TRADE_LOW_PRICE']
            else:
                weeks52_high   = stock_data['priceInfo']['weekHighLow']['max']
                weeks52_low    = stock_data['priceInfo']['weekHighLow']['min']
                todays_high    = stock_data['priceInfo']['intraDayHighLow']['max']
                todays_low     = stock_data['priceInfo']['intraDayHighLow']['min']
            perc_high      = ((weeks52_high - todays_low)/weeks52_high)*100
            perc_low       = ((todays_high - weeks52_low)/weeks52_low)*100
            PE_ratio       = stock_data['metadata']['pdSectorPe']
            # if perc_high < perc_var and perc_high > 0:
            #     weeks52_date_analysis[stock_code] = {'perc_high': perc_high,'PE_ratio':PE_ratio}
            #     print('near high: ',stock_code)
            #     print('perc_high: ',perc_high)
            if perc_low < perc_var and perc_low > 0:
                # print(stock_data)
                weeks52_date_analysis[stock_code] = {'perc_low': perc_low,'PE_ratio':PE_ratio}
        except KeyError:
            stock_data = nse_eq(stock_code)
            print(KeyError,stock_data)
        except JSONDecodeError:
            stock_data = nse_eq(stock_code)
            print(JSONDecodeError,stock_data)
        except ZeroDivisionError:
            stock_data = nse_eq(stock_code)
            print(JSONDecodeError,stock_data)
    #closing file
    stocksdictfile.close()
    return weeks52_date_analysis
