import json
import os
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen


HOST = "127.0.0.1"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "market prediction.html"
ALLOWED_SYMBOLS = {"AAPL", "MSFT", "NVDA", "AMZN"}
CACHE_SECONDS = 900
cache = {}


class MarketDataHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/bars":
            self.handle_bars()
        elif path in {"/", "/market%20prediction.html", "/market prediction.html"}:
            self.serve_page()
        else:
            self.send_json(404, {"error": "Not found."})

    def handle_bars(self):
        symbol_values = parse_qs(urlsplit(self.path).query).get("symbol", [])
        symbol = symbol_values[0].upper() if symbol_values else ""
        if symbol not in ALLOWED_SYMBOLS:
            self.send_json(400, {"error": "Unsupported symbol. Choose AAPL, MSFT, NVDA, or AMZN."})
            return

        api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
        if not api_key:
            self.send_json(503, {"error": "Set the ALPHAVANTAGE_API_KEY environment variable before requesting live data."})
            return

        cached = cache.get(symbol)
        if cached and time.monotonic() - cached["saved_at"] < CACHE_SECONDS:
            self.send_json(200, cached["response"])
            return

        parameters = urlencode({
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact",
            "apikey": api_key,
        })
        request = Request(
            f"https://www.alphavantage.co/query?{parameters}",
            headers={"User-Agent": "NorthstarMarketOutlook/1.0"},
        )
        try:
            with urlopen(request, timeout=20) as upstream:
                payload = json.loads(upstream.read().decode("utf-8"))
        except HTTPError as error:
            self.send_json(502, {"error": f"Alpha Vantage returned HTTP {error.code}."})
            return
        except URLError as error:
            self.send_json(502, {"error": f"Could not reach Alpha Vantage: {error.reason}."})
            return
        except (TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as error:
            self.send_json(502, {"error": f"Could not read a valid Alpha Vantage response: {error}."})
            return

        message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
        if message:
            self.send_json(502, {"error": f"Alpha Vantage: {message}"})
            return

        time_series = payload.get("Time Series (Daily)")
        if not isinstance(time_series, dict):
            self.send_json(502, {"error": "Alpha Vantage response did not contain daily OHLCV bars."})
            return

        bars = []
        try:
            for timestamp, values in sorted(time_series.items()):
                bar = {
                    "timestamp": timestamp,
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": int(values["5. volume"]),
                }
                if min(bar["open"], bar["high"], bar["low"], bar["close"]) <= 0 or bar["volume"] < 0:
                    raise ValueError("OHLCV values must be positive, with non-negative volume.")
                bars.append(bar)
        except (KeyError, TypeError, ValueError) as error:
            self.send_json(502, {"error": f"Alpha Vantage returned an invalid daily bar: {error}."})
            return

        if len(bars) < 2:
            self.send_json(502, {"error": "Alpha Vantage returned fewer than two daily bars."})
            return

        response = {
            "symbol": symbol,
            "source": "Alpha Vantage",
            "interval": "1day",
            "retrievedAt": datetime.now(timezone.utc).isoformat(),
            "bars": bars,
        }
        cache[symbol] = {"saved_at": time.monotonic(), "response": response}
        self.send_json(200, response)

    def serve_page(self):
        try:
            content = HTML_FILE.read_bytes()
        except OSError as error:
            self.send_json(500, {"error": f"Could not read the market outlook page: {error}."})
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, status, payload):
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")


if __name__ == "__main__":
    if not HTML_FILE.is_file():
        raise SystemExit(f"Market page not found: {HTML_FILE}")

    print(f"Serving Northstar at http://{HOST}:{PORT}/")
    print("Set ALPHAVANTAGE_API_KEY in the environment to enable live daily OHLCV data.")
    ThreadingHTTPServer((HOST, PORT), MarketDataHandler).serve_forever()
