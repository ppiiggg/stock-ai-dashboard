import json
import re
from openai import AsyncOpenAI
from backend.config import DEEPSEEK_API_KEY

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY environment variable is not set")
        _client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
    return _client

SYSTEM_PROMPT = '''你是一个专业的股票分析师。用户会提供股票的实时行情数据（价格、涨跌幅、成交量），可能还会附带 K 线历史数据的技术指标摘要。

请严格按以下 JSON 格式返回分析结果，不要包含任何其他文字、解释或 Markdown 标记：

{
  "summary": "用1-5句中文总结该股票当前的技术面表现和短期走势判断（200字以内）",
  "sentiment": "Bullish 或 Neutral 或 Bearish",
  "risk_level": "Low Risk 或 Medium Risk 或 High Risk"
}

规则：
- sentiment 只能是 Bullish、Neutral、Bearish 之一
- risk_level 只能是 Low Risk、Medium Risk、High Risk 之一
- 只返回 JSON 对象，不要用代码块包裹，不要有任何前缀或后缀文字
- 所有字段都必须有值，不能为空字符串
- 如果提供了 K 线技术指标，请在 summary 中结合均线、近期趋势、支撑压力位等信息进行综合判断'''


def _build_candle_summary(candles: list) -> str:
    """从 K 线数据中提取关键技术指标，生成简洁文本摘要。"""
    if not candles or len(candles) < 2:
        return ""

    closes = [c.get("close", 0) for c in candles]
    highs = [c.get("high", 0) for c in candles]
    lows = [c.get("low", 0) for c in candles]
    volumes = [c.get("volume", 0) for c in candles]
    dates = [c.get("date", "") for c in candles]

    period_high = max(highs)
    period_low = min(lows)
    latest_close = closes[-1]
    first_close = closes[0]
    total_change_pct = ((latest_close - first_close) / first_close * 100) if first_close else 0

    # 均线
    def ma(data, n):
        if len(data) < n:
            return None
        return sum(data[-n:]) / n

    ma5 = ma(closes, 5)
    ma10 = ma(closes, 10)
    ma20 = ma(closes, 20)

    # 近期趋势
    recent_5 = closes[-5:] if len(closes) >= 5 else closes
    trend_5 = "上涨" if recent_5[-1] > recent_5[0] else "下跌"

    # 成交量趋势
    if len(volumes) >= 10:
        recent_vol_avg = sum(volumes[-5:]) / 5
        prev_vol_avg = sum(volumes[-10:-5]) / 5
        vol_trend = "放量" if recent_vol_avg > prev_vol_avg * 1.2 else ("缩量" if recent_vol_avg < prev_vol_avg * 0.8 else "持平")
    else:
        vol_trend = "数据不足"

    # 当前价格在区间中的位置
    price_range = period_high - period_low
    position_pct = ((latest_close - period_low) / price_range * 100) if price_range > 0 else 50

    lines = [
        f"K线技术指标摘要（{dates[0]} 至 {dates[-1]}，共 {len(candles)} 根K线）：",
        f"- 区间最高价: {period_high:.2f}，区间最低价: {period_low:.2f}",
        f"- 期间涨跌幅: {total_change_pct:+.2f}%",
        f"- 最新收盘价: {latest_close:.2f}（处于区间 {position_pct:.0f}% 分位）",
        f"- 近5日趋势: {trend_5}",
    ]
    if ma5 is not None:
        lines.append(f"- MA5: {ma5:.2f}（{'高于' if latest_close > ma5 else '低于'} 现价）")
    if ma10 is not None:
        lines.append(f"- MA10: {ma10:.2f}（{'高于' if latest_close > ma10 else '低于'} 现价）")
    if ma20 is not None:
        lines.append(f"- MA20: {ma20:.2f}（{'高于' if latest_close > ma20 else '低于'} 现价）")
    lines.append(f"- 近期成交量: {vol_trend}")

    return "\n".join(lines)


async def analyze_stock(stock_data: dict, retry: int = 0) -> dict:
    currency = "¥" if stock_data.get("market") == "china" else "$"
    parts = [
        f"请分析以下股票数据并以 JSON 格式返回：",
        f"- 股票代码: {stock_data.get('symbol')}",
        f"- 当前价格: {currency}{stock_data.get('price')}",
        f"- 涨跌: {stock_data.get('change')} ({stock_data.get('change_percent')})",
        f"- 成交量: {stock_data.get('volume')}",
    ]

    candles = stock_data.get('candles')
    if candles:
        candle_text = _build_candle_summary(candles)
        if candle_text:
            parts.append("")
            parts.append(candle_text)

    parts.append("")
    parts.append("Return JSON only, no other text.")
    user_message = "\n".join(parts)

    try:
        response = await _get_client().chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        
        content = response.choices[0].message.content.strip()
        print(f"\n[LLM] ===== 原始响应 (前300字符) =====\n{content[:300]}\n")

        # Layer 1: 直接解析
        try:
            result = json.loads(content)
            print("[LLM] [OK] Layer 1 成功: 直接 JSON 解析")
            return _validate_and_return(result)
        except json.JSONDecodeError:
            print("[LLM] [FAIL] Layer 1 失败: 非纯 JSON，尝试正则提取")

        # Layer 2: 正则提取 JSON 对象
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            result = json.loads(match.group())
            print("[LLM] [OK] Layer 2 成功: 正则提取 JSON")
            return _validate_and_return(result)

        print("[LLM] [FAIL] Layer 2 失败: 正则也未找到 JSON")
        raise ValueError(f"无法从响应中解析 JSON: {content[:200]}")

    except Exception as e:
        print(f"[LLM] Exception (retry={retry}): {e}")
        if retry < 2:
            print(f"[LLM] Retry #{retry + 1}...")
            return await analyze_stock(stock_data, retry + 1)

        print("[LLM] 3 attempts failed, using fallback JSON")
        # Layer 5: 最终降级
        return {
            "summary": f"{stock_data.get('symbol')} 当前价格 {currency}{stock_data.get('price')}，AI 分析暂时不可用。",
            "sentiment": "Neutral",
            "risk_level": "Medium Risk",
        }


def _validate_and_return(data: dict) -> dict:
    valid_sentiments = {"Bullish", "Neutral", "Bearish"}
    valid_risks = {"Low Risk", "Medium Risk", "High Risk"}

    sentiment = data.get("sentiment", "Neutral")
    if sentiment not in valid_sentiments:
        sentiment = "Neutral"

    risk = data.get("risk_level", "Medium Risk")
    if risk not in valid_risks:
        risk = "Medium Risk"

    return {
        "summary": data.get("summary", "暂无分析")[:200],
        "sentiment": sentiment,
        "risk_level": risk,
    }
