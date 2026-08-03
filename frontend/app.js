let payload;
let usingStaticMode = false;

async function fetchJsonOrStatic(url, staticHandler) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    usingStaticMode = true;
    return staticHandler(new URL(url, window.location.href).searchParams);
  }
}

async function loadOptions() {
  const options = await fetchJsonOrStatic('/api/options', () => staticOptions());
  init.innerHTML = options.initializations
    .map((month) => `<option value="${month.year}-${month.month}">${month.label}</option>`)
    .join('');
  init.selectedIndex = Math.max(0, options.initializations.length - 2);
  lead.innerHTML = options.leads.map((l) => `<option value="${l}">Lead ${l}</option>`).join('');
  vars.innerHTML = Object.entries(options.variables)
    .map(([key, variable], index) => `<label><input type="radio" name="var" value="${key}" ${index ? '' : 'checked'}>${variable.label}</label>`)
    .join('');

  document.querySelectorAll('select,input').forEach((element) => element.addEventListener('change', refresh));
  projection.onchange = () => setProjection(projection.value);
  png.onclick = () => alert('GitHub Pages runs without a server. Use browser screenshot tools, or run the FastAPI backend for Cartopy PNG export.');
  csv.onclick = () => download('statistics.csv', statsCSV(payload));
  play.onclick = animate;
  dark.onclick = () => document.body.classList.toggle('light');
  await refresh();
}

async function refresh() {
  const [year, month] = init.value.split('-');
  const variable = document.querySelector('input[name="var"]:checked').value;
  const query = `/api/verify?init_year=${year}&init_month=${month}&lead=${lead.value}&variable=${variable}`;
  payload = await fetchJsonOrStatic(query, staticVerify);
  ['forecast', 'observed', 'difference'].forEach((id) => drawGrid(id, payload[id], variable, palette.value, id === 'observed' ? opacity.value : 0.85));
  stats.innerHTML = `<h3>${payload.metadata.variable.toUpperCase()} ${payload.metadata.init} → ${payload.metadata.verification}</h3>`
    + (usingStaticMode ? '<p><strong>Static GitHub Pages mode:</strong> showing deterministic sample grids. Run the FastAPI backend or publish precomputed data for live NOAA/ERA5 verification.</p>' : '')
    + metricRows(payload.statistics, payload.metric_explanations);
  drawChart(payload);
}

function download(name, text) {
  const anchor = document.createElement('a');
  anchor.href = URL.createObjectURL(new Blob([text], { type: 'text/csv' }));
  anchor.download = name;
  anchor.click();
}

async function animate() {
  for (let l = 1; l <= 9; l += 1) {
    lead.value = l;
    await refresh();
    await new Promise((resolve) => setTimeout(resolve, 750));
  }
}

initMaps();
loadOptions();
