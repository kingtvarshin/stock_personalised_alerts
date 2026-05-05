import json
import datetime
import logging
import sys

from dotenv import load_dotenv
load_dotenv()  # must run before constant_vars imports env vars

from complete_stocks_list_extractor import complete_stocks_list_extractor
from fiftytwo_week_analysis_retriever import retrieve_52week_analysis
from indicator_response_generator import load_stocks_indicators_data
from notification_sending_module import mail_message
from constant_vars import (
    output_json, fiftytwo_weeks_analysis_json, time_analysis_json,
    NEW_EXCEL_FLAG, EXCEL_NAME,
    LARGE_PERC_VAR, MID_PERC_VAR, SMALL_PERC_VAR, BACKDAYS,
)

# --- Logging setup -----------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(name)s -- %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('main')

# --- CLI flags ----------------------------------------------------------------
dry_run = '--dry-run' in sys.argv
if dry_run:
    logger.info('DRY-RUN mode -- pipeline will run normally but NO email will be sent.')

# --- Excel extraction (optional) ---------------------------------------------
if NEW_EXCEL_FLAG:
    logger.info('New Excel file detected. Extracting stock data from %s...', EXCEL_NAME)
    try:
        complete_stocks_list_extractor(EXCEL_NAME, output_json)
    except Exception as e:
        logger.error('Excel extraction failed for EXCEL_NAME="%s": %s', EXCEL_NAME, e, exc_info=True)
        raise SystemExit(1)

# --- Time tracking -----------------------------------------------------------
time_analysis = {}
start_time = datetime.datetime.now()
time_analysis['start_time'] = str(start_time)

# --- 52-week analysis --------------------------------------------------------
logger.info('Running 52-week analysis...')
retrieve_52week_analysis(output_json, LARGE_PERC_VAR, MID_PERC_VAR, SMALL_PERC_VAR, BACKDAYS)

retrieve_52week_analysis_completed = datetime.datetime.now()
time_analysis['time_for_52week_analysis_completed'] = str(retrieve_52week_analysis_completed)
time_analysis['duration_for_52week_analysis_completed'] = str(retrieve_52week_analysis_completed - start_time)

# --- Indicator calculation ---------------------------------------------------
logger.info('Calculating indicators...')
load_stocks_indicators_data(fiftytwo_weeks_analysis_json, BACKDAYS)

retrieve_indicators_data_completed = datetime.datetime.now()
time_analysis['time_for_retrieve_indicators_data_completed'] = str(retrieve_indicators_data_completed)
time_analysis['duration_for_retrieve_indicators_data_completed'] = str(retrieve_indicators_data_completed - retrieve_52week_analysis_completed)
time_analysis['duration_for_compelte_script'] = str(retrieve_indicators_data_completed - start_time)

with open(time_analysis_json, 'w') as outfile:
    json.dump(time_analysis, outfile)

# --- Send mail ---------------------------------------------------------------
mail_message(dry_run=dry_run)
