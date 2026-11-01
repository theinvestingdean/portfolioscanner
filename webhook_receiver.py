"""
TradingView Webhook Receiver for TID - Optimised Trend & Portfolio Scanner.
Runs as a lightweight background HTTP server listening for TradingView alert webhooks.
"""

import json
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Tuple
from db import log_alert

DEFAULT_PORT = 8000

class TradingViewWebhookHandler(BaseHTTPRequestHandler):
    def _send_response(self, status_code: int, message: dict):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(message).encode('utf-8'))

    def do_OPTIONS(self):
        self._send_response(200, {"status": "ok"})

    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self._send_response(200, {
                "status": "online",
                "service": "TID Webhook Receiver",
                "endpoint": "/webhook"
            })
        else:
            self._send_response(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == '/webhook' or self.path == '/':
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
            
            ticker, signal_type, price, tf, action = self._parse_alert_payload(raw_body)
            
            alert_id = log_alert(
                ticker=ticker,
                signal_type=signal_type,
                price=price,
                timeframe=tf,
                raw_message=raw_body,
                action=action
            )
            
            self._send_response(200, {
                "status": "success",
                "alert_id": alert_id,
                "ticker": ticker,
                "signal": signal_type,
                "action": action
            })
        else:
            self._send_response(404, {"error": "Unknown endpoint"})

    def _parse_alert_payload(self, text: str) -> Tuple[str, str, Optional[float], str, str]:
        """Intelligently parses both JSON and plain-text TradingView alert strings."""
        text = text.strip()
        ticker = "UNKNOWN"
        signal_type = "ALERT"
        price = None
        tf = "1D"
        action = "BUY"

        # 1. Try parsing JSON
        if text.startswith("{") and text.endswith("}"):
            try:
                data = json.loads(text)
                ticker = str(data.get("ticker", data.get("symbol", "UNKNOWN"))).upper()
                signal_type = str(data.get("signal", data.get("signal_type", data.get("action", "ALERT")))).upper()
                tf = str(data.get("timeframe", data.get("interval", "1D"))).upper()
                price = float(data.get("price", 0.0)) if data.get("price") is not None else None
                action = str(data.get("action", "BUY")).upper()
                return ticker, signal_type, price, tf, action
            except Exception:
                pass

        # 2. Plain Text Regex Parsing (Matches TID - Optimised Trend standard alerts)
        upper = text.upper()

        # Detect Ticker
        # Look for "on NASDAQ:TSLA" or "on TSLA"
        t_match = re.search(r'\bON\s+(?:[A-Z0-9]+:)?([A-Z0-9\.\_\-]+)', upper)
        if t_match:
            ticker = t_match.group(1).strip()
        else:
            # Fallback: scan for any known tickers
            known = ["ALAB", "AMD", "ARM", "ASML", "AVGO", "GOOG", "MRVL", "MU", "NVDA", "PLTR", "SKHY", "SMSN", "SPCX", "TSLA", "TSM", "SMGB", "XNAQ"]
            for k in known:
                if k in upper:
                    ticker = k
                    break

        # Detect Signal Type & Action
        if "CONFIRMED REVERSAL BUY" in upper or "CONFIRMED BUY" in upper:
            signal_type = "CONFIRMED BUY"
            action = "BUY"
        elif "GHOST CAPITULATION" in upper or "GHOST BUY" in upper:
            signal_type = "GHOST CAP"
            action = "SCALE IN"
        elif "FLIPPED BLUE" in upper:
            signal_type = "TREND BLUE (BULL)"
            action = "BULLISH"
        elif "FLIPPED ORANGE" in upper:
            signal_type = "TREND ORANGE (BEAR)"
            action = "BEARISH"
        elif "CONFIRMED REVERSAL SELL" in upper or "CONFIRMED SELL" in upper:
            signal_type = "CONFIRMED SELL"
            action = "SELL"
        elif "PRE-EARNINGS" in upper or "EARNINGS CAUTION" in upper:
            signal_type = "PRE-EARNINGS CAUTION"
            action = "WARN"

        # Detect Timeframe
        tf_match = re.search(r'\((\d+[DWMhms]?|1D|4H|1H|1W)\)', text)
        if tf_match:
            tf = tf_match.group(1).upper()

        # Detect Price
        p_match = re.search(r'(\$|PRICE:?\s*)([0-9]+(?:\.[0-9]+)?)', text)
        if p_match:
            try:
                price = float(p_match.group(2))
            except Exception:
                pass

        return ticker, signal_type, price, tf, action

_server_instance: Optional[HTTPServer] = None
_server_thread: Optional[threading.Thread] = None

def start_webhook_server(port: int = DEFAULT_PORT) -> Tuple[bool, str]:
    """Starts the TradingView Webhook server in a background daemon thread."""
    global _server_instance, _server_thread
    if _server_instance is not None:
        return True, f"Webhook server already running on port {port}"

    try:
        _server_instance = HTTPServer(('0.0.0.0', port), TradingViewWebhookHandler)
        _server_thread = threading.Thread(target=_server_instance.serve_forever, daemon=True)
        _server_thread.start()
        return True, f"Webhook server successfully started on port {port}"
    except Exception as e:
        return False, f"Failed to start server on port {port}: {e}"

def stop_webhook_server():
    global _server_instance, _server_thread
    if _server_instance:
        _server_instance.shutdown()
        _server_instance.server_close()
        _server_instance = None
        _server_thread = None

if __name__ == "__main__":
    print(f"Starting TID Webhook receiver on http://localhost:{DEFAULT_PORT}/webhook ...")
    server = HTTPServer(('0.0.0.0', DEFAULT_PORT), TradingViewWebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down webhook server.")
        server.shutdown()
