import os
import shutil
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

from perception.agent import PerceptionAgent
from correlation.agent import CorrelationAgent
from memory.agent import MemoryAgent

app = FastAPI(
    title="TACET DISCORD API",
    description="Shift-Handoff Copilot Backend for Factory Anomaly & Predictive Maintenance",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = os.path.dirname(__file__)
static_dir = os.path.join(base_dir, "static")
uploads_dir = os.path.join(base_dir, "data", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "heatmaps"), exist_ok=True)

# Instantiate Agents
perception_agent = PerceptionAgent(static_dir=static_dir)
correlation_agent = CorrelationAgent()
memory_agent = MemoryAgent()

class CorrelateRequest(BaseModel):
    telemetry_mode: Optional[str] = "normal"
    perception_score: Optional[float] = None

class RememberRequest(BaseModel):
    image_path: str
    confirmed_diagnosis: str
    fix_steps: str
    heatmap_path: Optional[str] = None
    voice_note_path: Optional[str] = None
    confidence_at_capture: Optional[float] = 0.85

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "system": "TACET DISCORD Multi-Agent Framework",
        "agents": ["perception", "correlation", "memory", "verifier", "coordinator"]
    }

@app.post("/perceive")
async def perceive(file: Optional[UploadFile] = File(None), image_path: Optional[str] = Form(None)):
    """Perception Agent Endpoint"""
    target_path = None
    if file:
        file_ext = os.path.splitext(file.filename)[1] or ".png"
        filename = f"upload_{uuid.uuid4().hex[:8]}{file_ext}"
        target_path = os.path.join(uploads_dir, filename)
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    elif image_path:
        target_path = image_path
    else:
        target_path = os.path.join(base_dir, "data", "mvtec", "bottle", "test", "broken_large", "000.png")

    if not os.path.exists(target_path):
        raise HTTPException(status_code=400, detail=f"Image file not found at {target_path}")

    try:
        result = perception_agent.perceive(target_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Perception agent analysis failed: {str(e)}")

@app.post("/correlate")
async def correlate(req: CorrelateRequest):
    """Correlation Agent Endpoint"""
    try:
        result = correlation_agent.correlate(
            telemetry_mode=req.telemetry_mode,
            perception_score=req.perception_score
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Correlation agent analysis failed: {str(e)}")

@app.post("/recall")
async def recall(file: Optional[UploadFile] = File(None), image_path: Optional[str] = Form(None)):
    """
    Memory Agent Recall Endpoint:
    Accepts image file upload or image_path.
    Returns single best match (all fields) and cosine similarity strength score.
    Returns match: null if similarity < 0.30.
    """
    target_path = None
    if file:
        file_ext = os.path.splitext(file.filename)[1] or ".png"
        filename = f"recall_{uuid.uuid4().hex[:8]}{file_ext}"
        target_path = os.path.join(uploads_dir, filename)
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    elif image_path:
        target_path = image_path
    else:
        target_path = os.path.join(base_dir, "data", "mvtec", "bottle", "test", "broken_large", "000.png")

    if not os.path.exists(target_path):
        raise HTTPException(status_code=400, detail=f"Image file not found at {target_path}")

    try:
        result = memory_agent.recall(target_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory agent recall failed: {str(e)}")

@app.post("/remember")
async def remember(req: RememberRequest):
    """
    Memory Agent Remember Endpoint:
    Accepts a new senior-confirmed incident and inserts it into SQLite store with seeded: False.
    """
    try:
        result = memory_agent.remember(
            image_path=req.image_path,
            confirmed_diagnosis=req.confirmed_diagnosis,
            fix_steps=req.fix_steps,
            heatmap_path=req.heatmap_path,
            voice_note_path=req.voice_note_path,
            confidence_at_capture=req.confidence_at_capture or 0.85
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory agent remember failed: {str(e)}")

@app.post("/verify")
async def verify(payload: Dict[str, Any] = {}):
    return {
        "agent": "Verifier Agent",
        "status": "placeholder",
        "tier": "Tier 3",
        "approved": False,
        "reasoning": "Verifier placeholder waiting for multi-agent inputs",
        "message": "Verifier agent ready for implementation in Phase 5"
    }

@app.post("/ask")
async def ask(payload: Dict[str, Any] = {}):
    return {
        "agent": "Coordinator Agent",
        "status": "placeholder",
        "final_response": {
            "tier": "Tier 3",
            "tier_label": "No Confident Match - Redirection to Senior Technician Required",
            "perception": None,
            "correlation": None,
            "memory": None,
            "verifier_criticism": "System operating with default baseline phase 1 configuration."
        }
    }

# Mount static directories
app.mount("/heatmaps", StaticFiles(directory=os.path.join(static_dir, "heatmaps")), name="heatmaps")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
