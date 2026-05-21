import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="Stock AI Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.routers import stock, analysis, candles

app.include_router(stock.router, prefix="/api", tags=["Stock"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(candles.router, prefix="/api", tags=["Candles"])

@app.get("/api/health")
def root():
    return {"message": "Stock AI Dashboard API is running"}


# Serve tutorial documentation (must mount before "/" or static root will swallow it)
import os
from fastapi.staticfiles import StaticFiles

tutorial_dir = os.path.join(os.path.dirname(__file__), "..", "tutorial")
if os.path.isdir(tutorial_dir):
    app.mount("/tutorial", StaticFiles(directory=tutorial_dir, html=True), name="tutorial")

# Serve frontend static files (production: same-origin, no CORS needed)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
