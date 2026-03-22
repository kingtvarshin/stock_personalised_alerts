import os as _os
_dir = _os.path.dirname(_os.path.abspath(__file__))

output_json = _os.path.join(_dir, 'stocksdict.json') # Output JSON file for storing categorized stocks
fiftytwo_weeks_analysis_json = _os.path.join(_dir, 'fiftytwo_weeks_analysis.json') # Output JSON file for storing 52-week analysis results
time_analysis_json = _os.path.join(_dir, 'time_analysis.json') # Output JSON file for storing time analysis results
indicators_data_csv = _os.path.join(_dir, 'indicators_data.csv') # Output CSV file for storing stock indicators data

# for mailing
indicators_result_csv_path_large = _os.path.join(_dir, "indicators_data_large_cap.csv")
indicators_result_csv_path_mid = _os.path.join(_dir, "indicators_data_mid_cap.csv")
indicators_result_csv_path_small = _os.path.join(_dir, "indicators_data_small_cap.csv")
indicators_result_csv_path_full = _os.path.join(_dir, "indicators_data.csv")
