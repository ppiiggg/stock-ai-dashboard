from fastapi import APIRouter, HTTPException
from backend.services.llm_service import analyze_stock
from backend.services.supabase_service import get_recent_analyses, save_analysis
from backend.models.schemas import StockData, AIAnalysisResult
from datetime import datetime, timezone

router = APIRouter()


@router.post("/analyze", response_model=AIAnalysisResult)
async def analyze(request: StockData):
    try:
        analysis = await analyze_stock(request.model_dump())

        record = {
            "symbol": request.symbol,
            "price": request.price,
            "change_percent": request.change_percent,
            "market": request.market,
            "summary": analysis["summary"],
            "sentiment": analysis["sentiment"],
            "risk_level": analysis["risk_level"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        save_analysis(record)

        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history():
    try:
        return get_recent_analyses(5)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
