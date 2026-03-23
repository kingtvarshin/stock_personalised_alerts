import json, os, asyncio, datetime, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import yfinance as yf
from stock_indicators import indicators, Quote
from stock_indicators import CandlePart
from constant_vars import indicators_data_csv, indicators_result_csv_path_large, indicators_result_csv_path_mid, indicators_result_csv_path_small
from dotenv import load_dotenv

load_dotenv()


def _signal_to_int(signal):
    if signal == 'buy':
        return 1
    elif signal == 'sell':
        return -1
    return 0


def _composite_score(close_price, sma200, boll_signal, rsi_signal, stoch_signal, supertrend_signal):
    """Weighted composite signal score: -1 (strong sell) to +1 (strong buy)."""
    boll  = _signal_to_int(boll_signal)
    rsi   = _signal_to_int(rsi_signal)
    stoch = _signal_to_int(stoch_signal)

    if 'rise' in str(supertrend_signal):
        st = 1
    elif 'fall' in str(supertrend_signal):
        st = -1
    else:
        st = 0

    sma_pos = 0
    try:
        if close_price != '' and sma200 != '':
            sma_pos = 0.5 if float(close_price) > float(sma200) else -0.5
    except (ValueError, TypeError):
        pass

    score = (boll * 0.20) + (rsi * 0.25) + (stoch * 0.20) + (st * 0.25) + (sma_pos * 0.10)

    if score >= 0.5:
        label = 'Strong Buy'
    elif score >= 0.2:
        label = 'Buy'
    elif score >= -0.2:
        label = 'Hold'
    elif score >= -0.5:
        label = 'Sell'
    else:
        label = 'Strong Sell'

    return round(score, 3), label


def _generate_ai_summary(symbol, category, close_price, sma200, sma50, boll_signal, rsi_signal,
                         stoch_signal, supertrend_signal, score, score_label,
                         pe_ratio, perc_high, perc_low, volume_signal):
    """Plain-English summary. Uses Groq if GROQ_API_KEY is set, else rule-based."""
    groq_key = os.getenv('GROQ_API_KEY', '').strip()

    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            prompt = (
                f"You are a stock analyst. Summarise the following technical indicators for {symbol} "
                f"({category} cap) in 2-3 concise sentences suitable for a retail investor.\n\n"
                f"Close: \u20b9{close_price}, SMA200: {sma200}, SMA50: {sma50}\n"
                f"Bollinger: {boll_signal}, RSI: {rsi_signal}, Stochastic: {stoch_signal}, Supertrend: {supertrend_signal}\n"
                f"Composite Score: {score} ({score_label})\n"
                f"PE Ratio: {pe_ratio}, % from 52w High: {perc_high}, % from 52w Low: {perc_low}\n"
                f"Volume: {volume_signal}\n\n"
                "Focus on the actionable signal and key risks. Do not mention specific prices."
            )
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception:
            pass

    # Rule-based fallback
    parts = []
    try:
        if close_price != '' and sma200 != '':
            if float(close_price) > float(sma200):
                parts.append(f"{symbol} is trading above its 200-day SMA, indicating a long-term uptrend.")
            else:
                parts.append(f"{symbol} is trading below its 200-day SMA, suggesting a long-term downtrend.")
    except (ValueError, TypeError):
        pass

    buy_count  = sum(1 for s in [boll_signal, rsi_signal, stoch_signal] if s == 'buy')
    sell_count = sum(1 for s in [boll_signal, rsi_signal, stoch_signal] if s == 'sell')
    if buy_count >= 2:
        parts.append(f"Short-term momentum indicators ({buy_count}/3) favour buying.")
    elif sell_count >= 2:
        parts.append(f"Short-term momentum indicators ({sell_count}/3) suggest caution.")
    else:
        parts.append("Momentum indicators are mixed — no clear directional signal.")

    if supertrend_signal:
        parts.append(f"Supertrend: {supertrend_signal}.")
    if volume_signal and volume_signal != 'Normal volume':
        parts.append(volume_signal + ".")
    parts.append(f"Overall signal: {score_label} (score: {score}).")
    return ' '.join(parts)


