"""Generate a line-by-line annotated DOCX for twelve_data_service.py."""

from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "twelve_data_service_详解.docx")

doc = Document()

# ── Page margins ──
for section in doc.sections:
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

# ── Style helpers ──
CODE_FONT = "Consolas"
BODY_FONT = "Microsoft YaHei"
BLUE = RGBColor(0x00, 0x66, 0xCC)
RED = RGBColor(0xCC, 0x33, 0x00)
GREEN = RGBColor(0x00, 0x80, 0x40)
GRAY = RGBColor(0x66, 0x66, 0x66)
DARK = RGBColor(0x22, 0x22, 0x22)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BG_DARK = RGBColor(0x1E, 0x1E, 0x2E)
BG_LIGHT = RGBColor(0xF0, 0xF0, 0xF5)

style = doc.styles["Normal"]
style.font.size = Pt(11)
style.font.name = BODY_FONT
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.line_spacing = 1.35


def add_title(text):
    p = doc.add_heading(text, level=0)
    for run in p.runs:
        run.font.size = Pt(22)
        run.font.color.rgb = DARK


def add_h1(text):
    p = doc.add_heading(text, level=1)
    for run in p.runs:
        run.font.size = Pt(17)
        run.font.color.rgb = RGBColor(0x00, 0x55, 0xAA)


def add_h2(text):
    p = doc.add_heading(text, level=2)
    for run in p.runs:
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0x33, 0x66, 0x99)


