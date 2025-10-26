from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from pathlib import Path
import os
from .db import SessionLocal, init_db
from .models import Job, Result
from redis import Redis
from rq import Queue

MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "/media"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = FastAPI(title="Deepfake Agent (MVP)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

class JobResp(BaseModel):
    job_id: str
    status: str

@app.post("/v1/jobs/upload", response_model=JobResp)
async def upload_job(file: UploadFile = File(...)):
    job_id = str(uuid4())
    ext = Path(file.filename).suffix or ""
    save_path = MEDIA_DIR / f"{job_id}{ext}"

    # save file to disk
    with save_path.open("wb") as f:
        f.write(await file.read())

    # write DB row
    db = SessionLocal()
    job = Job(id=job_id, status="PENDING", media_type=file.content_type or "unknown", filename=str(save_path))
    db.add(job); db.commit(); db.close()

    # enqueue
    q = Queue("jobs", connection=Redis.from_url(REDIS_URL))
    q.enqueue("workers.tasks.process_job", job_id)

    return {"job_id": job_id, "status": "PENDING"}

class StatusResp(BaseModel):
    job_id: str
    status: str
    score: float | None = None
    message: str | None = None

@app.get("/v1/jobs/{job_id}", response_model=StatusResp)
def get_status(job_id: str):
    db = SessionLocal()
    job = db.get(Job, job_id)
    if not job:
        db.close()
        raise HTTPException(status_code=404, detail="job not found")
    res = db.query(Result).filter_by(job_id=job_id).first()
    payload = {"job_id": job_id, "status": job.status}
    if res:
        payload.update({"score": res.score, "message": res.message})
    db.close()
    return payload
