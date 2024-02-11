import json
from algo_modules import retrive_weeks52_date_analysis_dict

start_date = "1-02-2024"
end_date ="12-02-2024"

# print(len(stocksdict['largestocks']),len(stocksdict['midstocks']),len(stocksdict['smallstocks']))

largestocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('largestocks', start_date, end_date)
midstocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('midstocks', start_date, end_date)
smallstocks_52_weeks_date_analysis = retrive_weeks52_date_analysis_dict('smallstocks', start_date, end_date)
        
# print(stock_52_weeks_date_analysis)

with open("largestocks_52_weeks_date_analysis.json", "w") as outfile: 
    json.dump(largestocks_52_weeks_date_analysis, outfile)
with open("largestocks_52_weeks_date_analysis.json", "w") as outfile: 
    json.dump(midstocks_52_weeks_date_analysis, outfile)
with open("largestocks_52_weeks_date_analysis.json", "w") as outfile: 
    json.dump(smallstocks_52_weeks_date_analysis, outfile)
