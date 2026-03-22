# stock_personalised_alerts
this project will give personalised intimation on list of stocks that you want 

Market capitalization = total number of outstanding shares multiplied by the market price of each share.

largestocks => market cap of these companies is significantly high, coming in at around Rs. 20,000 crores or more.

midstocks => market cap generally tends to range from Rs. 5,000 to Rs. 20,000 crores.

smallstocks => companies generally come in below Rs. 5,000 crores

## to run
pip install -r requirements.txt

.env file create add variables there and run main.py

or 

docker build -t stock-analyzer .

docker run --rm --env-file .env stock-analyzer

----

for my reference:

docker tag stock-analyzer truenas_ip:port/stock-analyzer

docker push truenas_ip:port/stock-analyzer

docker pull truenas_ip:port/stock-analyzer


to update with latest code

docker build -t stock-analyzer .

docker rmi truenas_ip:port/stock-analyzer

docker tag stock-analyzer truenas_ip:port/stock-analyzer

docker push truenas_ip:port/stock-analyzer

docker run --rm --env-file .env truenas_ip:port/stock-analyzer

help cmds -----------
docker container ls -a

docker container rm <container_id>>

docker image ls

docker image rm <Image_id>

----

## TODO

### AI & Analysis
- [ ] Integrate an LLM (e.g. OpenAI / local Ollama) to interpret indicator combinations and generate a plain-English buy/sell/hold summary per stock
- [ ] Score each stock with a composite signal score (weighted average of bollinger, RSI, stoch, supertrend) instead of individual labels
- [ ] Add volume analysis — unusual volume spikes often precede major moves
- [ ] Add sector-level analysis — flag sectors with multiple stocks near 52w low/high
- [ ] Improve supertrend logic — current string-append approach is fragile; return structured signal with trend direction + confirmation bar count

### Algorithm Improvements
- [ ] Tune RSI/stoch/bollinger thresholds per market-cap category (large caps behave differently from small caps)
- [ ] Add a confidence level to each signal based on how many indicators agree
- [ ] Use `nse_fno()` instead of `nse_eq()` for FNO-listed stocks to reduce latency
- [ ] Cache NSE API responses within a run to avoid duplicate fetches for the same symbol
- [ ] Handle stocks with < 200 days of history gracefully (currently SMA200 is silently empty)

### Mail & Output
- [ ] Add a summary section at the top of the email: total stocks scanned, how many flagged, breakdown by cap
- [ ] Colour-code cells in the HTML table (green = buy, red = sell, grey = hold)
- [ ] Add sparkline-style mini charts or links to NSE chart page per stock
- [ ] Send a separate alert email if any stock has all 4 indicators aligned (strong signal)
- [ ] Support Telegram / WhatsApp notification as an alternative to email

### Code Quality
- [ ] Replace `eval(os.getenv(...))` with `os.getenv(...).lower() == 'true'` for `NEW_EXCEL_FLAG`
- [ ] Centralise all `.env` variable reads into `constant_vars.py` so no module calls `os.getenv` directly
- [ ] Add proper logging (Python `logging` module) instead of bare `print` statements, with log levels
- [ ] Write unit tests for indicator signal logic and 52w threshold calculations
- [ ] Add a `--dry-run` flag to test the pipeline without sending emails

### Infrastructure
- [ ] Add a cron job / TrueNAS scheduled task to run the container automatically each morning before market open
- [ ] Mount output CSVs as a Docker volume so data persists between runs without rebuilding the image
- [ ] Add a GitHub Actions workflow to auto-build and push the image to the registry on every push to main
