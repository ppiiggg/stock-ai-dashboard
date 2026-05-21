import httpx
import re


async def get_china_stock_quote(symbol: str) -> dict:
    """从新浪财经获取中国A股实时行情（免费，无需API Key）。

    上海: 600036 → sh600036
    深圳: 000001 → sz000001
    """
    code = _resolve_sina_code(symbol)

    url = f"https://hq.sinajs.cn/list={code}"
    headers = {"Referer": "https://finance.sina.com.cn"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        resp.encoding = "gb2312"
        text = resp.text

    if not text or "FAILED" in text or text.strip() == '""':
        raise ValueError(f"无法获取 {symbol} 的行情数据（新浪数据源返回空，请检查股票代码）")

    # 解析新浪返回格式:
    # var hq_str_sh600036="招商银行,43.50,43.00,43.80,44.00,42.90,43.80,43.81,1234567,0,..."
    match = re.search(r'"([^"]*)"', text)
    if not match:
        raise ValueError(f"无法解析 {symbol} 的行情数据")

    fields = match.group(1).split(",")
    if len(fields) < 10:
        raise ValueError(f"{symbol} 行情数据不完整（字段不足）")

    name = fields[0]
    open_price = float(fields[1]) if fields[1] else 0
    prev_close = float(fields[2]) if fields[2] else 0
    current = float(fields[3]) if fields[3] else 0
    volume = int(fields[8]) if fields[8] else 0  # 手

    if current == 0:
        raise ValueError(f"{symbol} ({name}) 当前未交易或数据不可用")

    change = round(current - prev_close, 3)
    change_percent = f"{(change / prev_close * 100):.2f}%" if prev_close else "0.00%"

    return {
        "symbol": f"{symbol} ({name})",
        "price": current,
        "change": change,
        "change_percent": change_percent,
        "volume": volume,
    }


def _resolve_sina_code(raw: str) -> str:
    """将6位数字代码转为新浪格式: sh600036 或 sz000001"""
    s = raw.strip().upper()
    if s[0] in ("0", "3"):
        return f"sz{s}"
    if s[0] == "6":
        return f"sh{s}"
    return s
