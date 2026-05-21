// ===== 配置 =====
const hostname = window.location.hostname;
const API_BASE = (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '')
    ? 'http://localhost:8000'
    : window.location.origin;

// ===== DOM 引用 =====
const stockInput    = document.getElementById('stockInput');
const analyzeBtn    = document.getElementById('analyzeBtn');
const stockCard     = document.getElementById('stockCard');
const chartCard     = document.getElementById('chartCard');
const chartContainer = document.getElementById('chartContainer');
const analysisCard  = document.getElementById('analysisCard');
const historyList   = document.getElementById('historyList');
const debugCard     = document.getElementById('debugCard');
const debugContent  = document.getElementById('debugContent');
const showDebugBtn  = document.getElementById('showDebugBtn');
const toggleDebug   = document.getElementById('toggleDebug');

// ===== 图表实例 =====
let chart = null;
let candleSeries = null;

// ===== Debug 存储 =====
let debugLogs = [];

function addDebugLog(label, data, isError) {
    const entry = { label, data, isError, time: new Date().toLocaleTimeString() };
    debugLogs.push(entry);
    console.log(`[Debug] ${label}:`, data);
    renderDebug();
}

function renderDebug() {
    debugContent.innerHTML = debugLogs.map(e => `
        <div class="debug-section ${e.isError ? 'error' : 'success'}">
            <div class="debug-label">${e.time} — ${e.label}</div>
            <div class="debug-json">${JSON.stringify(e.data, null, 2)}</div>
        </div>
    `).join('');
}

// Toggle debug panel
showDebugBtn.addEventListener('click', function () {
    if (debugCard.style.display === 'none') {
        debugCard.style.display = 'block';
        showDebugBtn.textContent = '隐藏 API 返回数据';
    } else {
        debugCard.style.display = 'none';
        showDebugBtn.textContent = '查看 API 返回数据';
    }
});

toggleDebug.addEventListener('click', function () {
    debugCard.style.display = 'none';
    showDebugBtn.textContent = '查看 API 返回数据';
});

// ===== 核心流程 =====
async function analyzeStock() {
    // 防止重复点击
    if (analyzeBtn.disabled) return;

    const symbol = stockInput.value.trim().toUpperCase();
    if (!symbol) {
        alert('请输入股票代码');
        return;
    }

    debugLogs = [];
    setLoading(true);

    try {
        // 1. 获取行情数据
        const stockData = await fetchStock(symbol);
        addDebugLog('股票行情 API (/api/stock)', stockData, false);
        renderStockCard(stockData);

        // 2. 获取K线数据并绘图
        let candleData = null;
        try {
            candleData = await fetchCandles(symbol);
            addDebugLog('K线数据 API (/api/candles)', { symbol: candleData.symbol, count: candleData.candles.length }, false);
            renderChart(candleData);
        } catch (err) {
            console.warn('K线数据获取失败:', err.message);
            addDebugLog('K线数据 API (/api/candles)', { error: err.message }, true);
            chartCard.style.display = 'none';
        }

        // 3. 获取 AI 分析（K线数据成功时一并传入）
        const analysis = await fetchAnalysis(stockData, candleData);
        addDebugLog('AI 分析 API (/api/analyze)', analysis, false);
        renderAnalysisCard(analysis);

        // 4. 刷新历史记录
        await loadHistory();

    } catch (err) {
        console.error(err);
        addDebugLog('请求失败', { error: err.message }, true);
        alert('错误: ' + err.message);
    } finally {
        setLoading(false);
    }
}

// ===== API 调用 =====
async function fetchStock(symbol) {
    const url = `${API_BASE}/api/stock/${symbol}`;
    console.log(`[API] GET ${url}`);
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.detail || '获取行情失败，请检查股票代码');
    }
    return data;
}

async function fetchCandles(symbol) {
    const url = `${API_BASE}/api/candles/${symbol}?period=3mo&interval=1d`;
    console.log(`[API] GET ${url}`);
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.detail || '获取K线数据失败');
    }
    return data;
}

async function fetchAnalysis(stockData, candleData) {
    const url = `${API_BASE}/api/analyze`;
    const body = { ...stockData };
    if (candleData && candleData.candles) {
        body.candles = candleData.candles;
    }
    console.log(`[API] POST ${url}`, body);
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.detail || 'AI 分析失败，请稍后重试');
    }
    return data;
}

// ===== 按钮状态 =====
function setLoading(loading) {
    analyzeBtn.disabled = loading;
    if (loading) {
        analyzeBtn.innerHTML = '<span class="loading-spinner"></span>分析中...';
    } else {
        analyzeBtn.textContent = '分析';
    }
}

// ===== 渲染函数 =====

