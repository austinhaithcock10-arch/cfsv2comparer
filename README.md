# NOAA CFSv2 Monthly Verification Viewer

A FastAPI + vanilla JavaScript web application for comparing archived NOAA CFSv2 monthly forecasts with observed monthly analyses. It uses gridded numerical data, not screenshots, and automatically matches initialization month plus lead time to the verifying observation month.

## Features

- Forecast, observed, and forecast-minus-observed maps with Leaflet zoom/pan/hover.
- Lead 1 through Lead 9 monthly verification.
- Variables: 2-meter temperature, 850 mb temperature, 500 mb height, and precipitation anomalies.
- NOAA, Tropical Tidbits-style, and colorblind-friendly palettes.
- Objective statistics: mean bias, MAE, RMSE, pattern/spatial correlation, ACC, and a 0-100 score.
- Region-ready API parameters (`west`, `south`, `east`, `north`) for drag-box clients.
- Download statistics as CSV and local cache reuse.


## GitHub Pages Deployment

This repository can be published directly with GitHub Pages because `index.html` redirects to the static viewer in `frontend/`. In Pages/static mode there is no Python runtime, no secure place for ERA5 credentials, and browser CORS rules can prevent direct NOAA/ERA5 downloads. The site therefore falls back to deterministic sample grids so the UI, time matching, color tables, animation, CSV export, and metric calculations still work online.

For scientifically authoritative verification on GitHub Pages, precompute gridded forecast/observation anomaly pairs with the FastAPI backend or another trusted workflow, publish those files as static assets, and point the frontend at those precomputed products. For automatic archive lookup, downloading, regridding, and caching, run the FastAPI backend.

To enable Pages:

1. Push this branch to GitHub.
2. In repository settings, choose **Pages**.
3. Select deployment from the branch root.
4. Open the Pages URL; it will load `frontend/index.html`.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

System packages for `eccodes`, `cfgrib`, and `cartopy` may be required by your OS.

## Running

```bash
uvicorn backend.app:app --reload
```

Open <http://127.0.0.1:8000>.

## Cache Structure

```text
cache/
  forecast/      original CFSv2 GRIB2/NetCDF files
  observations/  ERA5 or NCEP/NCAR monthly analysis files
  derived/       paired, regridded anomaly NetCDF files
```

Files already present in cache are reused and never downloaded again.

## Dataset Download and Naming

The app first looks for local files:

- `cache/forecast/{variable}_{YYYYMM}_lead{N}.nc|grib2|grb2`
- `cache/observations/{variable}_{YYYYMM}.nc|grib2|grb2`

If forecast files are absent it attempts a NOAA NOMADS archive URL. ERA5 monthly means generally require Copernicus CDS credentials, so place ERA5 monthly anomaly files in `cache/observations`. NCEP/NCAR files can be used with the same naming convention as a fallback.

## Time Matching

The verifying month is calculated as:

```text
verification_month = initialization_month + lead
```

For example, September 2025 plus Lead 4 verifies against January 2026.

## Methodology

All verification is computed from gridded data with `xarray` and `numpy`. Observations are interpolated to the forecast latitude/longitude grid with linear interpolation. Temperature is converted from Kelvin to Celsius when needed, and geopotential is converted to meters when needed. Operational deployments should ensure forecast and observed anomalies use the same climatological baseline before files enter the cache.

## Metrics

- **Mean Bias**: area-weighted mean forecast anomaly minus observed anomaly.
- **MAE**: area-weighted mean absolute error.
- **RMSE**: square root of area-weighted mean squared error.
- **Pattern/Spatial Correlation**: Pearson correlation of forecast and observed gridpoint anomaly patterns.
- **ACC**: area-weighted anomaly correlation coefficient after removing domain means.
- **Score**: a bounded 0-100 blend of ACC, spatial correlation, and RMSE skill.

## Troubleshooting

- **NOAA download failures**: verify archive availability, variable naming, and internet access. Manually place GRIB2/NetCDF files in `cache/forecast` if the operational path has changed.
- **ERA5 failures**: install and configure CDS API credentials, download monthly means, compute anomalies against your selected climatology, and save them in `cache/observations`.
- **cfgrib/eccodes errors**: install the native ECMWF ecCodes library and rebuild the Python environment.
- **Cartopy install issues**: install GEOS/PROJ dependencies from your OS package manager or conda-forge.

## Scientific Notes

This project is designed around original gridded forecast and observational fields. Rendered images are never used for verification. For production scientific verification, precompute anomalies for both forecasts and observations against the same climatology and audit any regridding choices for the target domain.
