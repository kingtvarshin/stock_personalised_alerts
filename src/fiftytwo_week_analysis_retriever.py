import json
import asyncio
import aiohttp
from nsepython import equity_history,nse_eq
from constant_vars import fiftytwo_weeks_analysis_json

def retrieve_52week_analysis(output_json, large_perc_var, mid_perc_var, small_perc_var,  backdays):
    # importing the dictionary for stocks requirements
    stocksdictfile = open(output_json)
    stocksdict = json.load(stocksdictfile)

    # Step 1: Flatten into list of {"symbol": ..., "category": ...}
    stock_list = []
    for category, stocks in stocksdict.items():
        label = category.replace("stocks", "")  # "largestocks" → "large"
        for entry in stocks:
            for symbol in entry:
                stock_list.append({"symbol": symbol, "category": label})

    async def worker(stock_info):
        symbol = stock_info["symbol"]
        category = stock_info["category"]
        try:
            stock_data = await asyncio.to_thread(nse_eq, symbol)

            weeks52_high = stock_data['priceInfo']['weekHighLow']['max']
            weeks52_low = stock_data['priceInfo']['weekHighLow']['min']
            todays_high = stock_data['priceInfo']['intraDayHighLow']['max']
            todays_low = stock_data['priceInfo']['intraDayHighLow']['min']
            PE_ratio = stock_data['metadata']['pdSectorPe']

            perc_high = ((weeks52_high - todays_low) / weeks52_high) * 100
            perc_low = ((todays_high - weeks52_low) / weeks52_low) * 100

            result = {}
            if 0 < perc_high < large_perc_var:
                result['perc_high'] = perc_high
                result['PE_ratio'] = PE_ratio

            if 0 < perc_low < large_perc_var:
                result['perc_low'] = perc_low
                result['PE_ratio'] = PE_ratio

            if result:
                result['category'] = category
                return {symbol: result}
            return {}

        except Exception as e:
            print(f"Error with {symbol}: {e}")
            return {}

    async def run_all():
        tasks = [worker(stock) for stock in stock_list]
        results = await asyncio.gather(*tasks)

        final_result = {}
        for r in results:
            final_result.update(r)
        return final_result

    results = asyncio.run(run_all())
    with open(fiftytwo_weeks_analysis_json, "w") as outfile: 
        json.dump(results, outfile)