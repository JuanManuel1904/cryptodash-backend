import os
import time
import random
import httpx
from collections import deque
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL    = "https://api.coingecko.com/api/v3"
MAX_HISTORY = 60

COINS = ["bitcoin", "ethereum", "solana", "binancecoin", "cardano"]

COIN_META = {
    "bitcoin":     {"symbol": "BTC", "name": "Bitcoin",  "image": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png"},
    "ethereum":    {"symbol": "ETH", "name": "Ethereum", "image": "https://assets.coingecko.com/coins/images/279/large/ethereum.png"},
    "solana":      {"symbol": "SOL", "name": "Solana",   "image": "https://assets.coingecko.com/coins/images/4128/large/solana.png"},
    "binancecoin": {"symbol": "BNB", "name": "BNB",      "image": "https://assets.coingecko.com/coins/images/825/large/bnb-icon2_2x.png"},
    "cardano":     {"symbol": "ADA", "name": "Cardano",  "image": "https://assets.coingecko.com/coins/images/975/large/cardano.png"},
}

MOCK_BASE_PRICES = {
    "bitcoin": 105000.0,
    "ethereum": 2500.0,
    "solana": 155.0,
    "binancecoin": 650.0,
    "cardano": 0.62,
}

# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------

price_history: dict[str, deque] = {c: deque(maxlen=MAX_HISTORY) for c in COINS}
_last_prices:  dict[str, float]  = dict(MOCK_BASE_PRICES)

# Caches: key → (stored_at, data)
_cache: dict[str, tuple[float, object]] = {}

CACHE_TTL = {
    "prices":    30,    # broadcast already updates every 30s; REST snapshot can reuse
    "detail":    60,
    "search":    120,
    "top_coins": 120,
    "chart_1":   300,
    "chart_7":   900,
    "chart_30":  1800,
    "chart_90":  3600,
    "chart_365": 7200,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headers() -> dict:
    """Build request headers. Reads API key lazily so load_dotenv() timing doesn't matter."""
    h = {
        "User-Agent": "CryptoDash/1.0",
        "Accept":     "application/json",
    }
    key = os.getenv("COINGECKO_API_KEY", "").strip()
    if key:
        h["x-cg-demo-api-key"] = key
    return h


def _from_cache(key: str) -> object | None:
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL.get(key.split(":")[0], 120):
        return entry[1]
    return None


def _to_cache(key: str, data: object) -> None:
    _cache[key] = (time.time(), data)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(label: str, status: int) -> None:
    key = os.getenv("COINGECKO_API_KEY", "").strip()
    tag = "[LIVE]" if key else "[NO-KEY]"
    print(f"[CoinGecko] {tag} {label} → {status}")


# ---------------------------------------------------------------------------
# Mock fallback
# ---------------------------------------------------------------------------

def _generate_mock_prices() -> list[dict]:
    now    = _now()
    result = []
    for coin_id in COINS:
        base       = _last_prices[coin_id]
        new_price  = round(base * (1 + random.uniform(-0.003, 0.003)), 8)
        _last_prices[coin_id] = new_price
        price_history[coin_id].append({"timestamp": now, "price": new_price})
        meta = COIN_META[coin_id]
        result.append({
            "id":                 coin_id,
            "symbol":             meta["symbol"],
            "name":               meta["name"],
            "image":              meta["image"],
            "price":              new_price,
            "high_24h":           round(new_price * random.uniform(1.001, 1.02), 8),
            "low_24h":            round(new_price * random.uniform(0.98, 0.999), 8),
            "market_cap":         int(new_price * random.uniform(18_000_000, 20_000_000)),
            "volume_24h":         int(new_price * random.uniform(400_000, 600_000)),
            "change_1h":          round(random.uniform(-1.5, 1.5), 2),
            "change_24h":         round(random.uniform(-4.0, 4.0), 2),
            "change_7d":          round(random.uniform(-8.0, 8.0), 2),
            "ath":                round(new_price * random.uniform(1.5, 3.0), 8),
            "atl":                round(new_price * random.uniform(0.01, 0.3), 8),
            "circulating_supply": round(new_price * 18_000_000, 0),
            "timestamp":          now,
            "source":             "mock",
        })
    return result


# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------

async def fetch_prices() -> list[dict]:
    cached = _from_cache("prices:main")
    if cached:
        return cached

    url    = f"{BASE_URL}/coins/markets"
    params = {
        "vs_currency":            "usd",
        "ids":                    ",".join(COINS),
        "order":                  "market_cap_desc",
        "price_change_percentage":"1h,24h,7d",
    }
    async with httpx.AsyncClient(timeout=12.0) as client:
        try:
            r = await client.get(url, params=params, headers=_headers())
            _log("prices", r.status_code)
            if r.status_code == 429:
                return cached or _generate_mock_prices()
            r.raise_for_status()

            now    = _now()
            result = []
            for coin in r.json():
                cid   = coin["id"]
                price = coin["current_price"]
                _last_prices[cid] = price
                price_history[cid].append({"timestamp": now, "price": price})
                result.append({
                    "id":                 cid,
                    "symbol":             coin["symbol"].upper(),
                    "name":               coin["name"],
                    "image":              coin["image"],
                    "price":              price,
                    "high_24h":           coin.get("high_24h"),
                    "low_24h":            coin.get("low_24h"),
                    "market_cap":         coin.get("market_cap"),
                    "volume_24h":         coin.get("total_volume"),
                    "change_1h":          coin.get("price_change_percentage_1h_in_currency"),
                    "change_24h":         coin.get("price_change_percentage_24h"),
                    "change_7d":          coin.get("price_change_percentage_7d_in_currency"),
                    "ath":                coin.get("ath"),
                    "atl":                coin.get("atl"),
                    "circulating_supply": coin.get("circulating_supply"),
                    "timestamp":          now,
                    "source":             "live",
                })
            _to_cache("prices:main", result)
            return result

        except Exception as e:
            print(f"[CoinGecko] prices error: {e} — using mock")
            return _generate_mock_prices()


def get_history(coin_id: str) -> list:
    return list(price_history.get(coin_id, []))


async def fetch_coin_detail(coin_id: str) -> dict | None:
    cache_key = f"detail:{coin_id}"
    cached    = _from_cache(cache_key)
    if cached:
        return cached

    url    = f"{BASE_URL}/coins/markets"
    params = {
        "vs_currency":             "usd",
        "ids":                     coin_id,
        "price_change_percentage": "1h,24h,7d",
    }
    async with httpx.AsyncClient(timeout=12.0) as client:
        try:
            r = await client.get(url, params=params, headers=_headers())
            _log(f"detail/{coin_id}", r.status_code)
            if r.status_code == 429:
                return cached
            r.raise_for_status()
            data = r.json()
            if not data:
                return None
            c      = data[0]
            result = {
                "id":                 c["id"],
                "symbol":             c["symbol"].upper(),
                "name":               c["name"],
                "image":              c["image"],
                "price":              c["current_price"],
                "high_24h":           c.get("high_24h"),
                "low_24h":            c.get("low_24h"),
                "market_cap":         c.get("market_cap"),
                "volume_24h":         c.get("total_volume"),
                "change_1h":          c.get("price_change_percentage_1h_in_currency"),
                "change_24h":         c.get("price_change_percentage_24h"),
                "change_7d":          c.get("price_change_percentage_7d_in_currency"),
                "ath":                c.get("ath"),
                "atl":                c.get("atl"),
                "circulating_supply": c.get("circulating_supply"),
                "source":             "live",
            }
            _to_cache(cache_key, result)
            return result
        except Exception as e:
            print(f"[CoinGecko] detail error: {e}")
            return cached


async def search_coins(query: str) -> list[dict]:
    cache_key = f"search:{query.lower()}"
    cached    = _from_cache(cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(
                f"{BASE_URL}/search",
                params={"query": query},
                headers=_headers(),
            )
            _log(f"search/{query}", r.status_code)
            if r.status_code == 429:
                return cached or []
            r.raise_for_status()
            coins  = r.json().get("coins", [])[:20]
            result = [
                {
                    "id":              c["id"],
                    "name":            c["name"],
                    "symbol":          c["symbol"].upper(),
                    "image":           c.get("large") or c.get("thumb", ""),
                    "market_cap_rank": c.get("market_cap_rank"),
                }
                for c in coins
            ]
            _to_cache(cache_key, result)
            return result
        except Exception as e:
            print(f"[CoinGecko] search error: {e}")
            return cached or []


async def fetch_top_coins(sort_by: str = "market_cap", per_page: int = 50) -> list[dict]:
    cache_key = f"top_coins:{sort_by}"
    cached    = _from_cache(cache_key)
    if cached:
        return cached

    order_map = {
        "market_cap": "market_cap_desc",
        "volume":     "volume_desc",
        "price":      "market_cap_desc",
    }
    params = {
        "vs_currency":             "usd",
        "order":                   order_map.get(sort_by, "market_cap_desc"),
        "per_page":                per_page,
        "page":                    1,
        "price_change_percentage": "1h,24h,7d",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(f"{BASE_URL}/coins/markets", params=params, headers=_headers())
            _log(f"top-coins/{sort_by}", r.status_code)
            if r.status_code == 429:
                return cached or []
            r.raise_for_status()
            coins = [
                {
                    "id":              c["id"],
                    "name":            c["name"],
                    "symbol":          c["symbol"].upper(),
                    "image":           c["image"],
                    "price":           c["current_price"],
                    "market_cap":      c.get("market_cap"),
                    "volume_24h":      c.get("total_volume"),
                    "change_1h":       c.get("price_change_percentage_1h_in_currency"),
                    "change_24h":      c.get("price_change_percentage_24h"),
                    "change_7d":       c.get("price_change_percentage_7d_in_currency"),
                    "market_cap_rank": c.get("market_cap_rank"),
                }
                for c in r.json()
            ]
            if sort_by == "price":
                coins.sort(key=lambda c: c["price"] or 0, reverse=True)
            _to_cache(cache_key, coins)
            return coins
        except Exception as e:
            print(f"[CoinGecko] top-coins error: {e}")
            return cached or []


async def fetch_chart_history(coin_id: str, days: int) -> list[dict]:
    cache_key = f"chart_{days}:{coin_id}"
    cached    = _from_cache(cache_key)
    if cached:
        return cached

    params = {"vs_currency": "usd", "days": days}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(
                f"{BASE_URL}/coins/{coin_id}/market_chart",
                params=params,
                headers=_headers(),
            )
            _log(f"chart/{coin_id}/{days}d", r.status_code)
            if r.status_code == 429:
                return cached or []
            r.raise_for_status()
            points = [
                {
                    "timestamp": datetime.fromtimestamp(p[0] / 1000, tz=timezone.utc).isoformat(),
                    "price":     p[1],
                }
                for p in r.json().get("prices", [])
            ]
            _to_cache(cache_key, points)
            return points
        except Exception as e:
            print(f"[CoinGecko] chart error: {e}")
            return cached or []
