"""
RIT-Sync Vision - Model Downloader
Author: Paul Bryton Raj (AI & System Lead)

Fetches model weights that are too large to keep in Git into ai_engine/models/ and verifies
their SHA-256 checksums. Run once after cloning:

    python scripts/download_models.py

Models:
- face_recognition_sface_2021dec.onnx  (OpenCV Zoo, Apache-2.0, ~37 MB)
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "ai_engine" / "models"

MODELS = {
    "face_recognition_sface_2021dec.onnx": {
        "url": "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/"
        "face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "sha256": "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    },
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    ok = True
    for name, info in MODELS.items():
        dest = MODELS_DIR / name
        if dest.exists() and sha256_of(dest) == info["sha256"]:
            print(f"[ok]   {name} already present")
            continue
        print(f"[get]  {name}")
        tmp = dest.with_suffix(dest.suffix + ".part")
        urllib.request.urlretrieve(info["url"], tmp)
        digest = sha256_of(tmp)
        if digest != info["sha256"]:
            tmp.unlink(missing_ok=True)
            print(f"[FAIL] {name}: checksum mismatch ({digest})")
            ok = False
            continue
        tmp.replace(dest)
        print(f"[ok]   {name} verified")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
