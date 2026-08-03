from __future__ import annotations
from datetime import date
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import numpy as np
from .datasets import RequestKey, VARIABLES, load_pair
from .verification import verification_month, stats, subset_region

app = FastAPI(title="NOAA CFSv2 Monthly Verification Viewer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
ROOT = Path(__file__).resolve().parents[1]
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")

@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")

@app.get("/api/options")
def options():
    now = date.today()
    months = []
    y, m = 2011, 1
    while (y, m) <= (now.year, now.month):
        months.append({"year": y, "month": m, "label": f"{date(y,m,1):%B %Y}"})
        m += 1
        if m == 13: y, m = y + 1, 1
    return {"initializations": months, "leads": list(range(1, 10)), "variables": VARIABLES}

def _payload(da):
    return {"lat": da.lat.values.tolist(), "lon": da.lon.values.tolist(), "values": np.round(da.values, 4).tolist()}

@app.get("/api/verify")
def verify(init_year: int, init_month: int, lead: int = Query(1, ge=1, le=9), variable: str = "t2m", west: float | None = None, south: float | None = None, east: float | None = None, north: float | None = None):
    obs_year, obs_month = verification_month(init_year, init_month, lead)
    key = RequestKey(init_year, init_month, lead, variable, obs_year, obs_month)
    forecast, observed = load_pair(key)
    diff = forecast - observed
    bounds = None if None in (west, south, east, north) else {"west": west, "south": south, "east": east, "north": north}
    regional_f = subset_region(forecast, bounds)
    regional_o = subset_region(observed, bounds)
    return {
        "metadata": {"init": f"{init_year:04d}-{init_month:02d}", "lead": lead, "verification": f"{obs_year:04d}-{obs_month:02d}", "variable": variable, "units": VARIABLES[variable]["units"]},
        "forecast": _payload(forecast), "observed": _payload(observed), "difference": _payload(diff),
        "statistics": stats(forecast, observed),
        "regional": {"bounds": bounds, "forecast_mean": regional_f.mean(skipna=True).item(), "observed_mean": regional_o.mean(skipna=True).item(), **stats(regional_f, regional_o)},
        "metric_explanations": {
            "mean_bias": "Area-weighted mean forecast minus observed anomaly.", "mae": "Area-weighted mean absolute error.", "rmse": "Square root of the area-weighted mean squared error.", "pattern_correlation": "Pearson similarity of the anomaly patterns.", "spatial_correlation": "Gridpoint Pearson correlation over the selected domain.", "acc": "Area-weighted anomaly correlation coefficient.", "score": "0-100 blend of ACC, spatial correlation, and RMSE skill."
        }
    }
