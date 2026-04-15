import os
import sqlite3
import pandas as pd


def get_db_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_data.db")


def init_db(db_path: str | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            ticker  TEXT NOT NULL,
            date    TEXT NOT NULL,
            open    REAL,
            high    REAL,
            low     REAL,
            close   REAL,
            volume  INTEGER,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS request_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker    TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            success   INTEGER NOT NULL  -- 1 = ok, 0 = failed
        )
    """)
    conn.commit()
    return conn


def upsert_ohlcv(conn: sqlite3.Connection, ticker: str, df: pd.DataFrame) -> None:
    rows = []
    for date, row in df.iterrows():
        date_str = str(date.date()) if hasattr(date, "date") else str(date)
        rows.append((
            ticker,
            date_str,
            float(row["Open"]),
            float(row["High"]),
            float(row["Low"]),
            float(row["Close"]),
            int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
        ))
    conn.executemany(
        "INSERT OR REPLACE INTO ohlcv (ticker, date, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def load_ohlcv(conn: sqlite3.Connection, ticker: str, lookback_days: int = 365) -> pd.DataFrame:
    query = """
        SELECT date, open, high, low, close, volume
        FROM ohlcv
        WHERE ticker = ?
          AND date >= date('now', ?)
        ORDER BY date ASC
    """
    df = pd.read_sql_query(query, conn, params=(ticker, f"-{lookback_days} days"))
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        df.columns = ["Open", "High", "Low", "Close", "Volume"]
    return df


def has_data(conn: sqlite3.Connection, ticker: str) -> bool:
    cur = conn.execute("SELECT 1 FROM ohlcv WHERE ticker = ? LIMIT 1", (ticker,))
    return cur.fetchone() is not None


def log_request(conn: sqlite3.Connection, ticker: str, success: bool) -> None:
    conn.execute(
        "INSERT INTO request_log (ticker, success) VALUES (?, ?)",
        (ticker, 1 if success else 0),
    )
    conn.commit()


def get_request_counts(conn: sqlite3.Connection) -> tuple[int, int]:
    """Returns (success_count, total_count)."""
    cur = conn.execute("SELECT COALESCE(SUM(success), 0), COUNT(*) FROM request_log")
    row = cur.fetchone()
    return row[0], row[1]
