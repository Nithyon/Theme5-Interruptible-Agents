"""Media helpers: locate referenced files and embed frames.

Missing or unreadable files return None; callers turn that into a clarification.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Optional

_PKG_ROOT = Path(__file__).resolve().parent.parent

_MIME = {
    ".mp3": "audio/mp3", ".wav": "audio/wav", ".flac": "audio/flac", ".ogg": "audio/ogg",
    ".m4a": "audio/aac", ".aac": "audio/aac", ".aiff": "audio/aiff", ".webm": "audio/webm",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
}


def resolve(ref: str) -> Optional[Path]:
    if not ref or not isinstance(ref, str):
        return None
    p = Path(ref)
    candidates = [p] if p.is_absolute() else [Path.cwd() / p, _PKG_ROOT / p]
    for c in candidates:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


def read_bytes(ref: str) -> Optional[bytes]:
    path = resolve(ref)
    if path is None:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def sniff_mime(ref: str, data: Optional[bytes] = None) -> str:
    if data:
        head = data[:12]
        if head.startswith(b"RIFF") and head[8:12] == b"WAVE":
            return "audio/wav"
        if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
            return "audio/mp3"
        if head.startswith(b"fLaC"):
            return "audio/flac"
        if head.startswith(b"OggS"):
            return "audio/ogg"
        if head.startswith(b"\x89PNG"):
            return "image/png"
        if head[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
    return _MIME.get(os.path.splitext(ref or "")[1].lower(), "application/octet-stream")


def image_embedding(ref: str, dims_side: int = 8) -> Optional[List[float]]:
    """A dense descriptor of the frame computed from its pixels.

    Concatenates an 8x8 grayscale thumbnail and a 4x4 grid of mean RGB colours,
    then L2-normalises. Cheap and deterministic; kept behind this one function
    so a learned embedding can replace it.
    """
    path = resolve(ref)
    if path is None:
        return None
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return None
    try:
        with Image.open(path) as im:
            rgb = im.convert("RGB")
            gray = np.asarray(rgb.convert("L").resize((dims_side, dims_side)), dtype=np.float32) / 255.0
            grid = np.asarray(rgb.resize((4, 4)), dtype=np.float32) / 255.0
    except Exception:
        return None
    vec = np.concatenate([gray.ravel() - gray.mean(), grid.ravel()])
    norm = float(np.linalg.norm(vec)) or 1.0
    return [round(float(v) / norm, 5) for v in vec]