// 行情卡片
function renderStockCard(data) {
    document.getElementById('stockSymbol').textContent = data.symbol;
    const currency = data.market === 'china' ? '¥' : '$';
    document.getElementById('stockPrice').textContent =
        currency + Number(data.price).toFixed(2);

    // 涨跌 & 颜色
    const changeEl = document.getElementById('stockChange');
    const change = data.change;
    const changePct = data.change_percent;
    const sign = change >= 0 ? '+' : '';
    changeEl.textContent = `涨跌 ${sign}${Number(change).toFixed(2)} (${changePct})`;
    changeEl.className = change > 0 ? 'change-up'
                       : change < 0 ? 'change-down'
                       : 'change-zero';

    // 成交量
    document.getElementById('stockVolume').textContent =
        '成交量 ' + Number(data.volume).toLocaleString() + ' 手';

    stockCard.style.display = 'block';
}

// K线图
function renderChart(data) {
    // 销毁旧图表
    if (chart) {
        chart.remove();
        chart = null;
        candleSeries = null;
    }

    // 先显示容器，否则 LightweightCharts 会在 0x0 的不可见容器上初始化，导致图表无法渲染
    chartCard.style.display = 'block';

    const candles = data.candles.map(c => ({
        time: c.date,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
    }));

    chart = LightweightCharts.createChart(chartContainer, {
        layout: {
            background: { color: '#16213e' },
            textColor: '#888',
        },
        grid: {
            vertLines: { color: 'rgba(255,255,255,0.06)' },
            horzLines: { color: 'rgba(255,255,255,0.06)' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        timeScale: {
            borderColor: 'rgba(255,255,255,0.1)',
            timeVisible: true,
        },
        rightPriceScale: {
            borderColor: 'rgba(255,255,255,0.1)',
        },
    });

    candleSeries = chart.addCandlestickSeries({
        upColor: '#f56565',
        downColor: '#48bb78',
        borderUpColor: '#f56565',
        borderDownColor: '#48bb78',
        wickUpColor: '#f56565',
        wickDownColor: '#48bb78',
    });

    candleSeries.setData(candles);
    chart.timeScale().fitContent();
}

// AI 分析卡片
function renderAnalysisCard(data) {
    // 情绪标签（彩色圆点 + 文字）
    const sentimentEl = document.getElementById('sentimentTag');
    const sentiment = data.sentiment;
    sentimentEl.textContent = sentiment;
    const sentimentMap = {
        'Bullish': 'tag-bullish',
        'Neutral': 'tag-neutral',
        'Bearish': 'tag-bearish',
    };
    sentimentEl.className = 'tag ' + (sentimentMap[sentiment] || 'tag-neutral');

    // 风险等级标签
    const riskEl = document.getElementById('riskTag');
    const risk = data.risk_level;
    riskEl.textContent = risk;
    const riskMap = {
        'Low Risk':    'tag-risk-low',
        'Medium Risk': 'tag-risk-mid',
        'High Risk':   'tag-risk-high',
    };
    riskEl.className = 'tag ' + (riskMap[risk] || 'tag-risk-mid');

    // 分析总结
    document.getElementById('aiSummary').textContent = data.summary;

    analysisCard.style.display = 'block';
}

// 历史记录（最近5条）
async function loadHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/history`);
        if (!res.ok) return;

        const list = await res.json();
        const recent = list.slice(0, 5);

        if (!recent.length) {
            historyList.innerHTML = '<p class="empty-hint">暂无记录</p>';
            return;
        }

        const senColor = {
            'Bullish': '#f59e0b',
            'Neutral': '#9ca3af',
            'Bearish': '#3b82f6',
        };

        historyList.innerHTML = recent.map(item => `
            <div class="history-item">
                <span class="history-symbol">${item.symbol}</span>
                <span class="history-sentiment" style="color:${senColor[item.sentiment] || '#888'};">
                    ${item.sentiment}
                </span>
                <span style="color:#888;font-size:12px;">
                    ${item.market === 'china' ? '¥' : '$'}${Number(item.price).toFixed(2)}
                </span>
                <span style="color:#666;font-size:12px;">
                    ${new Date(item.created_at).toLocaleDateString('zh-CN')}
                </span>
            </div>
        `).join('');

    } catch (err) {
        console.error('加载历史记录失败:', err);
    }
}

// ===== 事件绑定 =====

// 回车键触发分析
stockInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        analyzeStock();
    }
});

// 输入自动转大写（仅对字母生效，不影响数字和中文输入）
stockInput.addEventListener('input', function () {
    const cursor = this.selectionStart;
    const oldVal = this.value;
    const newVal = oldVal.toUpperCase();
    if (newVal !== oldVal) {
        this.value = newVal;
        this.setSelectionRange(cursor, cursor);
    }
});

// 按钮点击
analyzeBtn.addEventListener('click', analyzeStock);

// ===== 页面初始化 =====
loadHistory();
