# AI 股票分析面板 (Stock AI Dashboard)

## 在线访问

| 用途 | URL |
|------|-----|
| 主应用 | https://stock-ai-dashboard-c3vm.onrender.com/ |
| 面试交付文档（Prompt 代码 + Debug 记录 + 技术栈） | https://stock-ai-dashboard-c3vm.onrender.com/interview.html |

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | HTML5 + CSS3 + Vanilla JavaScript |
| 后端 | Python FastAPI |
| 股票数据 | Finnhub API (免费) |
| AI 分析 | DeepSeek Chat |
| 数据库 | Supabase (PostgreSQL) |
| 部署 | Render.com |

## 功能

1. 输入股票代码（如 AAPL, TSLA），获取实时行情数据
2. 调用 LLM 对股票数据进行 AI 分析
3. 分析结果自动存入 Supabase 数据库
4. 展示历史分析记录

## 本地运行

```bash
git clone [填写你的 GitHub URL]
cd stock-ai-dashboard
pip install -r backend/requirements.txt
cp .env.example .env
# 编辑 .env 填入 API Keys
uvicorn backend.main:app --reload --port 8000
# 用浏览器打开 frontend/index.html
```

## Prompt 代码

### System Prompt（强制 JSON 输出）

```python
SYSTEM_PROMPT = '''你是一个专业的股票分析师。用户会提供股票的实时行情数据（价格、涨跌幅、成交量）。

请严格按以下 JSON 格式返回分析结果，不要包含任何其他文字、解释或 Markdown 标记：

{
  "summary": "用1-2句中文总结该股票当前的技术面表现和短期走势判断（50字以内）",
  "sentiment": "Bullish 或 Neutral 或 Bearish",
  "risk_level": "Low Risk 或 Medium Risk 或 High Risk"
}

规则：
- sentiment 只能是 Bullish、Neutral、Bearish 之一
- risk_level 只能是 Low Risk、Medium Risk、High Risk 之一
- 只返回 JSON 对象，不要用代码块包裹，不要有任何前缀或后缀文字
- 所有字段都必须有值，不能为空字符串'''
```

### 容错机制（4 层防护 + 可观测日志）

1. 直接 JSON 解析 — `json.loads(content)` 尝试直接解析
2. 正则提取 `re.search(r'\{.*\}', content, re.DOTALL)` — 暴力提取，应对 LLM 加前缀文字
3. 重试机制 — 失败自动重试最多 2 次（共 3 次机会）
4. 降级 JSON — 最终兜底，返回 "AI 分析暂时不可用"，避免前端崩溃
5. 每层均有 `print()` 日志输出到控制台，方便观察解析链路

> 注：生产环境建议开启 `response_format={"type": "json_object"}` + `temperature=0.3` 以提高 JSON 稳定性，减少进入降级层的概率。

## Debug 记录

### Bug: LLM 返回非 JSON 内容（前缀文字）

**现象：**
取消 `response_format={"type": "json_object"}` 并将 `temperature` 提高到 0.9 后，DeepSeek 偶尔会在 JSON 前加前缀文字，例如：
```
好的，以下是分析结果：\n\n{"summary": "...", "sentiment": "Neutral", "risk_level": "Medium Risk"}
```
前端仍正常展示分析结果，Bug 被容错机制静默消化，服务端无任何告警。

**排查过程：**
1. 确认 `response_format` 已注释、`temperature=0.9`（当前代码默认即此状态）
2. 多次调用 `/api/analyze`，前端始终正常——因为 Layer 2 正则 `re.search(r'\{.*\}', content)` 成功从文字中提取 JSON
3. 发现缺少日志，无法判断哪一层解析生效 → 在 `llm_service.py` 每层加 `print()` 日志
4. 加上日志后观察服务端控制台：当 LLM 返回纯 JSON 时走 Layer 1，带前缀时走 Layer 2
5. 结论：容错机制有效，但缺少可观测性

**修复方案：**
在 `llm_service.py` 的每层解析和重试逻辑中加入 `print()` 日志：

```python
print(f"\n[LLM] ===== 原始响应 (前300字符) =====\n{content[:300]}\n")
# Layer 1
print("[LLM] ✓ Layer 1 成功: 直接 JSON 解析")
# Layer 2
print("[LLM] ✓ Layer 2 成功: 正则提取 JSON")
# 重试
print(f"[LLM] → 重试第 {retry + 1} 次...")
# 降级
print("[LLM] → 3 次尝试均失败，使用降级 JSON")
```

**经验教训：**
容错逻辑本身是正确的，但没有日志就无法验证它在工作——给每层加 `print()` 即可在控制台观察完整的解析链路。

### Bug: 中国股票代码（6位数字）无法查询

**现象：**
输入 `000300`（沪深300）或 `000001`（平安银行），后端返回 404："无法获取 000300 的行情数据，请检查股票代码"。

**排查过程：**
1. Finnhub 要求中国股票带交易所后缀：上证 `.SS`（如 `600036.SS`）、深证 `.SZ`（如 `000001.SZ`）
2. 当前 `stock_service.py` 仅做 `.upper()` 转换，未追加后缀
3. 纯数字 6 位代码被原样发给 Finnhub → `000300` 无法匹配任何标的

**修复方案：**
新增 `resolve_symbol()` 函数，6 位纯数字自动加后缀：

```python
def resolve_symbol(raw: str) -> str:
    s = raw.strip().upper()
    if s.isdigit() and len(s) == 6:
        if s[0] in ("0", "3"):
            return f"{s}.SZ"   # 深圳
        if s[0] == "6":
            return f"{s}.SS"   # 上海
    return s  # 美股代码原样返回
```

**经验教训：**
中国股市有两个交易所（上海/深圳），代码格式相同但需要不同后缀，前端应提示用户输入完整代码或自动补全。

## 项目结构

```
stock-ai-dashboard/
  backend/
    main.py
    config.py
    routers/
      stock.py
      analysis.py
    services/
      stock_service.py
      llm_service.py
      supabase_service.py
    models/
      schemas.py
  frontend/
    index.html
    style.css
    app.js
  README.md
```

## 环境变量

| 变量名 | 说明 |
|--------|------|
| FINNHUB_API_KEY | Finnhub 免费 API Key |
| DEEPSEEK_API_KEY | DeepSeek API Key |
| SUPABASE_URL | Supabase 项目 URL |
| SUPABASE_KEY | Supabase anon/public key |