def indicators_response(symbol, backdays=0):
    try:
        end_datetime   = datetime.datetime.now() - datetime.timedelta(days=backdays)
        start_datetime = end_datetime - datetime.timedelta(days=365)

        ticker = yf.Ticker(f"{symbol}.NS")
        a = ticker.history(start=start_datetime.strftime('%Y-%m-%d'),
                           end=end_datetime.strftime('%Y-%m-%d'),
                           interval='1d')

        if a.empty:
            print(f"[!] No data from yfinance for {symbol}")
            return '','','','','','','','','','',''

        a = a.reset_index()
        # normalise column names to match rest of code
        a['CH_TIMESTAMP']       = a['Date'].astype(str).str[:10]
        a['CH_OPENING_PRICE']   = a['Open']
        a['CH_TRADE_HIGH_PRICE']= a['High']
        a['CH_TRADE_LOW_PRICE'] = a['Low']
        a['CH_CLOSING_PRICE']   = a['Close']
        a['CH_TOT_TRADED_VAL']  = a['Volume']

        quotes_list = [
            Quote(datetime.datetime.strptime(d, '%Y-%m-%d'), o, h, l, c, v)
            for d, o, h, l, c, v
            in zip(a['CH_TIMESTAMP'], a['CH_OPENING_PRICE'], a['CH_TRADE_HIGH_PRICE'],
                   a['CH_TRADE_LOW_PRICE'], a['CH_CLOSING_PRICE'], a['CH_TOT_TRADED_VAL'])
        ]

        sma_dict = {
            'date':[],
            'sma':[]
        }
        sma100_dict = {
            'date':[],
            'sma100':[]
        }
        sma50_dict = {
            'date':[],
            'sma50':[]
        }
        sma20_dict = {
            'date':[],
            'sma20':[]
        }
        sma10_dict = {
            'date':[],
            'sma10':[]
        }
        bollinger_bands_dict = {
            'date':[],
            'sma':[],
            'upper_band':[],
            'lower_band':[],
            'percent_b':[],
            'z_score':[],
            'width':[]
        }
        rsi_dict = {
            'date':[],
            'rsi':[]
        }
        stoch_dict = {
            'date':[],
            'oscillator':[],
            'signal':[],
            'percent_j':[]
        }
        super_trend_dict = {
            'date':[],
            'super_trend':[],
            'upper_band':[],
            'lower_band':[]
        }

        # print('get_sma')
        res = indicators.get_sma(quotes_list, 200, candle_part=CandlePart.CLOSE)
        for i in res:
            if i.sma is not None:
                sma_dict['date'].append(i.date)
                sma_dict['sma'].append(i.sma)
        # print('get_sma')
        res = indicators.get_sma(quotes_list, 100, candle_part=CandlePart.CLOSE)
        for i in res:
            if i.sma is not None:
                sma100_dict['date'].append(i.date)
                sma100_dict['sma100'].append(i.sma)
        # print('get_sma')
        res = indicators.get_sma(quotes_list, 50, candle_part=CandlePart.CLOSE)
        for i in res:
            if i.sma is not None:
                sma50_dict['date'].append(i.date)
                sma50_dict['sma50'].append(i.sma)
        # print('get_sma')
        res = indicators.get_sma(quotes_list, 20, candle_part=CandlePart.CLOSE)
        for i in res:
            if i.sma is not None:
                sma20_dict['date'].append(i.date)
                sma20_dict['sma20'].append(i.sma)
        res = indicators.get_sma(quotes_list, 10, candle_part=CandlePart.CLOSE)
        for i in res:
            if i.sma is not None:
                sma10_dict['date'].append(i.date)
                sma10_dict['sma10'].append(i.sma)

        # print('get_bollinger_bands')   
        results = indicators.get_bollinger_bands(quotes_list, 200, 2)
        for i in results:
            if i.sma is not None:
                bollinger_bands_dict['date'].append(i.date)
                bollinger_bands_dict['sma'].append(i.sma)
                bollinger_bands_dict['upper_band'].append(i.upper_band)
                bollinger_bands_dict['lower_band'].append(i.lower_band)
                bollinger_bands_dict['percent_b'].append(i.percent_b)
                bollinger_bands_dict['z_score'].append(i.z_score)
                bollinger_bands_dict['width'].append(i.width)

        # print('get_rsi')    
        results = indicators.get_rsi(quotes_list, 14)
        for i in results:
            if i.rsi is not None:
                rsi_dict['date'].append(i.date)
                rsi_dict['rsi'].append(i.rsi)

        # print('get_stoch')   
        results = indicators.get_stoch(quotes_list, 200, 3, 3)
        for i in results:
            if i.k is not None:
                stoch_dict['date'].append(i.date)
                stoch_dict['oscillator'].append(i.k)
                stoch_dict['signal'].append(i.d)
                stoch_dict['percent_j'].append(i.j)

        # print('get_super_trend')    
        results = indicators.get_super_trend(quotes_list, 14, 3)
        for i in results:
            if i.super_trend is not None:
                super_trend_dict['date'].append(i.date)
                super_trend_dict['super_trend'].append(i.super_trend)
                super_trend_dict['upper_band'].append(i.upper_band)
                super_trend_dict['lower_band'].append(i.lower_band)

        # print('All get completed')

        df_sma = pd.DataFrame(sma_dict)
        df_sma100 = pd.DataFrame(sma100_dict)
        df_sma50 = pd.DataFrame(sma50_dict)
        df_sma20 = pd.DataFrame(sma20_dict)
        df_sma10 = pd.DataFrame(sma10_dict)
        # df_sma.to_csv(f'{symbol}_sma.csv')
        df_bollinger_bands = pd.DataFrame(bollinger_bands_dict) # %b to be looked here => -ve or near 0 buy => near or above 1 sell
        # df_bollinger_bands.to_csv(f'{symbol}_bollinger_bands.csv')
        df_rsi = pd.DataFrame(rsi_dict) # rsi to be looked here => near of less than 30 means buy => near or greater than 70 means sell
        # df_rsi.to_csv(f'{symbol}_rsi.csv')
        df_stoch = pd.DataFrame(stoch_dict)
        # df_stoch.to_csv(f'{symbol}_stoch.csv')
        df_super_trend = pd.DataFrame(super_trend_dict)
        # df_super_trend.to_csv(f'{symbol}_super_trend.csv')

        v,w,w100,w50,w20,w10,x,y,z,aa = '','','','','','','','','',''
        
        # close price
        v = a[a['CH_TIMESTAMP']==a['CH_TIMESTAMP'].max()]['CH_CLOSING_PRICE'].values[0]
        
        # sma
        if not df_sma.empty:
            w = df_sma[df_sma['date']==df_sma['date'].max()]['sma'].values[0]
        if not df_sma100.empty:
            w100 = df_sma100[df_sma100['date']==df_sma100['date'].max()]['sma100'].values[0]
        if not df_sma50.empty:
            w50 = df_sma50[df_sma50['date']==df_sma50['date'].max()]['sma50'].values[0]
        if not df_sma20.empty:
            w20 = df_sma20[df_sma20['date']==df_sma20['date'].max()]['sma20'].values[0]
        if not df_sma10.empty:
            w10 = df_sma10[df_sma10['date']==df_sma10['date'].max()]['sma10'].values[0]
        
        # latest bollinger_band
        if not df_bollinger_bands.empty:
            # print('bollinger_band')
            if df_bollinger_bands[df_bollinger_bands['date']==df_bollinger_bands['date'].max()]['percent_b'].values[0]<=0:
                x = 'buy'
            elif df_bollinger_bands[df_bollinger_bands['date']==df_bollinger_bands['date'].max()]['percent_b'].values[0]>=0.6:
                x = 'sell'
            else:
                x = 'hold'
            
        # latest rsi
        if not df_rsi.empty:
            # print(df_rsi[df_rsi['date']==df_rsi['date'].max()]['rsi'].values[0])
            if df_rsi[df_rsi['date']==df_rsi['date'].max()]['rsi'].values[0]<=34:
                y = 'buy'
            elif df_rsi[df_rsi['date']==df_rsi['date'].max()]['rsi'].values[0]>=65:
                y = 'sell'
            else:
                y = 'hold'
               
        # latest stoch
        if not df_stoch.empty: 
            if df_stoch[df_stoch['date']==df_stoch['date'].max()]['oscillator'].values[0] >= 75:
                z = 'sell'
            elif df_stoch[df_stoch['date']==df_stoch['date'].max()]['oscillator'].values[0] <= 25:
                z = 'buy'
            else:
                z = 'hold'
                
        # latest super_trend
        if not df_super_trend.empty:
            if df_super_trend.tail(5).tail(1)['lower_band'].values[0] is None and df_super_trend.tail(5).tail(1)['upper_band'].values[0] is not None:
                if df_super_trend.tail(5).tail(2)['upper_band'].values[0] is None:
                    aa += 'trend change to upper band...'
                aa += 'probability to fall more'
            elif df_super_trend.tail(5).tail(1)['lower_band'].values[0] is not None and df_super_trend.tail(5).tail(1)['upper_band'].values[0] is None:
                if df_super_trend.tail(5).tail(2)['lower_band'].values[0] is None:
                    aa += 'trend change to lower band'
                aa += 'probability to rise more'

        # volume analysis
        volume_signal = 'Normal volume'
        try:
            vol = a['CH_TOT_TRADED_VAL'].astype(float)
            avg_30 = vol.tail(30).mean()
            avg_5  = vol.tail(5).mean()
            if avg_30 > 0:
                ratio = avg_5 / avg_30
                if ratio >= 1.5:
                    volume_signal = f'Volume spike (5d avg is {ratio:.1f}x the 30d avg)'
                elif ratio <= 0.5:
                    volume_signal = f'Low volume (5d avg is {ratio:.1f}x the 30d avg)'
        except Exception:
            pass

        return v,w,w100,w50,w20,w10,x,y,z,aa,volume_signal
    except Exception as e:
        print(f"[!] Error in indicators_response for symbol: {e}")
        return '','','','','','','','','','',''  


