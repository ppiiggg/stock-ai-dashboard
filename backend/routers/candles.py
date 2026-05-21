from fastapi import APIRouter, HTTPException, Query
from backend.services.candle_service import get_candles

router = APIRouter()


@router.get("/candles/{symbol}")
async def get_kline(
    symbol: str,
    period: str = Query("3mo", description="时间范围: 1mo, 3mo, 6mo, 1y, 2y, max"),
    interval: str = Query("1d", description="K线周期: 1d, 1wk, 1mo (仅美股支持非日线)"),
):
    try:
        return await get_candles(symbol, period=period, interval=interval)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
