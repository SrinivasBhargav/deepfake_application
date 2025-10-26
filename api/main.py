from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, uuid, json
from minio import Minio
from celery.result import AsyncResult
from celery import Celery

# ---------- env ----------
ALLOW_ORIGIN = os.getenv("ALLOW_ORIGIN", "http://localhost:5500").split(",")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_PASS = os.getenv("MINIO_ROOT_PASSWORD", "minio123")
BUCKET = os.getenv("STORAGE_BUCKET", "media")

# ---------- setup ----------
app = FastAPI(title="Deepfake Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGIN if "*" not in ALLOW_ORIGIN else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

celery = Celery(__name__, broker=REDIS_URL, backend=REDIS_URL)

def minio_client():
    return Minio(MINIO_ENDPOINT, access_key=MINIO_USER, secret_key=MINIO_PASS, secure=False)

# ensure bucket
try:
    mc = minio_client()
    if not mc.bucket_exists(BUCKET):
        mc.make_bucket(BUCKET)
except Exception:
    pass

@app.get("/healthz")
def healthz():
    return {"ok": True}

class JobOut(BaseModel):
    job_id: str
    status: str

@app.post("/v1/jobs/upload", response_model=JobOut)
def upload(file: UploadFile = File(...)):
    # 1) store upload in MinIO
    job_id = str(uuid.uuid4())
    key = f"uploads/{job_id}_{file.filename}"
    mc = minio_client()
    mc.put_object(BUCKET, key, file.file, length=-1, part_size=10*1024*1024, content_type=file.content_type)

    # 2) enqueue task
    task = celery.send_task("worker.tasks.process_media",
                            args=[job_id, key, file.content_type],
                            queue="default")

    return {"job_id": task.id, "status": "queued"}

@app.get("/v1/jobs/{job_id}")
def job_status(job_id: str):
    r = AsyncResult(job_id, app=celery)
    return {"job_id": job_id, "status": r.status}

@app.get("/v1/jobs/{job_id}/result")
def job_result(job_id: str):
    # Try celery backend
    r = AsyncResult(job_id, app=celery)
    data = r.result if isinstance(r.result, dict) else None

    # If not present, try MinIO JSON (authoritative)
    if not data:
        mc = minio_client()
        res_key = f"results/{job_id}.json"
        if mc.stat_object(BUCKET, res_key):
            resp = mc.get_object(BUCKET, res_key)
            data = json.loads(resp.read().decode("utf-8"))
    if not data:
        raise HTTPException(status_code=404, detail="Result not ready")
    return data
