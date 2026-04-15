"""Quick diagnostic script to test yfinance connectivity."""

import yfinance as yf
import time

TICKERS = ["SPY", "AAPL", "GLD"]

print("=== yfinance connectivity test ===\n")

for ticker in TICKERS:
    print(f"Fetching {ticker}...", end=" ")
    try:
        data = yf.download(ticker, period="5d", auto_adjust=True, progress=False)
        if data.empty:
            print("EMPTY (possible rate limit)")
        else:
            print(f"OK — {len(data)} rows")
            print(f"  Columns: {list(data.columns)}")
            print(f"  MultiIndex: {isinstance(data.columns, __import__('pandas').MultiIndex)}")
            print(f"  Head:\n{data.head()}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
    time.sleep(2)  # small delay between requests

print("\nDone.")
