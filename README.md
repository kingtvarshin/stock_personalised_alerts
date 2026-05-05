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

## Jenkins Scheduling (TrueNAS)

This repo includes a ready `Jenkinsfile` at project root.

1. Create a Pipeline job in Jenkins and point it to this repository.
2. The pipeline has a built-in cron trigger: `H 8 * * 1-5` (weekdays around 08:00).
3. Add Jenkins credentials for `.env`:
	- Type: `Secret file`
	- ID: `stock-alert-env-file` (or update `ENV_FILE_CREDENTIAL_ID` parameter)
	- File content: your full `.env` values
4. Run with parameters:
	- `BRANCH_NAME`: branch to run (default `main`)
	- `USE_JENKINS_SECRET_ENV=true`: use secret file credential as `src/.env`
	- `DRY_RUN=true/false`: test without sending emails or perform real send
5. Jenkins will:
	- Checkout the selected branch
	- Create `src/.env` from Jenkins secret (or `ENV_FILE_CONTENT` parameter)
	- Build Docker image from `src/Dockerfile`
	- Run `main.py` inside the container

If your repo is private, set `GIT_CREDENTIALS_ID` in Jenkins build parameters.

----

## TODO

### AI & Analysis
- [x] Integrate an LLM (e.g. OpenAI / local Ollama) to interpret indicator combinations and generate a plain-English buy/sell/hold summary per stock
- [x] Score each stock with a composite signal score (weighted average of bollinger, RSI, stoch, supertrend) instead of individual labels
- [x] Add volume analysis — unusual volume spikes often precede major moves
- [x] Add sector-level analysis — flag sectors with multiple stocks near 52w low/high
- [x] Improve supertrend logic — structured signal dict with direction, trend_change flag, and plain-English signal string

### Algorithm Improvements
- [x] Tune RSI/stoch/bollinger thresholds per market-cap category (large caps behave differently from small caps)
- [x] Add a confidence level to each signal based on how many indicators agree
- [x] Use `nse_fno()` instead of `nse_eq()` for FNO-listed stocks to reduce latency — superseded by yfinance migration
- [x] Cache NSE API responses within a run to avoid duplicate fetches for the same symbol
- [x] Handle stocks with < 200 days of history gracefully (currently SMA200 is silently empty)

### Mail & Output
- [x] Add a summary section at the top of the email: total stocks scanned, how many flagged, breakdown by cap
- [x] Colour-code cells in the HTML table (green = buy, red = sell, grey = hold)
- [x] Add sparkline-style mini charts or links to NSE chart page per stock
- [x] Send a separate alert email if any stock has all 4 indicators aligned (strong signal)
- [ ] Support Telegram / WhatsApp notification as an alternative to email

### Code Quality
- [x] Replace `eval(os.getenv(...))` with safe parsing (`json.loads` for lists, `str.lower()` for booleans)
- [x] Centralise all `.env` variable reads into `constant_vars.py` so no module calls `os.getenv` directly
- [x] Add proper logging (Python `logging` module) instead of bare `print` statements, with log levels
- [x] Write unit tests for indicator signal logic and 52w threshold calculations (`tests/test_indicators.py` — 36 tests)
- [x] Add a `--dry-run` flag to test the pipeline without sending emails (`python src/main.py --dry-run`)

### Infrastructure
- [ ] Add a cron job / TrueNAS scheduled task to run the container automatically each morning before market open
- [ ] Mount output CSVs as a Docker volume so data persists between runs without rebuilding the image
- [ ] Add a GitHub Actions workflow to auto-build and push the image to the registry on every push to main
