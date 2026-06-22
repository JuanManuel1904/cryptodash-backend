# CryptoDash — Backend

FastAPI backend que consume la API de CoinGecko y distribuye precios en tiempo real por WebSocket.

## Stack

- **FastAPI** — framework web async
- **Uvicorn** — servidor ASGI
- **httpx** — cliente HTTP async para CoinGecko
- **APScheduler** — scheduler para polling cada 10s
- **WebSockets** — broadcast de precios a todos los clientes conectados

## Desarrollo local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar variables de entorno
cp .env.example .env

# Correr el servidor
uvicorn app.main:app --reload --port 8000
```

Verificar que funciona: http://localhost:8000/ping

## Deploy

Ver instrucciones en la Fase 5 del plan de desarrollo.
