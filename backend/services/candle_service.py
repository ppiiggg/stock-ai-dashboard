import time
import random
import logging

import httpx
import yfinance as yf

from backend.services.cache import yf_cache, yf_throttle
from backend.services.twelve_data_service import get_twelve_data_candles

logger = logging.getLogger(__name__)


async def get_candles(symbol: str, period: str = "3mo", interval: str = "1d") -> dict:
    """Get daily K-line data.

    A-share: Sina Finance.  US stock: Twelve Data -> yfinance.
    """
    resolved = symbol.strip().upper()

    if _is_china_stock(resolved):
        return await _get_a_share_candles(resolved, period)

    # US stock: Twelve Data first, yfinance as fallback
    td_result = await get_twelve_data_candles(resolved, period, interval)
    if td_result is not None and td_result.get("candles"):
        return td_result

    return await _get_us_candles(resolved, period, interval)


def _is_china_stock(raw: str) -> bool:
    s = raw.strip()
    return s.isdigit() and len(s) == 6


def _resolve_sina_code(raw: str) -> str:
    s = raw.strip().upper()
    if s[0] in ("0", "3"):
        return f"sz{s}"
    if s[0] == "6":
        return f"sh{s}"
    return s


def _is_transient_yf_error(err: Exception) -> bool:
    msg = str(err).lower()
    transient = ("rate limited", "too many requests", "timeout",
                 "connection", "remote end closed", "no response")
    return any(kw in msg for kw in transient)


async def _get_us_candles(symbol: str, period: str, interval: str) -> dict:
    """Get US stock candles from yfinance with cache."""
    cache_key = f"candles:{symbol}:{period}:{interval}"

    cached = yf_cache.get(cache_key)
    if cached is not None:
        return cached

    ticker = yf.Ticker(symbol)
    df = None
    last_err = None

    for attempt in range(4):
        try:
            yf_throttle.acquire()
            df = ticker.history(period=period, interval=interval)
            if not df.empty:
                break
            last_err = ValueError("empty data returned")
        except Exception as e:
            last_err = e
            if not _is_transient_yf_error(e):
                raise

        if attempt < 3:
            time.sleep((2 ** attempt) * 2 + random.uniform(0, 1))

    if df is None or df.empty:
        msg = f"Cannot get K-line data for {symbol}"
        if last_err:
            msg += f" ({last_err})"
        raise ValueError(msg)

    candles = []
    for idx, row in df.iterrows():
        candles.append({
            "date": idx.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })

    result = {"symbol": symbol, "period": interval, "candles": candles}
    yf_cache.set(cache_key, result)
    return result


async def _get_a_share_candles(symbol: str, period: str) -> dict:
    """Get A-share daily K-line from Sina Finance (free, no rate limit)."""
    code = _resolve_sina_code(symbol)

    days_map = {"1mo": 22, "3mo": 66, "6mo": 130, "1y": 260, "2y": 520, "max": 2000}
    datalen = days_map.get(period, 66)

    url = (
        "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        f"CN_MarketData.getKLineData?symbol={code}&scale=240&ma=no&datalen={datalen}"
    )
    headers = {"Referer": "https://finance.sina.com.cn"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=headers)
        resp.encoding = "gb2312"
        data = resp.json()

    if not data or not isinstance(data, list) or len(data) == 0:
        raise ValueError(f"Cannot get K-line data for {symbol}, check the ticker")

    candles = []
    for item in data:
        candles.append({
            "date": str(item["day"]),
            "open": round(float(item["open"]), 2),
            "high": round(float(item["high"]), 2),
            "low": round(float(item["low"]), 2),
            "close": round(float(item["close"]), 2),
            "volume": int(item["volume"]),
        })

    return {"symbol": symbol, "period": "1d", "candles": candles}
