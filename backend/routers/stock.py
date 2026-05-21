from fastapi import APIRouter, HTTPException
from backend.services.stock_service import get_stock_quote

router = APIRouter()


@router.get("/stock/{symbol}")
async def get_stock(symbol: str):
    try:
        data = await get_stock_quote(symbol)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
