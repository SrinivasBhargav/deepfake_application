
import cv2
def extract_frames_from_video(video_path, every_n=5, size=(224,224)):
    cap = cv2.VideoCapture(video_path)
    frames, idx = [], 0
    while True:
        ok, frame = cap.read()
        if not ok: break
        if idx % every_n == 0:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, size)
            frames.append(frame)
        idx += 1
    cap.release()
    return frames

def load_image_as_frame(path, size=(224,224)):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, size)
    return img
