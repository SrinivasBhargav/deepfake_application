
import numpy as np
def fuse_scores(frame_probs, method="avg"):
    if not frame_probs: return 0.5
    if method == "max": return float(np.max(frame_probs))
    return float(np.mean(frame_probs))
