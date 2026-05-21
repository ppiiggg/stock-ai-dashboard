import time
import random
import logging

import httpx
import yfinance as yf

from backend.config import FINNHUB_API_KEY
from backend.services.cache import yf_cache, yf_throttle
from backend.services.china_stock_service import get_china_stock_quote
from backend.services.twelve_data_service import get_twelve_data_quote

logger = logging.getLogger(__name__)
FINNHUB_URL = "https://finnhub.io/api/v1/quote"


def is_china_stock(raw: str) -> bool:
    s = raw.strip()
    return s.isdigit() and len(s) == 6


def resolve_finnhub_symbol(raw: str) -> str:
    return raw.strip().upper()


def _get_us_volume(symbol: str) -> int:
    """Get US stock volume from yfinance with cache, throttle, and retry."""
    cache_key = f"vol:{symbol}"

    cached = yf_cache.get(cache_key)
    if cached is not None:
        return cached

    ticker = yf.Ticker(symbol)
    last_err = None

    for attempt in range(3):
        try:
            yf_throttle.acquire()
            hist = ticker.history(period="5d")
            if not hist.empty:
                vol = int(hist["Volume"].iloc[-1])
                yf_cache.set(cache_key, vol)
                return vol
        except Exception as e:
            last_err = e
            logger.warning(f"Volume fetch attempt {attempt + 1}/3 for {symbol} failed: {e}")
            if attempt < 2:
                time.sleep((2 ** attempt) * 2 + random.uniform(0, 1))

    if last_err:
        logger.error(f"All volume fetch attempts for {symbol} failed: {last_err}")
    return 0


def _get_us_quote_from_yf(symbol: str) -> dict | None:
    """Get US stock quote from yfinance (5-min cache), used as primary source."""
    cache_key = f"quote:{symbol}"

    cached = yf_cache.get(cache_key)
    if cached is not None:
        return cached

    ticker = yf.Ticker(symbol)

    for attempt in range(3):
        try:
            yf_throttle.acquire()
            info = ticker.fast_info
            price = (getattr(info, "last_price", None)
                     or getattr(info, "regular_market_previous_close", None))
            prev_close = getattr(info, "regular_market_previous_close", None)

            if price is None:
                yf_throttle.acquire()
                hist = ticker.history(period="5d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else prev_close

            if price is None or price == 0:
                return None

            change = round(price - prev_close, 3) if prev_close else 0
            change_pct = f"{(change / prev_close * 100):.2f}%" if prev_close else "0.00%"
            volume = _get_us_volume(symbol)

            result = {
                "symbol": symbol.upper(),
                "price": round(float(price), 2),
                "change": change,
                "change_percent": change_pct,
                "volume": volume,
            }
            yf_cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.warning(f"YF quote attempt {attempt + 1}/3 for {symbol} failed: {e}")
            if attempt < 2:
                time.sleep((2 ** attempt) * 2 + random.uniform(0, 1))

    return None


async def _get_finnhub_quote(symbol: str) -> dict | None:
    """Get US stock quote from Finnhub (last-resort fallback)."""
    finnhub_symbol = resolve_finnhub_symbol(symbol)
    params = {"symbol": finnhub_symbol, "token": FINNHUB_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(FINNHUB_URL, params=params)
            data = resp.json()
    except Exception as e:
        logger.warning(f"Finnhub quote for {symbol} failed: {e}")
        return None

    if not data or data.get("c") in (0, None):
        return None

    change_percent = data.get("dp", 0)
    if change_percent is not None:
        change_percent = f"{change_percent:.2f}%"

    volume = _get_us_volume(symbol)

    return {
        "symbol": symbol.upper(),
        "price": float(data.get("c", 0)),
        "change": float(data.get("d", 0)),
        "change_percent": change_percent,
        "volume": volume,
    }


async def get_stock_quote(symbol: str) -> dict:
    """Get stock quote, auto-detect A-share vs US stock.

    US stock priority: Twelve Data -> yfinance -> Finnhub.
    """
    resolved = symbol.strip().upper()

    if is_china_stock(resolved):
        result = await get_china_stock_quote(resolved)
        result["market"] = "china"
        return result

    # 1) Twelve Data (primary)
    td_result = await get_twelve_data_quote(resolved)
    if td_result is not None and td_result.get("price", 0) > 0:
        td_result["market"] = "us"
        return td_result

    # 2) yfinance (first fallback)
    yf_result = _get_us_quote_from_yf(resolved)
    if yf_result is not None and yf_result.get("price", 0) > 0:
        yf_result["market"] = "us"
        return yf_result

    # 3) Finnhub (last resort)
    fh_result = await _get_finnhub_quote(resolved)
    if fh_result is not None and fh_result.get("price", 0) > 0:
        fh_result["market"] = "us"
        return fh_result

    raise ValueError(f"Cannot get quote for {symbol}, check the ticker")
