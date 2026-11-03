import os, sys, time, json
import sys as _s; _s.path[:0] = [_s.argv[1], _s.argv[2]]
import numpy as np
sys.path[:0] = [sys.argv[1], sys.argv[2]]
os.environ["DV2_STRICT"] = "1"
import DV2_Vertex as D
rng = np.random.default_rng(1)
# synthetic 2-prong event: a 40 cm track + a displaced 20 cm "shower" blob, inside SBND
v = np.array([-100.0, 0.0, 200.0])
t = np.linspace(0, 40, 200)[:, None] * np.array([0.3, 0.2, 0.93]) + v
s = v + np.array([5, -10, 30]) + rng.normal(0, 3, (300, 3))
pts = np.vstack([v[None, :], (v + [0, 0, 40])[None, :], t, s]).astype(np.float32)
q = np.concatenate([[0, 0], np.full(200, 1.0), np.full(300, 0.6)]).astype(np.float32) * 1000
trad = np.array([-100.0, 0.0, 240.0], dtype=np.float32)
t0 = time.time()
out = D.DV2_Vertex(sys.argv[3], pts[:,0].tobytes(), pts[:,1].tobytes(), pts[:,2].tobytes(), q.tobytes(), 2, trad.tobytes(), 0.1, -1000.0, "float32")
print("elapsed_s", round(time.time() - t0, 1))
print("out", np.frombuffer(out, dtype=np.float32))
print("rec", json.dumps(D._LAST)[:600])
import torch, lightgbm, scipy
print("versions torch", torch.__version__, "numpy", np.__version__, "scipy", scipy.__version__, "lightgbm", lightgbm.__version__)
