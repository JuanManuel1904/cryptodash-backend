import asyncio
import os
from contextlib import asynccontextmanager

# load_dotenv MUST run before any app module is imported so os.getenv() works everywhere
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.ws_manager import manager
from app.coingecko import (
    fetch_prices, get_history, COINS,
    fetch_coin_detail, search_coins,
    fetch_top_coins, fetch_chart_history, fetch_compare,
    COIN_META,
)

# ---------------------------------------------------------------------------
# Background broadcast
# ---------------------------------------------------------------------------

BROADCAST_INTERVAL = 30  # seconds — safe margin for Demo API (30 req/min)


async def price_broadcast_loop():
    await asyncio.sleep(2)  # let server finish startup
    while True:
        try:
            prices = await fetch_prices()
            if prices and manager.active_connections:
                await manager.broadcast({"type": "prices", "data": prices})
                print(f"[Broadcast] {len(prices)} coins → {len(manager.active_connections)} client(s)")
        except Exception as e:
            print(f"[Broadcast] error: {e}")
        await asyncio.sleep(BROADCAST_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(price_broadcast_loop())
    yield
    task.cancel()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="CryptoDash API", version="2.0.0", lifespan=lifespan)

_raw_origins    = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/ping")
async def ping():
    key = os.getenv("COINGECKO_API_KEY", "").strip()
    return {"status": "ok", "api_key_loaded": bool(key)}


@app.get("/api/prices")
async def get_prices():
    return {"data": await fetch_prices()}


@app.get("/api/coins")
async def get_supported_coins():
    return {"coins": [{"id": cid, **meta} for cid, meta in COIN_META.items()]}


@app.get("/api/history/{coin_id}")
async def get_coin_history(coin_id: str):
    if coin_id not in COINS:
        return {"error": f"Unsupported coin. Options: {COINS}"}
    return {"coin_id": coin_id, "history": get_history(coin_id)}


@app.get("/api/coin/{coin_id}/chart")
async def get_coin_chart(coin_id: str, days: int = 1):
    days = max(1, min(days, 365))
    return {"coin_id": coin_id, "days": days, "points": await fetch_chart_history(coin_id, days)}


@app.get("/api/coin/{coin_id}")
async def get_coin_detail(coin_id: str):
    detail = await fetch_coin_detail(coin_id)
    if not detail:
        return {"error": f"No data for '{coin_id}'"}
    return {"data": detail}


@app.get("/api/search")
async def search(q: str = ""):
    if not q.strip():
        return {"results": []}
    return {"results": await search_coins(q.strip())}


@app.get("/api/compare")
async def compare_coins(coins: str = "bitcoin,ethereum", days: int = 7):
    """Compare chart history for multiple coins. coins = comma-separated CoinGecko IDs."""
    ids  = [c.strip() for c in coins.split(",") if c.strip()][:4]  # max 4
    days = max(1, min(days, 365))
    data = await fetch_compare(ids, days)
    return {"days": days, "coins": data}


@app.get("/api/top-coins")
async def get_top_coins(sort_by: str = "market_cap", per_page: int = 50):
    per_page = max(10, min(per_page, 250))
    return {"coins": await fetch_top_coins(sort_by=sort_by, per_page=per_page)}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    await manager.connect(websocket)
    print(f"[WS] Client connected. Total: {len(manager.active_connections)}")
    try:
        prices = await fetch_prices()
        if prices:
            await websocket.send_json({"type": "prices", "data": prices})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"[WS] Client disconnected. Total: {len(manager.active_connections)}")
