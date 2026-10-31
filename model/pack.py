"""Pack the viewer's binary layers into lossless RGB PNGs (served everywhere, smaller on the wire).
Byte stream -> rows of 1024 RGB pixels; the true byte length is stored in meta.json["packed"]."""
import json, os
import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "data")
WIDTH = 1024
meta_path = os.path.join(OUT, "meta.json")
meta = json.load(open(meta_path))
meta["packed"] = {}
for name in ("grid", "air20", "dem", "buildings", "roads"):
    src = os.path.join(OUT, name + ".bin")
    raw = np.fromfile(src, np.uint8)
    rows = -(-len(raw) // (WIDTH * 3))
    buf = np.zeros(rows * WIDTH * 3, np.uint8)
    buf[:len(raw)] = raw
    Image.fromarray(buf.reshape(rows, WIDTH, 3), "RGB").save(os.path.join(OUT, name + ".png"), optimize=True)
    meta["packed"][name] = int(len(raw))
    os.remove(src)
    print(name, len(raw), "->", os.path.getsize(os.path.join(OUT, name + ".png")))
json.dump(meta, open(meta_path, "w"), separators=(",", ":"), ensure_ascii=False)