def add_para(text, bold=False, color=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.name = BODY_FONT
    run.bold = bold
    if color:
        run.font.color.rgb = color
    return p


def add_code_block(lines):
    """Add a code block with dark background and syntax-style coloring.
    lines: list of (text, color_or_None) tuples.
    """
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    # Add shading to the paragraph
    pPr = p._p.get_or_add_pPr()
    shd = pPr.makeelement(qn("w:shd"), {
        qn("w:fill"): "1E1E2E",
        qn("w:val"): "clear",
    })
    pPr.append(shd)

    for text, color in lines:
        run = p.add_run(text)
        run.font.name = CODE_FONT
        run.font.size = Pt(9.5)
        if color:
            run.font.color.rgb = color
        else:
            run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    return p


def add_annotation(text):
    """Add a green annotation line."""
    p = doc.add_paragraph()
    run = p.add_run(f"  → {text}")
    run.font.size = Pt(10)
    run.font.name = BODY_FONT
    run.font.color.rgb = GREEN
    run.italic = True
    return p


def add_note(text):
    """Add a blue info box-style note."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.left_indent = Cm(0.5)
    run = p.add_run(f"  💡 {text}")
    run.font.size = Pt(10)
    run.font.name = BODY_FONT
    run.font.color.rgb = BLUE
    return p


# ============================================================
# DOCUMENT CONTENT
# ============================================================

add_title("Twelve Data 服务层 — 逐行注释详解")
add_para("文件路径：backend/services/twelve_data_service.py", color=GRAY)
add_para("本文档对 twelve_data_service.py 的每一行代码进行注释，解释其语法含义、设计动机和在整个项目中的作用。", color=GRAY)

# ── Section 0: File Overview ──
add_h1("0. 文件概览")

add_para("这个文件是美股数据的主入口，封装了 Twelve Data API 的两个端点：")
add_para("• /quote — 实时行情（价格、涨跌、成交量）", bold=True)
add_para("• /time_series — 历史K线数据（开/高/低/收/量）", bold=True)
add_para("")
add_para("同时包含一个异步速率限制器（AsyncRateLimiter），确保不超过 Twelve Data 免费版的限额（每分钟 8 次请求）。")

add_note("为什么需要这个文件？ Twelve Data 免费版提供实时行情和 K 线历史，但每分钟限 8 次请求。这个文件封装了 API 调用 + 限速 + 缓存 + 错误降级，让上层 stock_service.py 可以无脑调用。")

# ── Section 1: Imports ──
add_h1("1. 导入依赖（第 1–10 行）")

add_code_block([
    ("import asyncio\n", BLUE),
    ("import time\n", BLUE),
    ("import logging\n", BLUE),
    ("\n", None),
    ("import httpx\n", BLUE),
    ("\n", None),
    ("from backend.config import TWELVE_DATA_API_KEY\n", BLUE),
    ("from backend.services.cache import yf_cache\n", BLUE),
    ("\n", None),
    ("logger = logging.getLogger(__name__)\n", BLUE),
])

add_annotation("asyncio — 提供异步锁 (asyncio.Lock) 和异步休眠 (asyncio.sleep)，是限速器的核心依赖")
add_annotation("time — 提供 time.monotonic()，单调时钟（不受系统时间调整影响），用于计算时间差")
add_annotation("logging — Python 标准日志库，用来记录警告和错误信息")
add_annotation("httpx — 异步 HTTP 客户端（类似 requests 但支持 async/await），用来发请求给 Twelve Data")
add_annotation("TWELVE_DATA_API_KEY — 从环境变量中读取的 API Key，在 config.py 中定义")
add_annotation("yf_cache — 从 cache.py 导入的 TTL 缓存实例（5 分钟过期），减少重复 API 调用")
add_annotation("logger = logging.getLogger(__name__) — 创建本模块专属的 logger，日志中会显示模块名 'backend.services.twelve_data_service'")

# ── Section 2: Constants ──
add_h1("2. 常量定义（第 12–17 行）")

add_code_block([
    ("TWELVE_DATA_BASE = ", BLUE),
    ('"https://api.twelvedata.com"\n', RGBColor(0xCE, 0x91, 0x78)),
    ("\n", None),
    ("_INTERVAL_MAP = {", BLUE),
    ('"1d": "1day", "1wk": "1week", "1mo": "1month"', RGBColor(0xCE, 0x91, 0x78)),
    ("}\n", BLUE),
    ("\n", None),
    ("_PERIOD_DAYS = {", BLUE),
    ('"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "max": 3650', RGBColor(0xCE, 0x91, 0x78)),
    ("}\n", BLUE),
    ("_INTERVAL_DAYS = {", BLUE),
    ('"1d": 1, "1wk": 7, "1mo": 30', RGBColor(0xCE, 0x91, 0x78)),
    ("}\n", BLUE),
])

add_annotation("TWELVE_DATA_BASE — API 根地址，下面所有请求都拼在这个 URL 后面")
add_annotation("_INTERVAL_MAP — 前端用简写 ('1d'/'1wk'/'1mo')，Twelve Data 需要完整名称 ('1day'/'1week'/'1month')，这个字典做翻译")
add_annotation("_PERIOD_DAYS — 时间范围 → 天数映射，用于计算该请求多少根 K 线")
add_annotation("_INTERVAL_DAYS — K 线周期 → 天数映射，用于计算所需数据量")

add_note("前缀下划线 _ 表示这些是模块私有常量，外部不应直接引用。")

# ── Section 3: AsyncRateLimiter ──
add_h1("3. AsyncRateLimiter 异步限速器（第 20–40 行）")

add_h2("3.1 __init__ 构造函数（第 23–27 行）")
add_code_block([
    ("class AsyncRateLimiter:\n", RGBColor(0xCE, 0x91, 0x78)),
    ('    """Async sliding-window rate limiter for Twelve Data (8 req / 60 s free tier)."""\n', RGBColor(0x6A, 0x99, 0x55)),
    ("\n", None),
    ("    def __init__(self, max_requests: int = 8, window_seconds: float = 60.0):\n", BLUE),
    ("        self._max = max_requests\n", BLUE),
    ("        self._window = window_seconds\n", BLUE),
    ("        self._timestamps: list[float] = []\n", BLUE),
    ("        self._lock = asyncio.Lock()\n", BLUE),
])

add_annotation("max_requests=8 — 默认每分钟最多 8 次请求（Twelve Data 免费版限制）")
add_annotation("window_seconds=60.0 — 滑动窗口 60 秒")
add_annotation("_timestamps — 列表，记录最近几次请求的时间戳（秒级浮点数）")
add_annotation("_lock = asyncio.Lock() — 异步互斥锁，保证并发场景下「检查+等待+记录」三步操作原子性")

add_note("为什么用 asyncio.Lock 而不是 threading.Lock？因为这个服务的调用方都是 async 函数，运行在同一个事件循环中。用线程锁会阻塞整个事件循环，用异步锁只阻塞当前协程。")

add_h2("3.2 acquire() 方法（第 29–40 行）")
add_code_block([
    ("    async def acquire(self):\n", BLUE),
    ("        async with self._lock:\n", BLUE),
    ("            now = time.monotonic()\n", BLUE),
    ("            self._timestamps = [t for t in self._timestamps if now - t < self._window]\n", BLUE),
    ("            if len(self._timestamps) >= self._max:\n", BLUE),
    ("                wait = self._timestamps[0] + self._window - now + 0.5\n", BLUE),
    ("                if wait > 0:\n", BLUE),
    ("                    logger.info(f\"Twelve Data rate limiter: waiting {wait:.1f}s\")\n", BLUE),
    ("                    await asyncio.sleep(wait)\n", BLUE),
    ("                    now = time.monotonic()\n", BLUE),
    ("                    self._timestamps = [t for t in self._timestamps if now - t < self._window]\n", BLUE),
    ("            self._timestamps.append(now)\n", BLUE),
])

add_annotation("第 30 行 async with self._lock — 获取异步锁，同一时刻只有一个协程能进入此代码块。这是整个限速器线程安全的核心")
add_annotation("第 31 行 now = time.monotonic() — 获取当前单调时间。monotonic() 不受系统时间手动调整影响（如 NTP 校时），比 time.time() 更适合做时间差计算")
add_annotation("第 32 行 — 列表推导式清理过期的时间戳。now - t < self._window 即 t 在 60 秒窗口内则保留，否则丢弃")
add_annotation("第 33-34 行 — 如果窗口内请求数已达上限，计算需要等多久。self._timestamps[0] 是最早的记录，加上窗口时间再减去当前时间 = 需要等待的秒数。+0.5 是额外安全余量")
add_annotation("第 36-38 行 — await asyncio.sleep(wait) 异步等待（不阻塞事件循环）。醒来后重新获取 now 并清理时间戳")
add_annotation("第 40 行 — 记录本次请求的时间戳")

add_note("滑动窗口算法的工作原理：想象一个 60 秒的横轴，每次请求在上面打一个点。acquire() 先把 60 秒外的点删掉，如果剩下的点 ≥ 8 个，就睡到最早那个点过期。")

# ── Section 4: Module-level limiter instance ──
add_h1("4. 模块级限速器实例（第 43 行）")
add_code_block([
    ("_twelve_data_limiter = AsyncRateLimiter()\n", BLUE),
])
add_annotation("模块加载时创建全局唯一的限速器实例。因为 Twelve Data 的 8次/分钟 限制是按 API Key 算的，整个应用共享一个限速器即可。")

# ── Section 5: _calc_outputsize ──
add_h1("5. _calc_outputsize 计算请求数据量（第 46–49 行）")
add_code_block([
    ("def _calc_outputsize(period: str, interval: str) -> int:\n", BLUE),
    ("    days = _PERIOD_DAYS.get(period, 90)\n", BLUE),
    ("    ival_days = _INTERVAL_DAYS.get(interval, 1)\n", BLUE),
    ("    return max(min(days // ival_days + 10, 5000), 30)\n", BLUE),
])
add_annotation("第 47 行 — 从 _PERIOD_DAYS 字典查时间范围对应天数，查不到默认 90 天")
add_annotation("第 48 行 — 从 _INTERVAL_DAYS 字典查 K 线周期间隔天数，查不到默认 1 天")
add_annotation("第 49 行 — days // ival_days + 10：时间跨度除以周期间隔 + 10 条余量。min(..., 5000) 上限 5000 条，max(..., 30) 下限 30 条。Twelve Data 免费版最多返回 5000 条")

# ── Section 6: get_twelve_data_quote ──
add_h1("6. get_twelve_data_quote 行情接口（第 52–97 行）")

add_h2("6.1 函数签名与 Key 检查（第 52–55 行）")
add_code_block([
    ("async def get_twelve_data_quote(symbol: str) -> dict | None:\n", BLUE),
    ('    """Get US stock quote from Twelve Data. Returns None on any failure (graceful degradation)."""\n', RGBColor(0x6A, 0x99, 0x55)),
    ("    if not TWELVE_DATA_API_KEY:\n", BLUE),
    ("        return None\n", BLUE),
])
add_annotation("async def — 异步函数声明，调用它返回一个协程对象")
add_annotation("symbol: str — 类型注解，参数是股票代码字符串")
add_annotation("-> dict | None — 返回类型注解，成功返回行情字典，失败返回 None（永不抛异常）")
add_annotation("if not TWELVE_DATA_API_KEY — 如果没配 API Key，直接返回 None。这是防御性编程，避免应用因配置缺失而崩溃")

add_note("返回 None 而非抛异常是本文件的核心理念——「优雅降级」(graceful degradation)。上层 stock_service.py 看到 None 就会自动 fallback 到 yfinance。")

add_h2("6.2 缓存查询（第 57–60 行）")
add_code_block([
    ("    cache_key = f\"quote:{symbol}\"\n", BLUE),
    ("    cached = yf_cache.get(cache_key)\n", BLUE),
    ("    if cached is not None:\n", BLUE),
    ("        return cached\n", BLUE),
])
add_annotation("cache_key — 字符串拼接生成缓存键，如 'quote:AAPL'")
add_annotation("yf_cache.get() — 查 TTL 缓存（5分钟过期），相同股票在 5 分钟内重复查询直接返回缓存，避免浪费 API 配额")
add_annotation("if cached is not None — 命中缓存则直接返回，跳过网络请求")

add_h2("6.3 限速 + 发起请求（第 62–70 行）")
add_code_block([
    ("    await _twelve_data_limiter.acquire()\n", BLUE),
    ("\n", None),
    ("    try:\n", BLUE),
    ("        async with httpx.AsyncClient(timeout=15.0) as client:\n", BLUE),
    ("            resp = await client.get(\n", BLUE),
    ('                f"{TWELVE_DATA_BASE}/quote",\n', BLUE),
    ('                params={"symbol": symbol, "apikey": TWELVE_DATA_API_KEY},\n', BLUE),
    ("            )\n", BLUE),
    ("            data = resp.json()\n", BLUE),
    ("    except Exception as e:\n", BLUE),
    ('        logger.warning(f"Twelve Data quote for {symbol} failed: {e}")\n', BLUE),
    ("        return None\n", BLUE),
])
add_annotation("第 62 行 — 调用限速器，如果 60 秒内已发 8 次请求，这里会 await asyncio.sleep() 等待")
add_annotation("第 65 行 async with httpx.AsyncClient — 创建异步 HTTP 客户端上下文管理器，退出时自动关闭连接。timeout=15.0 超时 15 秒")
add_annotation("第 66-68 行 — GET 请求 Twelve Data /quote 端点。params 参数会被拼成 URL 查询字符串：?symbol=AAPL&apikey=xxx")
add_annotation("第 69 行 resp.json() — 把响应体的 JSON 字符串解析为 Python 字典")
add_annotation("第 70-72 行 — 任何网络异常（超时、DNS 失败、连接拒绝）都被捕获，记录警告日志后返回 None。不会让上层崩溃")

add_h2("6.4 校验响应（第 75–83 行）")
add_code_block([
    ("    if not isinstance(data, dict):\n", BLUE),
    ("        return None\n", BLUE),
    ("    if data.get(\"status\") == \"error\" or \"code\" in data:\n", BLUE),
    ('        logger.warning(f"Twelve Data quote error for {symbol}: {data.get(\'message\', data)}")\n', BLUE),
    ("        return None\n", BLUE),
    ("\n", None),
    ('    close = data.get("close")\n', BLUE),
    ('    if close is None or close == "0":\n', BLUE),
    ("        return None\n", BLUE),
])
add_annotation("第 75-76 行 — 类型检查：如果返回的不是字典（可能是列表、字符串），直接放弃")
add_annotation("第 77-79 行 — Twelve Data 的错误响应格式：{\"status\": \"error\", \"message\": \"...\"} 或 {\"code\": 400, ...}。检测到这两种情况 → 记录日志 → 返回 None")
add_annotation("第 81-83 行 — 收盘价不存在或为 '0'（字符串！）说明该股票无有效数据，返回 None")

add_h2("6.5 字段提取与返回（第 85–97 行）")
add_code_block([
    ('    change = float(data.get("change", 0) or 0)\n', BLUE),
    ('    pct = data.get("percent_change")\n', BLUE),
    ('    change_pct = f"{float(pct):.2f}%" if pct else "0.00%"\n', BLUE),
    ("\n", None),
    ("    result = {\n", BLUE),
    ('        "symbol": symbol.upper(),\n', BLUE),
    ('        "price": round(float(close), 2),\n', BLUE),
    ('        "change": round(change, 3),\n', BLUE),
    ('        "change_percent": change_pct,\n', BLUE),
    ('        "volume": int(data.get("volume", 0)),\n', BLUE),
    ("    }\n", BLUE),
    ("    yf_cache.set(cache_key, result)\n", BLUE),
    ("    return result\n", BLUE),
])
add_annotation("第 85 行 float(data.get('change', 0) or 0) — data.get('change', 0) 取涨跌值，如果为 None 或不存在则用 0。or 0 处理 change 为空字符串 '' 的情况")
add_annotation("第 87 行 — Twelve Data 返回的 percent_change 是数字（如 1.35），格式化为 '+1.35%' 风格字符串")
add_annotation("第 90 行 symbol.upper() — 统一转大写，如 'aapl' → 'AAPL'")
add_annotation("第 91 行 round(float(close), 2) — 价格保留两位小数")
add_annotation("第 93 行 round(change, 3) — 涨跌金额保留三位小数（有些股票涨幅不到 1 分钱）")
add_annotation("第 94 行 int(data.get('volume', 0)) — 成交量转整数。免费版 Twelve Data 的 volume 常为 0，这就是 Bug 3 的根因")
add_annotation("第 96 行 yf_cache.set(cache_key, result) — 存入缓存，5 分钟内相同请求直接走缓存")

add_note("注意第 94 行：免费版 Twelve Data 的 /quote 端点经常不返回成交量（volume=0）。这个项目后来通过 stock_service.py 中的 _get_us_volume() 函数从 yfinance 补齐了成交量，形成了「字段级数据互补」。")

# ── Section 7: get_twelve_data_candles ──
add_h1("7. get_twelve_data_candles K线接口（第 100–156 行）")

add_h2("7.1 函数签名与 Key 检查（第 100–105 行）")
add_code_block([
    ("async def get_twelve_data_candles(\n", BLUE),
    ('    symbol: str, period: str = "3mo", interval: str = "1d"\n', BLUE),
    (") -> dict | None:\n", BLUE),
    ('    """Get US stock candles from Twelve Data. Returns None on any failure."""\n', RGBColor(0x6A, 0x99, 0x55)),
    ("    if not TWELVE_DATA_API_KEY:\n", BLUE),
    ("        return None\n", BLUE),
])
add_annotation("period='3mo' — 默认查询 3 个月的 K 线数据")
add_annotation("interval='1d' — 默认日线（每天一根 K 线）")

add_h2("7.2 缓存查询（第 107–110 行）")
add_code_block([
    ('    cache_key = f"candles:{symbol}:{period}:{interval}"\n', BLUE),
    ("    cached = yf_cache.get(cache_key)\n", BLUE),
    ("    if cached is not None:\n", BLUE),
    ("        return cached\n", BLUE),
])
add_annotation("缓存键包含三个维度：股票代码 + 时间范围 + K线周期。如 'candles:AAPL:3mo:1d'")

add_h2("7.3 参数转换 + 限速 + 请求（第 112–131 行）")
add_code_block([
    ('    td_interval = _INTERVAL_MAP.get(interval, "1day")\n', BLUE),
    ("    outputsize = _calc_outputsize(period, interval)\n", BLUE),
    ("\n", None),
    ("    await _twelve_data_limiter.acquire()\n", BLUE),
    ("\n", None),
    ("    try:\n", BLUE),
    ("        async with httpx.AsyncClient(timeout=15.0) as client:\n", BLUE),
    ("            resp = await client.get(\n", BLUE),
    ('                f"{TWELVE_DATA_BASE}/time_series",\n', BLUE),
    ("                params={\n", BLUE),
    ('                    "symbol": symbol,\n', BLUE),
    ('                    "interval": td_interval,\n', BLUE),
    ('                    "outputsize": outputsize,\n', BLUE),
    ('                    "apikey": TWELVE_DATA_API_KEY,\n', BLUE),
    ("                },\n", BLUE),
    ("            )\n", BLUE),
    ("            data = resp.json()\n", BLUE),
    ("    except Exception as e:\n", BLUE),
    ('        logger.warning(f"Twelve Data candles for {symbol} failed: {e}")\n', BLUE),
    ("        return None\n", BLUE),
])
add_annotation("第 112 行 — 把前端的简写 ('1d') 翻译成 Twelve Data 要求的全名 ('1day')。字典找不到则默认 '1day'")
add_annotation("第 113 行 — 计算该请求多少根 K 线。如 3mo 日线 = 90/1 + 10 = 100 根")
add_annotation("第 115 行 — 和 quote 接口共用同一个限速器（总配额 8次/分钟）")
add_annotation("第 120 行 — /time_series 是 Twelve Data 的 K 线端点，返回时间序列数据")

add_h2("7.4 校验响应（第 133–141 行）")
add_code_block([
    ("    if not isinstance(data, dict):\n", BLUE),
    ("        return None\n", BLUE),
    ('    if data.get("status") != "ok":\n', BLUE),
    ('        logger.warning(f"Twelve Data candles error for {symbol}: {data.get(\'message\', data)}")\n', BLUE),
    ("        return None\n", BLUE),
    ("\n", None),
    ('    values = data.get("values")\n', BLUE),
    ("    if not values or not isinstance(values, list):\n", BLUE),
    ("        return None\n", BLUE),
])
add_annotation("第 135 行 — K 线正常响应 status 为 'ok'，不是 'ok' 则视为失败")
add_annotation("第 139-141 行 — values 字段是 K 线数组，必须存在且为列表类型")

add_h2("7.5 数据翻转 + 构建返回（第 143–156 行）")
add_code_block([
    ("    candles = []\n", BLUE),
    ("    for v in reversed(values):  # Twelve Data returns newest first, reverse to chronological\n", BLUE),
    ("        candles.append({\n", BLUE),
    ('            "date": v["datetime"],\n', BLUE),
    ('            "open": round(float(v["open"]), 2),\n', BLUE),
    ('            "high": round(float(v["high"]), 2),\n', BLUE),
    ('            "low": round(float(v["low"]), 2),\n', BLUE),
    ('            "close": round(float(v["close"]), 2),\n', BLUE),
    ('            "volume": int(v["volume"]),\n', BLUE),
    ("        })\n", BLUE),
    ("\n", None),
    ('    result = {"symbol": symbol, "period": interval, "candles": candles}\n', BLUE),
    ("    yf_cache.set(cache_key, result)\n", BLUE),
    ("    return result\n", BLUE),
])
add_annotation("第 144 行 reversed(values) — 这是最关键的一行！Twelve Data 返回的 K 线是从新到旧（descending），但 Lightweight Charts 前端图表库要求从旧到新（ascending）。reversed() 做了这个翻转")
add_annotation("第 145-152 行 — 每根 K 线包含六个字段：日期、开盘价、最高价、最低价、收盘价、成交量。价格统一 round 到两位小数")
add_annotation("第 154 行 — 返回结构：symbol（代码）+ period（K线周期）+ candles（数组）。注意 period 传的是前端参数 interval（如 '1d'），不是请求时用的 '3mo'")
add_annotation("第 155 行 — 缓存 K 线结果（5 分钟 TTL），避免频繁请求触发限速")
add_annotation("第 156 行 — 返回结果给 candle_service.py，由它决定是否还需要 fallback 到 yfinance")

add_note("为什么用 reversed()？ Twelve Data 的 API 设计是默认返回最新的在前（方便看最新数据），但前端图表库画图需要时间从前往后排。如果不翻转，K 线图会从右往左画，视觉效果是反的。")

# ── Section 8: Summary ──
add_h1("8. 设计模式总结")

add_para("这个 157 行的文件体现了以下设计模式：")

# Use bullet points
p = doc.add_paragraph(style="List Bullet")
run = p.add_run("优雅降级 (Graceful Degradation)")
run.bold = True
p.add_run("：任何失败都返回 None，不抛异常，让上层决定是否 fallback。这是多级数据源架构的基石。")

p = doc.add_paragraph(style="List Bullet")
run = p.add_run("滑动窗口限速 (Sliding Window Rate Limiting)")
run.bold = True
p.add_run("：用时间戳列表 + 异步锁实现的轻量级限速器，无外部依赖，适配 Twelve Data 免费版 8次/分钟限制。")

p = doc.add_paragraph(style="List Bullet")
run = p.add_run("TTL 缓存 (Time-To-Live Cache)")
run.bold = True
p.add_run("：5 分钟过期的内存缓存，减少重复请求。相同股票在缓存期内直接返回，不消耗 API 配额。")

p = doc.add_paragraph(style="List Bullet")
run = p.add_run("类型注解 + 防御性校验")
run.bold = True
p.add_run("：dict | None 返回类型让 IDE 和调用方明确知道可能返回 None；多层 isinstance 检查防止 API 异常响应格式导致崩溃。")

p = doc.add_paragraph(style="List Bullet")
run = p.add_run("数据格式适配 (Adapter Pattern)")
run.bold = True
p.add_run("：reversed() 翻转 K 线顺序、_INTERVAL_MAP 翻译简写、round() 统一小数位数——将外部 API 格式适配为项目内部统一格式。")

p = doc.add_paragraph(style="List Bullet")
run = p.add_run("延迟初始化 + 模块级单例")
run.bold = True
p.add_run("：_twelve_data_limiter 在模块加载时创建，全局共享。只在 acquire() 时才检查限速，无额外开销。")

add_para("")
add_para("— 全文完 —", color=GRAY)
add_para(f"文件位置：{OUTPUT}", color=GRAY)

doc.save(OUTPUT)
print(f"Done! Saved to: {OUTPUT}")
