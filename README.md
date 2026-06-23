# 🔌 CryptoDash API - Cryptocurrency Data Backend

*A high-performance FastAPI backend for real-time cryptocurrency data and portfolio tracking.*

**Deployed** https://cryptodash-api.railway.app/

---

## ✨ Features

### 📡 **Real-Time Price Streaming**
- **WebSocket support** for continuous price updates every 30 seconds.
- **5 featured cryptocurrencies** with live market data (Bitcoin, Ethereum, Solana, BNB, Cardano).
- **Automatic fallback** to mock data if API rate limits are exceeded.
- **Efficient broadcasting** to minimize API calls to CoinGecko.

### 🔍 **Search & Lookup**
- **Search any cryptocurrency** by name/symbol across 10,000+ coins.
- **Market ranking** — Get top coins sorted by market cap, volume, or price.
- **Detailed coin information** — Price, market cap, volume, changes, ATH/ATL, supply.
- **Smart caching** — Responses cached with configurable TTLs to optimize API usage.

### 📊 **Historical Data & Analysis**
- **Chart history** — Fetch price history for any cryptocurrency (1-365 days).
- **Concurrent requests** — Parallel data fetching with `asyncio.gather()`.
- **Time-series data** — Normalized timestamps for accurate charting.

### ⚖️ **Crypto Comparison**
- **Multi-coin comparison** — Fetch history for up to 4 coins simultaneously.
- **Normalized comparison** — Frontend can calculate % changes on equal footing.
- **Configurable duration** — Compare across any time period.

---

## 🛠️ Technologies

- **FastAPI** (Modern Python web framework)
- **Python 3.10+** (Async/await with asyncio)
- **httpx** (Async HTTP client)
- **CoinGecko API** (Free cryptocurrency data)
- **WebSocket** (Real-time connections)
- **CORS middleware** (Cross-origin requests)

---

## 🚀 API Endpoints

### WebSocket
```
GET /ws/prices
```
Stream live price updates (BTC, ETH, SOL, BNB, ADA)

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/prices` | Get latest prices for featured coins |
| GET | `/api/coin/{coin_id}` | Get detailed info for a single coin |
| GET | `/api/search?q={query}` | Search cryptocurrencies |
| GET | `/api/coins` | List all supported coins |
| GET | `/api/history/{coin_id}` | Get in-memory price history |
| GET | `/api/coin/{coin_id}/chart?days={n}` | Fetch chart data (1-365 days) |
| GET | `/api/top-coins?sort_by={field}` | Get top coins by ranking |
| GET | `/api/compare?coins={ids}&days={n}` | Compare multiple cryptocurrencies |
| GET | `/ping` | Health check (shows API key status) |

---

## 🔧 Smart Caching Strategy

### Per-Endpoint TTL
```python
"prices":    30s     # Real-time updates
"detail":    60s     # Coin info
"search":    120s    # Search results
"top_coins": 120s    # Rankings
"chart_1":   300s    # 24-hour charts
"chart_7":   900s    # Weekly charts
"chart_30":  1800s   # Monthly charts
"chart_90":  3600s   # 90-day charts
"chart_365": 7200s   # Yearly charts
```

### Rate Limit Handling
- Graceful fallback to cached data on HTTP 429
- Automatic mock price generation if API is unavailable
- Detailed logging with `[LIVE]` vs `[NO-KEY]` tags

---

## 🔐 Environment Variables

```env
COINGECKO_API_KEY=your_api_key_here          # Optional: Free or Pro tier
ALLOWED_ORIGINS=https://frontend.example.com # CORS whitelist
```

---

## 🚀 Deployment

Hosted on **Railway** with:
- Automatic deployments from `develop` branch
- Environment variable configuration
- CORS configured for Vercel frontend
- 30-second broadcast interval (respects Demo API limits)

---

## 📈 Performance Optimizations

- **Async/await** for non-blocking I/O
- **Concurrent API calls** with `asyncio.gather()`
- **In-memory caching** with TTL-based expiration
- **Selective API requests** — Only fetch what's changed
- **Connection pooling** with httpx

---

## 🔮 Future Improvements

- `Redis cache` for distributed caching
- `Database storage` for historical data
- `Advanced filters` (market cap ranges, volume thresholds)
- `Order book data` (bid/ask spreads)
- `Technical indicators` (RSI, MACD, Bollinger Bands)
- `Alert system` (price triggers, webhooks)
- `Rate limiting` (per-IP request throttling)
- `API authentication` (API keys for premium features)

---

## 📚 Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload

# Run server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---
