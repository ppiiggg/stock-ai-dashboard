from pydantic import BaseModel
from typing import Literal, Optional


class StockRequest(BaseModel):
    symbol: str


class StockData(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: str
    volume: int = 0
    market: Optional[str] = None
    candles: Optional[list] = None


class AIAnalysisResult(BaseModel):
    summary: str
    sentiment: Literal["Bullish", "Neutral", "Bearish"]
    risk_level: str
