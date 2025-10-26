
import numpy as np, os

def load_model(weights_path: str):
    if os.path.exists(weights_path):
        try:
            import onnxruntime as ort
            return ("onnx", ort.InferenceSession(weights_path, providers=["CPUExecutionProvider"]))
        except Exception:
            pass
    return ("heuristic", None)

def _predict_with_onnx(session, frames):
    arr = np.stack(frames).astype("float32")/255.0
    arr = np.transpose(arr, (0,3,1,2))
    inputs = {session.get_inputs()[0].name: arr}
    out = session.run(None, inputs)[0].squeeze()
    out = np.atleast_1d(out)
    if (out<0).any() or (out>1).any():
        out = 1/(1+np.exp(-out))
    return out.tolist()

def _predict_heuristic(frames):
    import cv2, numpy as np
    probs = []
    for f in frames:
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        sharp = cv2.Laplacian(g, cv2.CV_64F).var()
        p = float(np.exp(-sharp/300.0))
        probs.append(p)
    return probs

def predict_batch(model_tuple, frames):
    kind, obj = model_tuple
    if kind == "onnx" and obj is not None:
        return _predict_with_onnx(obj, frames)
    return _predict_heuristic(frames)
