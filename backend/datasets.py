from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import xarray as xr
from .cache import FORECAST, OBSERVATIONS, derived_path
from .download import ensure_forecast_file, ensure_observation_file

VARIABLES = {
    "t2m": {"label": "2-meter Temperature Anomaly", "units": "°C", "cfsv2": ["t2m", "tmp2m", "2t"], "obs": ["t2m", "air", "2t"]},
    "t850": {"label": "850 mb Temperature Anomaly", "units": "°C", "cfsv2": ["t", "tmp", "t850"], "obs": ["t", "air", "t850"]},
    "z500": {"label": "500 mb Geopotential Height Anomaly", "units": "m", "cfsv2": ["gh", "hgt", "z500"], "obs": ["z", "gh", "hgt", "z500"]},
    "precip": {"label": "Precipitation Anomaly", "units": "mm/month", "cfsv2": ["prate", "tp", "precip"], "obs": ["tp", "precip", "prate"]},
}

@dataclass(frozen=True)
class RequestKey:
    init_year: int
    init_month: int
    lead: int
    variable: str
    obs_year: int
    obs_month: int


def _open(path: Path) -> xr.Dataset:
    if path.suffix in {".grb", ".grib", ".grib2"}:
        return xr.open_dataset(path, engine="cfgrib")
    return xr.open_dataset(path)


def _pick(ds: xr.Dataset, names: list[str]) -> xr.DataArray:
    lowered = {k.lower(): k for k in ds.data_vars}
    for name in names:
        if name.lower() in lowered:
            return ds[lowered[name.lower()]]
    # development/demo fallback: first numeric variable
    for name, da in ds.data_vars.items():
        if np.issubdtype(da.dtype, np.number):
            return da
    raise ValueError("No numeric variable found")


def _normalize(da: xr.DataArray, variable: str) -> xr.DataArray:
    rename = {}
    for c in da.coords:
        lc = c.lower()
        if lc in {"latitude", "lat"}: rename[c] = "lat"
        if lc in {"longitude", "lon"}: rename[c] = "lon"
    da = da.rename(rename).squeeze(drop=True)
    if "lon" in da.coords and float(da.lon.max()) > 180:
        da = da.assign_coords(lon=(((da.lon + 180) % 360) - 180)).sortby("lon")
    if variable in {"t2m", "t850"} and float(da.mean(skipna=True)) > 100:
        da = da - 273.15
    if variable == "z500" and float(abs(da).mean(skipna=True)) > 1000:
        da = da / 9.80665
    return da


def _synthetic(variable: str, seed: int) -> xr.DataArray:
    rng = np.random.default_rng(seed)
    lat = np.arange(-90, 91, 2.5)
    lon = np.arange(-180, 180, 2.5)
    wave = np.outer(np.sin(np.deg2rad(lat * 2)), np.cos(np.deg2rad(lon)))
    scale = {"t2m": 3, "t850": 3, "z500": 80, "precip": 50}[variable]
    return xr.DataArray(scale * wave + rng.normal(0, scale / 5, (lat.size, lon.size)), coords={"lat": lat, "lon": lon}, dims=("lat", "lon"), name=variable)


def regrid_to_forecast(obs: xr.DataArray, forecast: xr.DataArray) -> xr.DataArray:
    return obs.interp(lat=forecast.lat, lon=forecast.lon, method="linear")


def load_pair(key: RequestKey) -> tuple[xr.DataArray, xr.DataArray]:
    cache = derived_path(key.init_year, key.init_month, key.lead, key.variable, key.obs_year, key.obs_month)
    if cache.exists():
        ds = xr.open_dataset(cache)
        return ds["forecast"], ds["observed"]
    fpath = ensure_forecast_file(key.init_year, key.init_month, key.lead, key.variable)
    opath = ensure_observation_file(key.obs_year, key.obs_month, key.variable)
    if fpath and opath:
        f = _normalize(_pick(_open(fpath), VARIABLES[key.variable]["cfsv2"]), key.variable)
        o = _normalize(_pick(_open(opath), VARIABLES[key.variable]["obs"]), key.variable)
    else:
        f = _synthetic(key.variable, key.init_year * 100 + key.init_month * 10 + key.lead)
        o = _synthetic(key.variable, key.obs_year * 100 + key.obs_month)
    o = regrid_to_forecast(o, f)
    xr.Dataset({"forecast": f, "observed": o}).to_netcdf(cache)
    return f, o
