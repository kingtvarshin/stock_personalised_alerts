from nsepython import equity_history
from stock_indicators import indicators, Quote
from stock_indicators import CandlePart
from dateutil import parser 
import pandas as pd
import datetime

def indicators_response(symbol,backdays=0):
    try:

        series         = "EQ"
        end_datetime   = datetime.datetime.now() - datetime.timedelta(days=backdays)
        start_datetime = end_datetime - datetime.timedelta(days=365)
        end_date       = f'{end_datetime.day}-{end_datetime.month}-{end_datetime.year}'
        start_date     = f'{start_datetime.day}-{start_datetime.month}-{start_datetime.year}'
        a              =  equity_history(symbol,series,start_date,end_date)
        quotes_list    = [
            Quote(parser.parse(d),o,h,l,c,v) 
            for d,o,h,l,c,v 
            in zip(a['CH_TIMESTAMP'], a['CH_OPENING_PRICE'], a['CH_TRADE_HIGH_PRICE'], a['CH_TRADE_LOW_PRICE'], a['CH_CLOSING_PRICE'], a['CH_TOT_TRADED_VAL'])
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
        ema_dict = {
            'date':[],
            'ema':[]
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
        # print('get_sma100')
        res = indicators.get_sma(quotes_list, 100, candle_part=CandlePart.CLOSE)
        for i in res:
            if i.sma is not None:
                sma100_dict['date'].append(i.date)
                sma100_dict['sma100'].append(i.sma)
        # print('get_sma50')
        res = indicators.get_sma(quotes_list, 50, candle_part=CandlePart.CLOSE)
        for i in res:
            if i.sma is not None:
                sma50_dict['date'].append(i.date)
                sma50_dict['sma50'].append(i.sma)
        # print('get_sma20')
        res = indicators.get_sma(quotes_list, 20, candle_part=CandlePart.CLOSE)
        for i in res:
            if i.sma is not None:
                sma20_dict['date'].append(i.date)
                sma20_dict['sma20'].append(i.sma)
        # print('get_sma10')
        res = indicators.get_sma(quotes_list, 10, candle_part=CandlePart.CLOSE)
        for i in res:
            if i.sma is not None:
                sma10_dict['date'].append(i.date)
                sma10_dict['sma10'].append(i.sma)
        # print('get_ema')
        res = indicators.get_ema(quotes_list, 100, candle_part=CandlePart.CLOSE)
        for i in res:
            if i.ema is not None:
                ema_dict['date'].append(i.date)
                ema_dict['ema'].append(i.ema)

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
        df_ema = pd.DataFrame(ema_dict)
        # df_sma.to_csv(f'{symbol}_sma.csv')
        df_bollinger_bands = pd.DataFrame(bollinger_bands_dict) # %b to be looked here => -ve or near 0 buy => near or above 1 sell
        # df_bollinger_bands.to_csv(f'{symbol}_bollinger_bands.csv')
        df_rsi = pd.DataFrame(rsi_dict) # rsi to be looked here => near of less than 30 means buy => near or greater than 70 means sell
        # df_rsi.to_csv(f'{symbol}_rsi.csv')
        df_stoch = pd.DataFrame(stoch_dict)
        # df_stoch.to_csv(f'{symbol}_stoch.csv')
        df_super_trend = pd.DataFrame(super_trend_dict)
        # df_super_trend.to_csv(f'{symbol}_super_trend.csv')

        v,w,w100,w50,w20,w10,wema,x,y,z,aa = '','','','','','','','','','',''
        
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
        if not df_ema.empty:
            wema = df_ema[df_ema['date']==df_ema['date'].max()]['ema'].values[0]
        
        # latest bollinger_band
        if not df_bollinger_bands.empty:
            # print('bollinger_band')
            if df_bollinger_bands[df_bollinger_bands['date']==df_bollinger_bands['date'].max()]['percent_b'].values[0]<=0.3:
                x = 'buy'
            elif df_bollinger_bands[df_bollinger_bands['date']==df_bollinger_bands['date'].max()]['percent_b'].values[0]>=0.9:
                x = 'sell'
            else:
                x = 'hold'
            
        # latest rsi
        if not df_rsi.empty:
            print(df_rsi[df_rsi['date']==df_rsi['date'].max()]['rsi'].values[0])
            if df_rsi[df_rsi['date']==df_rsi['date'].max()]['rsi'].values[0]<=35:
                y = 'buy'
            elif df_rsi[df_rsi['date']==df_rsi['date'].max()]['rsi'].values[0]>=75:
                y = 'sell'
            else:
                y = 'hold'
               
        # latest stoch
        if not df_stoch.empty: 
            if df_stoch[df_stoch['date']==df_stoch['date'].max()]['oscillator'].values[0] >= 85:
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
                
        return v,w,w100,w50,w20,w10,wema,x,y,z,aa
    except Exception as e:
        # print(type(e))
        # print(e.args)
        # print(e)
        return '','','','','','','','','','',''