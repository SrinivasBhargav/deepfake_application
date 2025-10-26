
import os, uuid, boto3
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from celery import Celery

router = APIRouter()
cel = Celery(broker=os.getenv("REDIS_URL"), backend=os.getenv("REDIS_URL"))

class JobOut(BaseModel):
    job_id: str
    status: str

def _s3():
    return boto3.client("s3",
        endpoint_url=os.getenv("S3_ENDPOINT"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"))

@router.post("/upload", response_model=JobOut)
async def upload(file: UploadFile = File(...)):
    if file.content_type not in {"video/mp4","image/jpeg","image/png"}:
        raise HTTPException(400, "Only MP4/JPEG/PNG supported in starter.")
    s3 = _s3()
    bucket = os.getenv("S3_BUCKET")
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        s3.create_bucket(Bucket=bucket)
    key = f"uploads/{uuid.uuid4()}_{file.filename}"
    s3.upload_fileobj(file.file, bucket, key)
    task = cel.send_task("worker.tasks.process_media", kwargs={"s3_key": key})
    return JobOut(job_id=task.id, status="queued")

@router.get("/{job_id}", response_model=JobOut)
def status(job_id: str):
    res = cel.AsyncResult(job_id)
    return JobOut(job_id=job_id, status=res.status)

@router.get("/{job_id}/result")
def result(job_id: str):
    res = cel.AsyncResult(job_id)
    if not res.ready():
        return {"status": res.status}
    return res.get()
