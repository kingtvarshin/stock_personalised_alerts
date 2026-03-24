import os as _os
import json as _json
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
sector_analysis_csv = _os.path.join(_dir, "sector_analysis.csv")

# ── Environment variable reads — single source of truth ──────────────────────
# All modules import from here; no module should call os.getenv() directly.

def _bool_env(key, default=False):
    """Parse a boolean env var. Accepts 'true'/'1'/'yes' (case-insensitive)."""
    return _os.getenv(key, str(default)).strip().lower() in ('true', '1', 'yes')

def _float_env(key, default=0.0):
    try:
        return float(_os.getenv(key, default))
    except (TypeError, ValueError):
        return default

def _int_env(key, default=0):
    try:
        return int(_os.getenv(key, default))
    except (TypeError, ValueError):
        return default

def _list_env(key, default=None):
    """Parse a JSON-array env var safely (no eval)."""
    raw = _os.getenv(key, '')
    if not raw:
        return default or []
    try:
        return _json.loads(raw)
    except _json.JSONDecodeError:
        return default or []

# Loaded at import time (after dotenv is called in the entry point)
NEW_EXCEL_FLAG     = _bool_env('NEW_EXCEL_FLAG', False)
EXCEL_NAME         = _os.getenv('EXCEL_NAME', '')
LARGE_PERC_VAR     = _float_env('LARGE_PERC_VAR', 16.0)
MID_PERC_VAR       = _float_env('MID_PERC_VAR', 6.0)
SMALL_PERC_VAR     = _float_env('SMALL_PERC_VAR', 5.0)
BACKDAYS           = _int_env('BACKDAYS', 0)
PE_RATIO_MAX       = _float_env('PE_RATIO_MAX', 25.0)
PE_RATIO_MIN       = _float_env('PE_RATIO_MIN', 15.0)
GROQ_API_KEY       = _os.getenv('GROQ_API_KEY', '').strip()
SENDER_EMAIL       = _os.getenv('SENDER_EMAIL', '')
SENDER_EMAIL_PASS  = _os.getenv('SENDER_EMAIL_PASSWORD', '')
EMAIL_RECIPIENTS   = _list_env('EMAIL_ID_LIST', [])
