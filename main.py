import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path


load_dotenv()

Path("uploads").mkdir(parents=True, exist_ok=True)

# ── CREATE FASTAPI APP ───────────────────────────────────────
app = FastAPI(
    title="MedAssist API",
    description="AI-powered medical assistant with multimodal input support",
    version="1.0.0",
)

# ── CORS MIDDLEWARE ──────────────────────────────────────────
# CORS allows your React frontend (running on localhost:3000)
# to talk to your FastAPI backend (running on localhost:8000)
# without the browser blocking the request
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── IMPORT ROUTERS ───────────────────────────────────────────
# we will add these as we build each route file
from api.routes import router
app.include_router(router, prefix="/api")

# ── ROOT ENDPOINT ────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "message": "MedAssist API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

# ── RUN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug   # reload=True only in dev, False in production
    )