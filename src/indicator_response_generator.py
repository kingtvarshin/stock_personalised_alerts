import json, os, asyncio, datetime, logging, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from tqdm import tqdm
import yfinance as yf
from stock_indicators import indicators, Quote
from stock_indicators import CandlePart
from constant_vars import (
    indicators_data_csv, indicators_result_csv_path_large,
    indicators_result_csv_path_mid, indicators_result_csv_path_small,
    sector_analysis_csv, GROQ_API_KEY, PE_RATIO_MAX, PE_RATIO_MIN,
)

logger = logging.getLogger(__name__)

# Thread-safe yfinance cache â€” avoids duplicate fetches for the same symbol within a run
_yf_cache: dict = {}
_yf_cache_lock = Lock()

# Per-cap thresholds for indicator signals
# Large caps are more stable â€” tighter overbought/oversold levels
# Small caps are more volatile â€” wider bands needed
_THRESHOLDS = {
    'large': {'rsi_buy': 40, 'rsi_sell': 60, 'stoch_buy': 30, 'stoch_sell': 70, 'boll_buy': 0.1,  'boll_sell': 0.55},
    'mid':   {'rsi_buy': 37, 'rsi_sell': 63, 'stoch_buy': 27, 'stoch_sell': 73, 'boll_buy': 0.05, 'boll_sell': 0.58},
    'small': {'rsi_buy': 34, 'rsi_sell': 65, 'stoch_buy': 25, 'stoch_sell': 75, 'boll_buy': 0.0,  'boll_sell': 0.60},
}


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

    if isinstance(supertrend_signal, dict):
        direction = supertrend_signal.get('direction', '')
        st = 1 if direction == 'bullish' else (-1 if direction == 'bearish' else 0)
    else:
        st = 1 if 'rise' in str(supertrend_signal) else (-1 if 'fall' in str(supertrend_signal) else 0)

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

    # Confidence: count how many of the 4 directional indicators agree with the overall label
    signals = [boll, rsi, stoch, st]
    if score > 0:
        confidence = sum(1 for s in signals if s == 1)
    elif score < 0:
        confidence = sum(1 for s in signals if s == -1)
    else:
        confidence = 0

    return round(score, 3), label, confidence


def _generate_ai_summary(symbol, category, close_price, sma200, sma50, boll_signal, rsi_signal,
                         stoch_signal, supertrend_signal, score, score_label,
                         pe_ratio, perc_high, perc_low, volume_signal):
    """Plain-English summary. Uses Groq if GROQ_API_KEY is set, else rule-based."""
    groq_key = GROQ_API_KEY

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
        parts.append("Momentum indicators are mixed â€” no clear directional signal.")

    if supertrend_signal:
        if isinstance(supertrend_signal, dict):
            sig = supertrend_signal.get('signal', '')
            if sig:
                change = ' âš¡ Trend change!' if supertrend_signal.get('trend_change') else ''
                parts.append(f"Supertrend: {sig}{change}.")
        else:
            parts.append(f"Supertrend: {supertrend_signal}.")
    if volume_signal and volume_signal != 'Normal volume':
        parts.append(volume_signal + ".")
    parts.append(f"Overall signal: {score_label} (score: {score}).")
    return ' '.join(parts)


