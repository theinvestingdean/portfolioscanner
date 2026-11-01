"""
Database management for TID Portfolio Dashboard.
Handles persistent storage of TradingView Webhook Alerts and Scanner metric caches.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tid_portfolio.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create Alerts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        ticker TEXT NOT NULL,
        signal_type TEXT NOT NULL,
        price REAL,
        timeframe TEXT DEFAULT '1D',
        raw_message TEXT,
        action TEXT,
        status TEXT DEFAULT 'ACTIVE'
    )
    """)
    
    # Create cached metrics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scanner_cache (
        symbol TEXT PRIMARY KEY,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        payload TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

def log_alert(ticker: str, signal_type: str, price: Optional[float] = None, 
              timeframe: str = "1D", raw_message: str = "", action: str = "BUY") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alerts (timestamp, ticker, signal_type, price, timeframe, raw_message, action)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), ticker.upper(), signal_type, price, timeframe, raw_message, action))
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id

def get_recent_alerts(limit: int = 50, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if ticker and ticker != "ALL":
        cursor.execute("SELECT * FROM alerts WHERE ticker = ? ORDER BY timestamp DESC LIMIT ?", (ticker.upper(), limit))
    else:
        cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    alerts = [dict(row) for row in rows]
    conn.close()
    return alerts

def get_active_signals_summary() -> Dict[str, Any]:
    """Returns the latest signal active for each ticker within the last 48 hours."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticker, signal_type, price, timestamp, action
        FROM alerts
        ORDER BY timestamp DESC
    """)
    rows = cursor.fetchall()
    latest_by_ticker = {}
    for r in rows:
        t = r["ticker"]
        if t not in latest_by_ticker:
            latest_by_ticker[t] = dict(r)
    conn.close()
    return latest_by_ticker

def clear_alerts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alerts")
    conn.commit()
    conn.close()

# Initialize upon module load
init_db()