def load_stocks_indicators_data(fiftytwo_weeks_analysis_json,backdays):

    # Load the final 52-week analysis result
    with open(fiftytwo_weeks_analysis_json) as f:
        stock_summary = json.load(f)

    # Prepare executor and loop
    executor = ThreadPoolExecutor(max_workers=4)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Your indicators_response function must be synchronous — we’ll wrap it in executor
    def get_stock_data(symbol, data):
        try:
            close_price, sma200, sma100, sma50, sma20, sma10, boll_signal, rsi_signal, stoch_signal, supertrend_signal, volume_signal = indicators_response(symbol, backdays)

            score, score_label = _composite_score(close_price, sma200, boll_signal, rsi_signal, stoch_signal, supertrend_signal)
            ai_summary = _generate_ai_summary(
                symbol, data.get('category', ''), close_price, sma200, sma50,
                boll_signal, rsi_signal, stoch_signal, supertrend_signal,
                score, score_label,
                data.get('PE_ratio', ''), data.get('perc_high', ''), data.get('perc_low', ''),
                volume_signal
            )

            return {
                "symbol": symbol,
                "category": data.get('category', ''),
                "PE_ratio": data.get('PE_ratio', ''),
                "perc_high": data.get('perc_high', ''),
                "perc_low": data.get('perc_low', ''),
                "close_price": close_price,
                "sma200": sma200,
                "sma100": sma100,
                "sma50": sma50,
                "sma20": sma20,
                "sma10": sma10,
                "bollinger_signal": boll_signal,
                "rsi_signal": rsi_signal,
                "stoch_signal": stoch_signal,
                "supertrend_signal": supertrend_signal,
                "volume_signal": volume_signal,
                "composite_score": score,
                "signal": score_label,
                "ai_summary": ai_summary,
            }
        except Exception as e:
            print(f"[!] Error processing {symbol}: {e}")
            return None

    async def process_all_stocks():
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, get_stock_data, symbol, data)
            for symbol, data in stock_summary.items()
        ]

        # Optional: wrap with tqdm for progress bar
        results = []
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing"):
            result = await f
            if result:
                results.append(result)
        return results

    # Run the async processing
    final_results = loop.run_until_complete(process_all_stocks())

    # Save to CSV using pandas
    df = pd.DataFrame(final_results)
    df['PE_ratio'] = pd.to_numeric(df['PE_ratio'], errors='coerce')  # convert to float, NaN if invalid
    df.to_csv(indicators_data_csv, index=False)
    df = df[(df['PE_ratio'] < float(os.getenv('PE_RATIO_MAX'))) & (df['PE_ratio'] > float(os.getenv('PE_RATIO_MIN')))]
    df[df['category']=='large'].to_csv(indicators_result_csv_path_large, index=False)
    df[df['category']=='mid'].to_csv(indicators_result_csv_path_mid, index=False)
    df[df['category']=='small'].to_csv(indicators_result_csv_path_small, index=False)

    print(f"✅ Done! CSV saved as {indicators_data_csv}")
