import os, io, json, cv2, numpy as np
from celery import Celery
from minio import Minio

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_PASS = os.getenv("MINIO_ROOT_PASSWORD", "minio123")
BUCKET = os.getenv("STORAGE_BUCKET", "media")

celery = Celery(__name__, broker=REDIS_URL, backend=REDIS_URL)

def mclient():
    return Minio(MINIO_ENDPOINT, access_key=MINIO_USER, secret_key=MINIO_PASS, secure=False)

def _load_image_from_minio(key:str):
    mc = mclient()
    obj = mc.get_object(BUCKET, key)
    raw = obj.read()
    img = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    return img

def _extract_frames_from_video(key:str, every_n:int=10, max_frames:int=32):
    mc = mclient()
    tmp = f"/tmp/{os.path.basename(key)}"
    mc.fget_object(BUCKET, key, tmp)
    cap = cv2.VideoCapture(tmp)
    frames, idx = [], 0
    while cap.isOpened():
        ok, frame = cap.read()
        if not ok: break
        if idx % every_n == 0:
            frames.append(frame)
            if len(frames) >= max_frames: break
        idx += 1
    cap.release()
    try: os.remove(tmp)
    except: pass
    return frames

def _heuristic_score(frame: np.ndarray) -> float:
    # very simple baseline: “sharpness” inverse + noise ratio → 0..1
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    var = cv2.Laplacian(gray, cv2.CV_64F).var()  # focus measure
    var_norm = 1.0 / (1.0 + var/100.0)
    noise = np.std(gray)/255.0
    return float(np.clip(0.5*var_norm + 0.5*noise, 0.0, 1.0))

@celery.task(name="worker.tasks.process_media")
def process_media(job_id: str, key: str, content_type: str):
    # Decide image vs video
    is_image = (content_type or "").startswith("image/")
    if is_image:
        frame = _load_image_from_minio(key)
        frames = [frame] if frame is not None else []
    else:
        frames = _extract_frames_from_video(key)

    scores = [_heuristic_score(f) for f in frames] if frames else [0.0]
    score = float(np.mean(scores))
    result = {
        "job_id": job_id,
        "status": "completed",
        "n_frames": int(len(frames)),
        "score": score
    }

    # Save result JSON to MinIO (authoritative)
    mc = mclient()
    data = json.dumps(result).encode("utf-8")
    mc.put_object(BUCKET, f"results/{job_id}.json", io.BytesIO(data), length=len(data), content_type="application/json")

    return result
