
import argparse, glob, os, cv2
from preprocessing.extract_frames import extract_frames_from_video

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True)
ap.add_argument("--dst", required=True)
ap.add_argument("--every-n", type=int, default=10)
args = ap.parse_args()
os.makedirs(args.dst, exist_ok=True)

for v in glob.glob(args.src):
    frames = extract_frames_from_video(v, every_n=args.every_n, size=(224,224))
    base = os.path.splitext(os.path.basename(v))[0]
    for i, f in enumerate(frames):
        cv2.imwrite(os.path.join(args.dst, f"{base}_{i:04d}.jpg"), f[:,:,::-1])
print("Done")
