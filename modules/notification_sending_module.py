import pandas as pd
import json

JSONFILEPATH_LARGESTOCK = './stocks_52_week_analysis/largestocks_52_weeks_date_analysis.json'
JSONFILEPATH_MIDSTOCK = './stocks_52_week_analysis/midstocks_52_weeks_date_analysis.json'
JSONFILEPATH_SMALLSTOCK = './stocks_52_week_analysis/smallstocks_52_weeks_date_analysis.json'

def json_transfrom_to_dataframe(json_file):
    analysis_json = open(json_file)
    analysis_dict = json.load(analysis_json)
    data = {
        'STOCK_NAME': list(analysis_dict.keys()),
        'percentage_LOW' : [x['perc_low'] for x in list(analysis_dict.values())]
    }
    df = pd.DataFrame.from_dict(data)
    return df.sort_values(by=['percentage_LOW'], ignore_index=True)

largestocks_result_df = json_transfrom_to_dataframe(JSONFILEPATH_LARGESTOCK)
midstocks_result_df = json_transfrom_to_dataframe(JSONFILEPATH_MIDSTOCK)
smallstocks_result_df = json_transfrom_to_dataframe(JSONFILEPATH_SMALLSTOCK)

print(largestocks_result_df)
print(midstocks_result_df)
print(smallstocks_result_df)