import asyncio
import time
import logging

import httpx

from backend.config import TWELVE_DATA_API_KEY
from backend.services.cache import yf_cache

logger = logging.getLogger(__name__)

TWELVE_DATA_BASE = "https://api.twelvedata.com"

_INTERVAL_MAP = {"1d": "1day", "1wk": "1week", "1mo": "1month"}

_PERIOD_DAYS = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "max": 3650}
_INTERVAL_DAYS = {"1d": 1, "1wk": 7, "1mo": 30}


class AsyncRateLimiter:
    """Async sliding-window rate limiter for Twelve Data (8 req / 60 s free tier)."""

    def __init__(self, max_requests: int = 8, window_seconds: float = 60.0):
        self._max = max_requests
        self._window = window_seconds
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            self._timestamps = [t for t in self._timestamps if now - t < self._window]
            if len(self._timestamps) >= self._max:
                wait = self._timestamps[0] + self._window - now + 0.5
                if wait > 0:
                    logger.info(f"Twelve Data rate limiter: waiting {wait:.1f}s")
                    await asyncio.sleep(wait)
                    now = time.monotonic()
                    self._timestamps = [t for t in self._timestamps if now - t < self._window]
            self._timestamps.append(now)


_twelve_data_limiter = AsyncRateLimiter()


def _calc_outputsize(period: str, interval: str) -> int:
    days = _PERIOD_DAYS.get(period, 90)
    ival_days = _INTERVAL_DAYS.get(interval, 1)
    return max(min(days // ival_days + 10, 5000), 30)


async def get_twelve_data_quote(symbol: str) -> dict | None:
    """Get US stock quote from Twelve Data. Returns None on any failure (graceful degradation)."""
    if not TWELVE_DATA_API_KEY:
        return None

    cache_key = f"quote:{symbol}"
    cached = yf_cache.get(cache_key)
    if cached is not None:
        return cached

    await _twelve_data_limiter.acquire()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{TWELVE_DATA_BASE}/quote",
                params={"symbol": symbol, "apikey": TWELVE_DATA_API_KEY},
            )
            data = resp.json()
    except Exception as e:
        logger.warning(f"Twelve Data quote for {symbol} failed: {e}")
        return None

    if not isinstance(data, dict):
        return None
    if data.get("status") == "error" or "code" in data:
        logger.warning(f"Twelve Data quote error for {symbol}: {data.get('message', data)}")
        return None

    close = data.get("close")
    if close is None or close == "0":
        return None

    change = float(data.get("change", 0) or 0)
    pct = data.get("percent_change")
    change_pct = f"{float(pct):.2f}%" if pct else "0.00%"

    result = {
        "symbol": symbol.upper(),
        "price": round(float(close), 2),
        "change": round(change, 3),
        "change_percent": change_pct,
        "volume": int(data.get("volume", 0)),
    }
    yf_cache.set(cache_key, result)
    return result


async def get_twelve_data_candles(
    symbol: str, period: str = "3mo", interval: str = "1d"
) -> dict | None:
    """Get US stock candles from Twelve Data. Returns None on any failure."""
    if not TWELVE_DATA_API_KEY:
        return None

    cache_key = f"candles:{symbol}:{period}:{interval}"
    cached = yf_cache.get(cache_key)
    if cached is not None:
        return cached

    td_interval = _INTERVAL_MAP.get(interval, "1day")
    outputsize = _calc_outputsize(period, interval)

    await _twelve_data_limiter.acquire()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{TWELVE_DATA_BASE}/time_series",
                params={
                    "symbol": symbol,
                    "interval": td_interval,
                    "outputsize": outputsize,
                    "apikey": TWELVE_DATA_API_KEY,
                },
            )
            data = resp.json()
    except Exception as e:
        logger.warning(f"Twelve Data candles for {symbol} failed: {e}")
        return None

    if not isinstance(data, dict):
        return None
    if data.get("status") != "ok":
        logger.warning(f"Twelve Data candles error for {symbol}: {data.get('message', data)}")
        return None

    values = data.get("values")
    if not values or not isinstance(values, list):
        return None

    candles = []
    for v in reversed(values):  # Twelve Data returns newest first, reverse to chronological
        candles.append({
            "date": v["datetime"],
            "open": round(float(v["open"]), 2),
            "high": round(float(v["high"]), 2),
            "low": round(float(v["low"]), 2),
            "close": round(float(v["close"]), 2),
            "volume": int(v["volume"]),
        })

    result = {"symbol": symbol, "period": interval, "candles": candles}
    yf_cache.set(cache_key, result)
    return result
