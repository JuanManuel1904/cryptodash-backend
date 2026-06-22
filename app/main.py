import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.ws_manager import manager
from app.coingecko import fetch_prices, get_history, COINS


async def price_broadcast_loop():
    while True:
        prices = await fetch_prices()
        if prices:
            await manager.broadcast({"type": "prices", "data": prices})
            print(f"[Scheduler] Broadcast a {len(manager.active_connections)} cliente(s)")
        else:
            print("[Scheduler] Sin datos, reintentando en 10s")
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(price_broadcast_loop())
    yield
    task.cancel()


app = FastAPI(
    title="CryptoDash API",
    version="1.0.0",
    description="""
## CryptoDash Backend

Precios de criptomonedas en tiempo real consumidos desde CoinGecko.

### Endpoints REST
Usa `/api/prices` para un snapshot inicial y `/api/history/{coin_id}` para el historial en memoria.

### WebSocket
Conéctate a `/ws/prices` para recibir actualizaciones cada 10 segundos.

```js
const ws = new WebSocket('ws://localhost:8000/ws/prices')
ws.onmessage = e => console.log(JSON.parse(e.data))
```

### Monedas soportadas
`bitcoin` · `ethereum` · `solana` · `binancecoin` · `cardano`
    """,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping", tags=["Health"])
async def ping():
    """Verifica que el servidor está corriendo."""
    return {"status": "ok", "message": "CryptoDash backend running"}


@app.get("/api/prices", tags=["Prices"])
async def get_prices():
    """
    Retorna el precio actual de todas las monedas soportadas.

    Útil para la carga inicial del dashboard antes de conectar el WebSocket.
    El campo `source` indica si los datos son `live` (CoinGecko) o `mock` (fallback).
    """
    prices = await fetch_prices()
    if prices is None:
        return {"error": "No se pudo obtener datos de CoinGecko"}
    return {"data": prices}


@app.get("/api/history/{coin_id}", tags=["Prices"])
async def get_coin_history(coin_id: str):
    """
    Retorna el historial de precios en memoria de una moneda (últimos 60 puntos).

    **coin_id** debe ser uno de: `bitcoin`, `ethereum`, `solana`, `binancecoin`, `cardano`
    """
    if coin_id not in COINS:
        return {"error": f"Moneda no soportada. Opciones: {COINS}"}
    return {"coin_id": coin_id, "history": get_history(coin_id)}


@app.get("/api/coins", tags=["Prices"])
async def get_supported_coins():
    """Lista las monedas soportadas con sus metadatos."""
    from app.coingecko import COIN_META
    return {"coins": [
        {"id": coin_id, **meta}
        for coin_id, meta in COIN_META.items()
    ]}


@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """
    WebSocket que emite precios actualizados cada 10 segundos.

    Formato del mensaje:
    ```json
    {
      "type": "prices",
      "data": [{ "id": "bitcoin", "price": 67000, ... }]
    }
    ```
    """
    await manager.connect(websocket)
    print(f"[WS] Cliente conectado. Total: {len(manager.active_connections)}")
    try:
        prices = await fetch_prices()
        if prices:
            await websocket.send_json({"type": "prices", "data": prices})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"[WS] Cliente desconectado. Total: {len(manager.active_connections)}")