def indicators_response(symbol, backdays=0, category='small'):
    try:
        end_datetime   = datetime.datetime.now() - datetime.timedelta(days=backdays)
        start_datetime = end_datetime - datetime.timedelta(days=365)

        # Use cached data if already fetched this run
        cache_key = f"{symbol}_{backdays}"
        with _yf_cache_lock:
            if cache_key in _yf_cache:
                a = _yf_cache[cache_key]
            else:
                ticker = yf.Ticker(f"{symbol}.NS")
                raw = ticker.history(start=start_datetime.strftime('%Y-%m-%d'),
                                     end=end_datetime.strftime('%Y-%m-%d'),
                                     interval='1d')
                if raw.empty:
                    logger.warning('No data from yfinance for %s', symbol)
                    _yf_cache[cache_key] = None
                    _yf_cache[cache_key + '_info'] = {}
                else:
                    raw = raw.reset_index()
                    raw['CH_TIMESTAMP']        = raw['Date'].astype(str).str[:10]
                    raw['CH_OPENING_PRICE']    = raw['Open']
                    raw['CH_TRADE_HIGH_PRICE'] = raw['High']
                    raw['CH_TRADE_LOW_PRICE']  = raw['Low']
                    raw['CH_CLOSING_PRICE']    = raw['Close']
                    raw['CH_TOT_TRADED_VAL']   = raw['Volume']
                    _yf_cache[cache_key] = raw
                    # cache ticker.info separately to avoid Pandas attribute warning
                    try:
                        _yf_cache[cache_key + '_info'] = ticker.info
                    except Exception:
                        _yf_cache[cache_key + '_info'] = {}
                a = _yf_cache[cache_key]

        if a is None:
            return '','','','','','','','','',{'direction':'','trend_change':False,'signal':''},'','',''

        # Graceful handling for stocks with < 200 days of history
        n_days = len(a)
        if n_days < 50:
            logger.warning('%s: only %d days of data â€” skipping (too short for indicators)', symbol, n_days)
            return '','','','','','','','','',{'direction':'','trend_change':False,'signal':''},'','',''
        if n_days < 200:
            logger.info('%s: only %d days â€” SMA200/Bollinger200 will be unavailable', symbol, n_days)

        # Per-cap thresholds
        thr = _THRESHOLDS.get(category, _THRESHOLDS['small'])

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

        v,w,w100,w50,w20,w10,x,y,z = '','','','','','','','',''
        aa = {'direction': '', 'trend_change': False, 'signal': ''}
        
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
        
        # latest bollinger_band â€” per-cap thresholds
        if not df_bollinger_bands.empty:
            pb = df_bollinger_bands[df_bollinger_bands['date']==df_bollinger_bands['date'].max()]['percent_b'].values[0]
            if pb <= thr['boll_buy']:
                x = 'buy'
            elif pb >= thr['boll_sell']:
                x = 'sell'
            else:
                x = 'hold'
            
        # latest rsi â€” per-cap thresholds
        if not df_rsi.empty:
            rsi_val = df_rsi[df_rsi['date']==df_rsi['date'].max()]['rsi'].values[0]
            if rsi_val <= thr['rsi_buy']:
                y = 'buy'
            elif rsi_val >= thr['rsi_sell']:
                y = 'sell'
            else:
                y = 'hold'
               
        # latest stoch â€” per-cap thresholds
        if not df_stoch.empty:
            osc_val = df_stoch[df_stoch['date']==df_stoch['date'].max()]['oscillator'].values[0]
            if osc_val >= thr['stoch_sell']:
                z = 'sell'
            elif osc_val <= thr['stoch_buy']:
                z = 'buy'
            else:
                z = 'hold'
                
        # latest super_trend â€” structured signal
        def _is_empty(val):
            return val is None or (isinstance(val, float) and pd.isna(val))

        if not df_super_trend.empty:
            last = df_super_trend.iloc[-1]
            prev = df_super_trend.iloc[-2] if len(df_super_trend) >= 2 else None
            lb_now = last['lower_band']
            ub_now = last['upper_band']
            lb_none = _is_empty(lb_now)
            ub_none = _is_empty(ub_now)

            if lb_none and not ub_none:
                # upper band active â†’ price below supertrend â†’ bearish
                aa['direction'] = 'bearish'
                aa['signal'] = 'probability to fall more'
                if prev is not None and not _is_empty(prev['lower_band']):
                    aa['trend_change'] = True
                    aa['signal'] = 'trend change to bearish â€” probability to fall more'
            elif not lb_none and ub_none:
                # lower band active â†’ price above supertrend â†’ bullish
                aa['direction'] = 'bullish'
                aa['signal'] = 'probability to rise more'
                if prev is not None and _is_empty(prev['lower_band']):
                    aa['trend_change'] = True
                    aa['signal'] = 'trend change to bullish â€” probability to rise more'

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

        # sector & industry (best-effort â€” use cached ticker.info)
        sector = ''
        industry = ''
        try:
            info = _yf_cache.get(cache_key + '_info', {})
            sector   = info.get('sector', '')   or ''
            industry = info.get('industry', '') or ''
        except Exception:
            pass

        return v,w,w100,w50,w20,w10,x,y,z,aa,volume_signal,sector,industry
    except Exception as e:
        logger.error('Error in indicators_response for %s: %s', symbol, e, exc_info=True)
        return '','','','','','','','','',{'direction':'','trend_change':False,'signal':''},'','',''  


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

    # Your indicators_response function must be synchronous â€” weâ€™ll wrap it in executor
    def get_stock_data(symbol, data):
        try:
            category = data.get('category', 'small')
            close_price, sma200, sma100, sma50, sma20, sma10, boll_signal, rsi_signal, stoch_signal, supertrend_signal, volume_signal, sector, industry = indicators_response(symbol, backdays, category)

            score, score_label, confidence = _composite_score(close_price, sma200, boll_signal, rsi_signal, stoch_signal, supertrend_signal)
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
                "supertrend_direction": supertrend_signal.get('direction', '') if isinstance(supertrend_signal, dict) else '',
                "supertrend_signal": supertrend_signal.get('signal', '') if isinstance(supertrend_signal, dict) else str(supertrend_signal),
                "supertrend_trend_change": supertrend_signal.get('trend_change', False) if isinstance(supertrend_signal, dict) else False,
                "volume_signal": volume_signal,
                "sector": sector,
                "industry": industry,
                "composite_score": score,
                "confidence": confidence,
                "signal": score_label,
                "ai_summary": ai_summary,
            }
        except Exception as e:
            logger.error('Error processing %s: %s', symbol, e, exc_info=True)
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
    df = df[(df['PE_ratio'] < PE_RATIO_MAX) & (df['PE_ratio'] > PE_RATIO_MIN)]
    df[df['category']=='large'].to_csv(indicators_result_csv_path_large, index=False)
    df[df['category']=='mid'].to_csv(indicators_result_csv_path_mid, index=False)
    df[df['category']=='small'].to_csv(indicators_result_csv_path_small, index=False)

    # Clear cache after run to free memory
    with _yf_cache_lock:
        _yf_cache.clear()

    print(f"âœ… Done! CSV saved as {indicators_data_csv}")

    # Sector-level analysis â€” flag sectors with multiple buy signals
    try:
        df_all = pd.read_csv(indicators_data_csv)
        if 'sector' in df_all.columns and df_all['sector'].notna().any():
            df_sector = df_all[df_all['sector'].str.strip() != '']
            if not df_sector.empty:
                sector_groups = df_sector.groupby('sector').agg(
                    total_flagged=('symbol', 'count'),
                    buy_signals=('signal', lambda x: x.isin(['Buy', 'Strong Buy']).sum()),
                    strong_buy=('signal', lambda x: (x == 'Strong Buy').sum()),
                    sell_signals=('signal', lambda x: x.isin(['Sell', 'Strong Sell']).sum()),
                    avg_score=('composite_score', lambda x: round(x.mean(), 3)),
                    trend_changes=('supertrend_trend_change', lambda x: x.sum()),
                    symbols=('symbol', lambda x: ', '.join(x.tolist()))
                ).reset_index()
                sector_groups = sector_groups[sector_groups['buy_signals'] >= 2].sort_values('buy_signals', ascending=False)
                if not sector_groups.empty:
                    sector_groups.to_csv(sector_analysis_csv, index=False)
                    logger.info('Sector analysis saved: %d sectors with 2+ buy signals', len(sector_groups))
                else:
                    logger.info('No sectors with 2+ buy signals today.')
    except Exception as e:
        logger.error('Sector analysis error: %s', e, exc_info=True)
