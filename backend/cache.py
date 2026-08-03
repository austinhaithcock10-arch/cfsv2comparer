from __future__ import annotations
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache"
FORECAST = CACHE / "forecast"
OBSERVATIONS = CACHE / "observations"
DERIVED = CACHE / "derived"

for directory in (FORECAST, OBSERVATIONS, DERIVED):
    directory.mkdir(parents=True, exist_ok=True)

def safe_key(*parts: object) -> str:
    text = "|".join(str(p) for p in parts)
    return hashlib.sha256(text.encode()).hexdigest()[:16]

def derived_path(*parts: object, suffix: str = ".nc") -> Path:
    return DERIVED / f"{safe_key(*parts)}{suffix}"
