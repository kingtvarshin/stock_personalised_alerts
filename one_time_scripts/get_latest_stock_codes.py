import pandas as pd
import json 
excel_name = 'MCAP31122023.xlsx'
list_of_companies = pd.read_excel(excel_name)
stocksdict = {
    "largestocks" : [],
    "midstocks" : [],
    "smallstocks" : []
}
for index,company in list_of_companies.iterrows():
    try:
        market_value = company['Market capitalization as on December 31, 2023\n(In Lakhs)']
        stock_code = company['Symbol']
        stock_full_name = company['Company Name']
        if market_value > 2000000:
            stocksdict['largestocks'].append({stock_code:stock_full_name})
        elif market_value < 2000000 and market_value > 500000:
            stocksdict['midstocks'].append({stock_code:stock_full_name})
        elif market_value < 500000:
            stocksdict['smallstocks'].append({stock_code:stock_full_name})
        else:
            pass
    except TypeError:
        print(stock_full_name)
        print(TypeError)
    
# Serializing json
stocksdict_json_object = json.dumps(stocksdict, indent=4)
# Writing to stocksdict.json
with open("stocksdict.json", "w") as stocksdictoutfile:
    stocksdictoutfile.write(stocksdict_json_object)