import json
from requests import JSONDecodeError
from nsepython import equity_history
from stock_indicators import indicators, Quote
from stock_indicators import CandlePart
from dateutil import parser 

symbol = "ATUL"
series = "EQ"
start_date = "01-04-2023"
end_date ="01-04-2024"
a  =  equity_history(symbol,series,start_date,end_date)
quotes_list = [
    Quote(parser.parse(d),o,h,l,c,v) 
    for d,o,h,l,c,v 
    in zip(a['CH_TIMESTAMP'], a['CH_OPENING_PRICE'], a['CH_TRADE_HIGH_PRICE'], a['CH_TRADE_LOW_PRICE'], a['CH_CLOSING_PRICE'], a['CH_TOT_TRADED_QTY'])
]

print('get_sma')
res = indicators.get_sma(quotes_list, 200, candle_part=CandlePart.CLOSE)
for i in res:
    print(i.date,i.sma)
print('get_bollinger_bands')    
results = indicators.get_bollinger_bands(quotes_list, 200, 2)
for i in results:
    print(i.date,i.sma,i.upper_band,i.lower_band,i.percent_b,i.z_score,i.width)
print('get_rsi')    
results = indicators.get_rsi(quotes_list, 30)
for i in results:
    print(i.date,i.rsi)
print('get_stoch')   
results = indicators.get_stoch(quotes_list, 14, 3, 3)
for i in results:
    print(i.date,i.k,i.d,i.j)
print('get_super_trend')    
results = indicators.get_super_trend(quotes_list, 14, 3)
for i in results:
    print(i.date,i.super_trend,i.upper_band,i.lower_band)