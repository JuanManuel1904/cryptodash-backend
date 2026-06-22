import httpx
from collections import deque
from datetime import datetime
import random

COINS = ["bitcoin", "ethereum", "solana", "binancecoin", "cardano"]

COIN_META = {
    "bitcoin":     {"symbol": "BTC", "name": "Bitcoin",  "image": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png"},
    "ethereum":    {"symbol": "ETH", "name": "Ethereum", "image": "https://assets.coingecko.com/coins/images/279/large/ethereum.png"},
    "solana":      {"symbol": "SOL", "name": "Solana",   "image": "https://assets.coingecko.com/coins/images/4128/large/solana.png"},
    "binancecoin": {"symbol": "BNB", "name": "BNB",      "image": "https://assets.coingecko.com/coins/images/825/large/bnb-icon2_2x.png"},
    "cardano":     {"symbol": "ADA", "name": "Cardano",  "image": "https://assets.coingecko.com/coins/images/975/large/cardano.png"},
}

MOCK_BASE_PRICES = {
    "bitcoin": 67000.0,
    "ethereum": 3500.0,
    "solana": 170.0,
    "binancecoin": 590.0,
    "cardano": 0.45,
}

MAX_HISTORY = 60

price_history: dict[str, deque] = {
    coin: deque(maxlen=MAX_HISTORY) for coin in COINS
}

_last_prices: dict[str, float] = dict(MOCK_BASE_PRICES)


def _generate_mock_prices() -> list[dict]:
    """Genera precios simulados con variación realista. Usado como fallback."""
    now = datetime.utcnow().isoformat()
    result = []

    for coin_id in COINS:
        base = _last_prices[coin_id]
        change_pct = random.uniform(-0.003, 0.003)
        new_price = round(base * (1 + change_pct), 8)
        _last_prices[coin_id] = new_price

        price_history[coin_id].append({"timestamp": now, "price": new_price})

        meta = COIN_META[coin_id]
        result.append({
            "id": coin_id,
            "symbol": meta["symbol"],
            "name": meta["name"],
            "image": meta["image"],
            "price": new_price,
            "market_cap": int(new_price * random.uniform(18_000_000, 20_000_000)),
            "volume_24h": int(new_price * random.uniform(400_000, 600_000)),
            "change_1h": round(random.uniform(-1.5, 1.5), 2),
            "change_24h": round(random.uniform(-4.0, 4.0), 2),
            "change_7d": round(random.uniform(-8.0, 8.0), 2),
            "timestamp": now,
            "source": "mock",
        })

    return result


async def fetch_prices() -> list[dict] | None:
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(COINS),
        "order": "market_cap_desc",
        "price_change_percentage": "1h,24h,7d",
    }
    headers = {
        "User-Agent": "CryptoDash/1.0 (portfolio project)",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            now = datetime.utcnow().isoformat()
            result = []

            for coin in data:
                coin_id = coin["id"]
                price = coin["current_price"]
                _last_prices[coin_id] = price

                price_history[coin_id].append({"timestamp": now, "price": price})

                result.append({
                    "id": coin_id,
                    "symbol": coin["symbol"].upper(),
                    "name": coin["name"],
                    "image": coin["image"],
                    "price": price,
                    "market_cap": coin["market_cap"],
                    "volume_24h": coin["total_volume"],
                    "change_1h": coin.get("price_change_percentage_1h_in_currency"),
                    "change_24h": coin.get("price_change_percentage_24h"),
                    "change_7d": coin.get("price_change_percentage_7d_in_currency"),
                    "timestamp": now,
                    "source": "live",
                })

            return result

        except Exception as e:
            print(f"[CoinGecko] Error: {e} — usando mock data")
            return _generate_mock_prices()


def get_history(coin_id: str) -> list:
    return list(price_history.get(coin_id, []))
