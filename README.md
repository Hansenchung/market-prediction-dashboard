# Northstar — Market Outlook Dashboard

A web dashboard that fetches daily stock market OHLCV data via Alpha Vantage and plots log-linear trend projections alongside company financial metrics[cite: 1, 2].

## Features
- **Live Data Proxy Server**: Python HTTP server proxying Alpha Vantage requests with local caching[cite: 2].
- **Interactive UI**: Client-side rendering of market overview, daily stock trend extrapolation, and top company metrics[cite: 1, 2].

## Prerequisites
- Python 3.8+ (uses built-in standard libraries like `http.server` and `urllib`)[cite: 2]
- An API key from [Alpha Vantage](https://www.alphavantage.co/)[cite: 2]

## Quick Start

1. **Set your Alpha Vantage API Key**:
   - **Linux/macOS**:
     ```bash
     export ALPHAVANTAGE_API_KEY="your_api_key_here"
     ```
   - **Windows (Command Prompt)**:
     ```cmd
     set ALPHAVANTAGE_API_KEY="your_api_key_here"
     ```
   - **Windows (PowerShell)**:
     ```powershell
     $env:ALPHAVANTAGE_API_KEY="your_api_key_here"
     ```

2. **Run the Server**:
   ```bash
   python market_data_server.py