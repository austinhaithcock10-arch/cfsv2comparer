const STATIC_VARIABLES = {
  t2m: { label: '2-meter Temperature Anomaly', units: '°C' },
  t850: { label: '850 mb Temperature Anomaly', units: '°C' },
  z500: { label: '500 mb Geopotential Height Anomaly', units: 'm' },
  precip: { label: 'Precipitation Anomaly', units: 'mm/month' }
};

function verificationMonth(initYear, initMonth, lead) {
  const zeroBased = initYear * 12 + (initMonth - 1) + Number(lead);
  return { year: Math.floor(zeroBased / 12), month: (zeroBased % 12) + 1 };
}

function staticOptions() {
  const now = new Date();
  const initializations = [];
  for (let y = 2011, m = 1; y < now.getUTCFullYear() || (y === now.getUTCFullYear() && m <= now.getUTCMonth() + 1);) {
    initializations.push({ year: y, month: m, label: new Date(Date.UTC(y, m - 1, 1)).toLocaleString('en', { month: 'long', year: 'numeric', timeZone: 'UTC' }) });
    m += 1;
    if (m === 13) { y += 1; m = 1; }
  }
  return { initializations, leads: [1, 2, 3, 4, 5, 6, 7, 8, 9], variables: STATIC_VARIABLES, staticMode: true };
}

function seededNoise(seed) {
  let x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

function makeGrid(variable, seed, observed = false) {
  const lat = [], lon = [], values = [];
  const scale = variable === 'z500' ? 90 : variable === 'precip' ? 55 : 4;
  for (let y = -90; y <= 90; y += 2.5) lat.push(y);
  for (let x = -180; x < 180; x += 2.5) lon.push(x);
  for (let i = 0; i < lat.length; i += 1) {
    const row = [];
    for (let j = 0; j < lon.length; j += 1) {
      const phase = observed ? 0.55 : 0;
      const planetaryWave = Math.sin((lat[i] * 2 + seed % 30) * Math.PI / 180) * Math.cos((lon[j] + phase * 30) * Math.PI / 180);
      const regionalWave = 0.45 * Math.sin((lon[j] / 2 + seed) * Math.PI / 180) * Math.cos((lat[i] + seed % 20) * Math.PI / 180);
      const noise = (seededNoise(seed + i * 97 + j * 131) - 0.5) * scale * 0.25;
      row.push(Number((scale * (planetaryWave + regionalWave) + noise).toFixed(4)));
    }
    values.push(row);
  }
  return { lat, lon, values };
}

function flattenValid(a, b) {
  const pairs = [];
  for (let i = 0; i < a.values.length; i += 1) {
    const w = Math.max(0, Math.cos(a.lat[i] * Math.PI / 180));
    for (let j = 0; j < a.values[i].length; j += 1) pairs.push([a.values[i][j], b.values[i][j], w]);
  }
  return pairs;
}

function gridStats(forecast, observed) {
  const pairs = flattenValid(forecast, observed);
  const wsum = pairs.reduce((s, p) => s + p[2], 0);
  const meanF = pairs.reduce((s, p) => s + p[0] * p[2], 0) / wsum;
  const meanO = pairs.reduce((s, p) => s + p[1] * p[2], 0) / wsum;
  const meanBias = pairs.reduce((s, p) => s + (p[0] - p[1]) * p[2], 0) / wsum;
  const mae = pairs.reduce((s, p) => s + Math.abs(p[0] - p[1]) * p[2], 0) / wsum;
  const rmse = Math.sqrt(pairs.reduce((s, p) => s + (p[0] - p[1]) ** 2 * p[2], 0) / wsum);
  const cov = pairs.reduce((s, p) => s + (p[0] - meanF) * (p[1] - meanO) * p[2], 0) / wsum;
  const vf = pairs.reduce((s, p) => s + (p[0] - meanF) ** 2 * p[2], 0) / wsum;
  const vo = pairs.reduce((s, p) => s + (p[1] - meanO) ** 2 * p[2], 0) / wsum;
  const acc = cov / Math.sqrt(vf * vo);
  const score = Math.max(0, Math.min(100, 100 * (0.8 * Math.max(acc, 0) + 0.2 * Math.exp(-rmse / 3))));
  return { mean_bias: meanBias, mae, rmse, pattern_correlation: acc, spatial_correlation: acc, acc, score };
}

function differenceGrid(forecast, observed) {
  return { lat: forecast.lat, lon: forecast.lon, values: forecast.values.map((row, i) => row.map((v, j) => Number((v - observed.values[i][j]).toFixed(4)))) };
}

async function staticVerify(params) {
  const initYear = Number(params.get('init_year'));
  const initMonth = Number(params.get('init_month'));
  const lead = Number(params.get('lead'));
  const variable = params.get('variable') || 't2m';
  const verifying = verificationMonth(initYear, initMonth, lead);
  const forecast = makeGrid(variable, initYear * 1000 + initMonth * 20 + lead, false);
  const observed = makeGrid(variable, verifying.year * 100 + verifying.month, true);
  const difference = differenceGrid(forecast, observed);
  const statistics = gridStats(forecast, observed);
  return {
    metadata: { init: `${initYear}-${String(initMonth).padStart(2, '0')}`, lead, verification: `${verifying.year}-${String(verifying.month).padStart(2, '0')}`, variable, units: STATIC_VARIABLES[variable].units, staticMode: true },
    forecast, observed, difference, statistics,
    regional: { bounds: null, forecast_mean: 0, observed_mean: 0, ...statistics },
    metric_explanations: {
      mean_bias: 'Area-weighted mean forecast minus observed anomaly.', mae: 'Area-weighted mean absolute error.', rmse: 'Square root of the area-weighted mean squared error.', pattern_correlation: 'Pearson similarity of anomaly patterns.', spatial_correlation: 'Gridpoint Pearson correlation.', acc: 'Area-weighted anomaly correlation coefficient.', score: '0-100 blend of ACC and RMSE skill.'
    }
  };
}
