# Stock Daily Range Dashboard

A Streamlit dashboard that visualizes the distribution of daily price ranges for stock tickers using interactive histograms. Useful for analyzing volatility patterns across different timeframes.

## Features

- **Three histograms** showing daily range distribution for 14-day, 28-day, and a custom window
- **Dollar or percentage mode** — toggle between absolute range (High - Low) and percentage range relative to previous close
- **Median line** displayed on each histogram
- **Rug plot** showing individual data points on the x-axis
- **Date vs range chart** — dashed line plot for the custom window period
- **Adjustable bin width** — defaults to $2 (dollar mode) or 1% (percentage mode)
- **13 default tickers**: TSLA, GOOGL, META, AAPL, AMZN, AVGO, ORCL, NVDA, MSFT, QQQ, SLV, GLD, IBIT
- **Custom ticker input** — enter any ticker symbol (not saved to the database)
- **Local SQLite storage** — fetched data is cached locally so subsequent loads don't hit the API
- **Request counter** — tracks successful/failed Yahoo Finance API calls (persisted in the database)

## Requirements

- Python 3.10+

## Setup

```bash
cd stock-range-dashboard
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
source .venv/bin/activate
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

### Controls (sidebar)

| Control | Description |
|---------|-------------|
| **Default ticker** | Select from the 13 preset tickers |
| **Custom ticker** | Type any ticker symbol (overrides the dropdown) |
| **Show as percentage** | Toggle between dollar and percentage range |
| **Custom window** | Number of trading days for the third histogram and the time series chart |
| **Bin width** | Set histogram bin width (0 = auto) |
| **Refresh Data** | Re-download 1 year of data from Yahoo Finance |

## Data

- Source: Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance)
- Storage: SQLite (`stock_data.db`, created automatically)
- Default history: 1 year
- Data is fetched automatically on first load for a ticker, then served from local cache until you click Refresh Data

## Project Structure

```
stock-range-dashboard/
    app.py              # Streamlit UI and chart logic
    db.py               # SQLite helper functions
    requirements.txt    # Python dependencies
    stock_data.db       # Local database (created at runtime)
```
