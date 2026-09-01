import os
import uuid
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from perception.agent import PerceptionAgent
from correlation.agent import CorrelationAgent
from memory.agent import MemoryAgent
from verifier.agent import VerifierAgent
from coordinator.agent import CoordinatorAgent

app = FastAPI(
    title="TACET DISCORD",
    description="Shift-handoff copilot preserving senior technician knowledge with Active Evidence Gathering & Factory Onboarding",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate Agents
perception_agent = PerceptionAgent()
correlation_agent = CorrelationAgent()
memory_agent = MemoryAgent()
verifier_agent = VerifierAgent(
    perception_agent=perception_agent,
    correlation_agent=correlation_agent,
    memory_agent=memory_agent
)
coordinator_agent = CoordinatorAgent(verifier_agent=verifier_agent)

# Static file serving
static_dir = os.path.join(os.path.dirname(__file__), "static")
uploads_dir = os.path.join(os.path.dirname(__file__), "data", "uploads")
heatmaps_dir = os.path.join(os.path.dirname(__file__), "heatmaps")

os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(heatmaps_dir, exist_ok=True)

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
if os.path.exists(heatmaps_dir):
    app.mount("/heatmaps", StaticFiles(directory=heatmaps_dir), name="heatmaps")

@app.get("/")
async def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        from fastapi.responses import FileResponse
        return FileResponse(index_path)
    return {"message": "Welcome to TACET DISCORD Multi-Agent API"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "system": "TACET DISCORD Multi-Agent Framework with Active Evidence Gathering",
        "agents": ["perception", "correlation", "memory", "verifier", "coordinator", "investigation"]
    }

@app.get("/factory-state")
async def get_factory_state():
    return coordinator_agent.factory_state_manager.get_factory_state()

@app.post("/perceive")
async def perceive(file: Optional[UploadFile] = File(None), image_path: Optional[str] = Form(None)):
    target_path = image_path
    if file:
        file_ext = os.path.splitext(file.filename)[1] or ".png"
        filename = f"upload_{uuid.uuid4().hex[:8]}{file_ext}"
        target_path = os.path.join(uploads_dir, filename)
        with open(target_path, "wb") as f:
            f.write(await file.read())

    if not target_path or not os.path.exists(target_path):
        target_path = "data/mvtec/bottle/test/broken_large/000.png"

    return perception_agent.perceive(target_path)

@app.post("/correlate")
async def correlate(
    telemetry_mode: str = Form("normal"),
    perception_score: Optional[float] = Form(None),
    file_path: Optional[str] = Form(None)
):
    return correlation_agent.correlate(
        telemetry_mode=telemetry_mode,
        perception_score=perception_score,
        file_path=file_path
    )

@app.post("/recall")
async def recall(image_path: str = Form(...)):
    return memory_agent.recall(image_path)

class RememberRequest(BaseModel):
    image_path: str
    confirmed_diagnosis: str
    fix_steps: str
    voice_note_path: Optional[str] = None
    confidence_at_capture: float = 0.95

@app.post("/remember")
async def remember(req: RememberRequest):
    return memory_agent.remember(
        image_path=req.image_path,
        confirmed_diagnosis=req.confirmed_diagnosis,
        fix_steps=req.fix_steps,
        voice_note_path=req.voice_note_path,
        confidence_at_capture=req.confidence_at_capture
    )

@app.post("/verify")
async def verify(image_path: str = Form(...), telemetry_mode: str = Form("normal")):
    return verifier_agent.verify(image_path=image_path, telemetry_mode=telemetry_mode)

@app.post("/ask")
async def ask(
    file: Optional[UploadFile] = File(None),
    image_path: Optional[str] = Form(None),
    telemetry_mode: Optional[str] = Form("normal")
):
    target_path = image_path
    if file:
        file_ext = os.path.splitext(file.filename)[1] or ".png"
        filename = f"ask_{uuid.uuid4().hex[:8]}{file_ext}"
        target_path = os.path.join(uploads_dir, filename)
        with open(target_path, "wb") as f:
            f.write(await file.read())

    if not target_path or not os.path.exists(target_path):
        target_path = "data/mvtec/bottle/test/broken_large/000.png"

    return coordinator_agent.ask(image_path=target_path, telemetry_mode=telemetry_mode)

class AcquireRequest(BaseModel):
    image_path: str
    evidence_id: Optional[str] = "vibration_sample_10s"

@app.post("/acquire")
async def acquire_evidence(req: AcquireRequest):
    return coordinator_agent.investigation_engine.acquire_and_rerun(
        image_path=req.image_path,
        evidence_id=req.evidence_id
    )
