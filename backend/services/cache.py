import time
import asyncio
import threading
from functools import wraps


class TTLCache:
    """简单的内存 TTL 缓存，避免重复调用 yfinance / 外部 API。"""

    def __init__(self, ttl_seconds: float = 300):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, object]] = {}

    def get(self, key: str):
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, val = entry
        if time.monotonic() - ts > self._ttl:
            self._store.pop(key, None)
            return None
        return val

    def set(self, key: str, value):
        self._store[key] = (time.monotonic(), value)

    def clear(self):
        self._store.clear()


class YFRateLimiter:
    """全局 yfinance 调用节流器，确保两次调用间隔 >= min_interval 秒。"""

    def __init__(self, min_interval: float = 3.0):
        self._min_interval = min_interval
        self._last_call = 0.0
        self._lock = threading.Lock()

    def acquire(self):
        """阻塞直到可以发起下一次 yfinance 调用。"""
        with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()


# 缓存 yfinance 行情/K线结果，5 分钟过期，避免触发 Yahoo 频率限制
yf_cache = TTLCache(ttl_seconds=300)

# 全局 yfinance 节流器：每次调用至少间隔 3 秒
yf_throttle = YFRateLimiter(min_interval=3.0)
