from __future__ import annotations
import numpy as np
import xarray as xr


def verification_month(init_year: int, init_month: int, lead: int) -> tuple[int, int]:
    if not 1 <= lead <= 9:
        raise ValueError("lead must be 1-9")
    idx = init_year * 12 + (init_month - 1) + lead
    return idx // 12, idx % 12 + 1


def area_weights(lat: xr.DataArray) -> xr.DataArray:
    return np.cos(np.deg2rad(lat)).clip(min=0)


def _valid_pair(forecast: xr.DataArray, observed: xr.DataArray):
    f, o = xr.align(forecast, observed, join="inner")
    mask = np.isfinite(f) & np.isfinite(o)
    return f.where(mask), o.where(mask), mask


def stats(forecast: xr.DataArray, observed: xr.DataArray) -> dict[str, float]:
    f, o, mask = _valid_pair(forecast, observed)
    w = area_weights(f["lat"]) if "lat" in f.coords else 1
    diff = f - o
    bias = diff.weighted(w).mean(skipna=True).item()
    mae = abs(diff).weighted(w).mean(skipna=True).item()
    rmse = np.sqrt((diff ** 2).weighted(w).mean(skipna=True)).item()
    fv = f.values[mask.values]
    ov = o.values[mask.values]
    spatial = float(np.corrcoef(fv, ov)[0, 1]) if fv.size > 1 else np.nan
    fp = f - f.weighted(w).mean(skipna=True)
    op = o - o.weighted(w).mean(skipna=True)
    numerator = (fp * op).weighted(w).mean(skipna=True)
    denominator = np.sqrt((fp**2).weighted(w).mean(skipna=True) * (op**2).weighted(w).mean(skipna=True))
    acc = (numerator / denominator).item() if denominator.item() != 0 else np.nan
    score = float(np.clip(100 * (0.55 * max(acc, 0) + 0.25 * max(spatial, 0) + 0.20 * np.exp(-rmse / 3)), 0, 100))
    return {"mean_bias": bias, "mae": mae, "rmse": rmse, "pattern_correlation": spatial, "spatial_correlation": spatial, "acc": acc, "score": score}


def subset_region(field: xr.DataArray, bounds: dict | None) -> xr.DataArray:
    if not bounds:
        return field
    west, south, east, north = bounds["west"], bounds["south"], bounds["east"], bounds["north"]
    lon = field.lon
    if float(lon.max()) > 180 and west < 0:
        west, east = west % 360, east % 360
    lat_slice = slice(south, north) if field.lat[0] < field.lat[-1] else slice(north, south)
    if west <= east:
        return field.sel(lat=lat_slice, lon=slice(west, east))
    return xr.concat([field.sel(lat=lat_slice, lon=slice(west, float(lon.max()))), field.sel(lat=lat_slice, lon=slice(float(lon.min()), east))], dim="lon")
