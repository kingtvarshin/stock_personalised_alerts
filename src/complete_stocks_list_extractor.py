import pandas as pd
import json

def complete_stocks_list_extractor(excel_name: str = '',
                                   output_json: str = 'stocksdict.json') -> None:
    
    print(f"Extracting stock data from resources/{excel_name} and saving to {output_json}")
    list_of_companies = pd.read_excel(f'resources/{excel_name}')
    stocksdict = {
        "largestocks": [],
        "midstocks": [],
        "smallstocks": []
    }
    
    capitalization_col = [col for col in list_of_companies.columns if ('market capital' in col.lower() or 'in lakh' in col.lower())][0]
    print(f"Using capitalization column: {capitalization_col}")
    for index, company in list_of_companies.iterrows():
        try:
            market_value = company[capitalization_col]
            stock_code = company['Symbol']
            stock_full_name = company['Company Name']
            if market_value > 2000000:
                stocksdict['largestocks'].append({stock_code: stock_full_name})
            elif market_value < 2000000 and market_value > 500000:
                stocksdict['midstocks'].append({stock_code: stock_full_name})
            elif market_value < 500000:
                stocksdict['smallstocks'].append({stock_code: stock_full_name})
            else:
                pass
        except TypeError:
            print(f"Error processing {stock_full_name}: {TypeError}")

    # Serializing json
    stocksdict_json_object = json.dumps(stocksdict, indent=4)
    
    # Writing to stocksdict.json
    with open(output_json, "w") as stocksdictoutfile:
        stocksdictoutfile.write(stocksdict_json_object)