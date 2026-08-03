from __future__ import annotations
from pathlib import Path
import httpx
from .cache import FORECAST, OBSERVATIONS

NOAA_CFSV2_TEMPLATE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/cfs/cfs.{yyyymm}/00/monthly_grib_01/{variable}.{yyyymm}.grb2"
ERA5_NOTE = "ERA5 monthly means normally require CDS credentials; place files in cache/observations as {variable}_{yyyymm}.nc."

def _download(url: str, path: Path) -> Path | None:
    if path.exists():
        return path
    try:
        with httpx.stream("GET", url, timeout=30, follow_redirects=True) as r:
            if r.status_code != 200:
                return None
            with path.open("wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        return path
    except Exception:
        path.unlink(missing_ok=True)
        return None

def ensure_forecast_file(year: int, month: int, lead: int, variable: str) -> Path | None:
    yyyymm = f"{year:04d}{month:02d}"
    for ext in ("nc", "grib2", "grb2"):
        local = FORECAST / f"{variable}_{yyyymm}_lead{lead}.{ext}"
        if local.exists(): return local
    url = NOAA_CFSV2_TEMPLATE.format(yyyymm=yyyymm, variable=variable)
    return _download(url, FORECAST / f"{variable}_{yyyymm}_lead{lead}.grb2")

def ensure_observation_file(year: int, month: int, variable: str) -> Path | None:
    yyyymm = f"{year:04d}{month:02d}"
    for ext in ("nc", "grib2", "grb2"):
        local = OBSERVATIONS / f"{variable}_{yyyymm}.{ext}"
        if local.exists(): return local
    return None
