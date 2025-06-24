import json
import asyncio
from nsepython import nse_eq
from constant_vars import fiftytwo_weeks_analysis_json
from tqdm.asyncio import tqdm_asyncio


def retrieve_52week_analysis(output_json, large_perc_var, mid_perc_var, small_perc_var, backdays):
    with open(output_json) as stocksdictfile:
        stocksdict = json.load(stocksdictfile)

    stock_list = []
    for category, stocks in stocksdict.items():
        label = category.replace("stocks", "").lower()
        for entry in stocks:
            for symbol in entry:
                stock_list.append({"symbol": symbol, "category": label})

    async def worker(stock_info, sem):
        async with sem:
            symbol = stock_info["symbol"]
            category = stock_info["category"]

            # Assign threshold based on category
            if category == "large":
                threshold = large_perc_var
            elif category == "mid":
                threshold = mid_perc_var
            elif category == "small":
                threshold = small_perc_var
            else:
                threshold = large_perc_var  # default fallback

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
                if 0 < perc_high < threshold:
                    result['perc_high'] = perc_high
                    result['PE_ratio'] = PE_ratio
                if 0 < perc_low < threshold:
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
        sem = asyncio.Semaphore(5)
        tasks = [worker(stock, sem) for stock in stock_list]
        results = await tqdm_asyncio.gather(*tasks, desc="Processing Stocks", total=len(stock_list))

        final_result = {}
        for r in results:
            final_result.update(r)
        return final_result

    results = asyncio.run(run_all())

    with open(fiftytwo_weeks_analysis_json, "w") as outfile:
        json.dump(results, outfile, indent=2)
