"""Quick diagnostic: plain yfinance vs curl_cffi browser-impersonated session."""

import time
import yfinance as yf
from curl_cffi import requests as curl_requests

TICKERS = ["SPY", "AAPL", "GLD"]


def test_plain():
    print("--- Plain yfinance (default session) ---")
    for ticker in TICKERS:
        print(f"  {ticker}...", end=" ", flush=True)
        try:
            data = yf.Ticker(ticker).history(period="5d")
            print("EMPTY" if data.empty else f"OK ({len(data)} rows)")
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
        time.sleep(2)


def test_curl_cffi():
    print("\n--- curl_cffi (impersonate=chrome) ---")
    session = curl_requests.Session(impersonate="chrome")
    for ticker in TICKERS:
        print(f"  {ticker}...", end=" ", flush=True)
        try:
            data = yf.Ticker(ticker, session=session).history(period="5d")
            print("EMPTY" if data.empty else f"OK ({len(data)} rows)")
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
        time.sleep(2)


if __name__ == "__main__":
    print("=== yfinance connectivity test ===\n")
    test_plain()
    test_curl_cffi()
    print("\nDone.")
