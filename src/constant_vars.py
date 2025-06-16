excel_name = 'Average MCAP_July2024ToDecember 2024.xlsx' # Name of the Excel file containing stock data
output_json = 'stocksdict.json' # Output JSON file for storing categorized stocks
fiftytwo_weeks_analysis_json = 'fiftytwo_weeks_analysis.json' # Output JSON file for storing 52-week analysis results
time_analysis_json = 'time_analysis.json' # Output JSON file for storing time analysis results
indicators_data_csv = 'indicators_data.csv' # Output CSV file for storing stock indicators data

# Percentage variation from 52 weeks low and high thresholds for stock categorization
large_perc_var = 16
mid_perc_var   = 6
small_perc_var = 5

# Maximum and minimum P/E ratio for stock selection
PE_ratio_max   = 25
PE_ratio_min   = 15

backdays = 0 # Number of days to look back for stock data analysis, 0 means current day

