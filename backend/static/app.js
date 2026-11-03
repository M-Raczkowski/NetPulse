const REFRESH_MS = 15000;
const STALE_AFTER_S = 120;
const GAP_MS = 150000;
const COLORS = ["#2a6fdb", "#e8833a", "#2a9d8f", "#9b5de5", "#d1495b", "#6b7280"];
const DETECTORS = ["threshold", "zscore", "ewma"];

const rangeSelect = document.getElementById("range");
const statusEl = document.getElementById("status");
const charts = {};

const bodyStyle = getComputedStyle(document.body);
Chart.defaults.color = bodyStyle.color;
Chart.defaults.borderColor = bodyStyle.getPropertyValue("--border");
Chart.defaults.font.family = bodyStyle.fontFamily;
Chart.defaults.font.size = 13;
Chart.defaults.font.weight = "normal";

// Draws one thin strip per alert above the plot: lane = detector, colour = agent.
const alertStrips = {
  id: "alertStrips",
  afterDatasetsDraw(chart) {
    const {ctx, chartArea, scales} = chart;
    const {alerts = [], colors = {}} = chart.$strips || {};
    ctx.save();
    for (const alert of alerts) {
      const lane = DETECTORS.indexOf(alert.detector);
      if (lane < 0 || !colors[alert.agent_id]) continue;
      const start = new Date(alert.opened_at).getTime();
      const end = alert.closed_at ? new Date(alert.closed_at).getTime() : Date.now();
      const left = Math.max(scales.x.getPixelForValue(start), chartArea.left);
      const right = Math.min(scales.x.getPixelForValue(end), chartArea.right);
      if (right <= left) continue;
      ctx.fillStyle = colors[alert.agent_id];
      ctx.fillRect(left, chartArea.top - 24 + lane * 7, right - left, 5);
    }
    ctx.restore();
  },
};

async function getJson(path, params = {}) {
  const response = await fetch(`${path}?${new URLSearchParams(params)}`);
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json();
}

function minutesAgo(minutes) {
  return new Date(Date.now() - minutes * 60000).toISOString();
}

function formatDateTime(iso) {
  return iso ? new Date(iso).toLocaleString([], {hour12: false}) : "-";
}

function formatNumber(value, digits = 2) {
  return value === null || value === undefined ? "-" : value.toFixed(digits);
}

function formatThroughput(mbps) {
  if (mbps === null || mbps === undefined) return "-";
  return mbps >= 1000 ? `${(mbps / 1000).toFixed(1)} Gb/s` : `${mbps.toFixed(1)} Mb/s`;
}

// Latest raw measurement for every (agent, target) pair seen in the selected range.
async function loadLatestPerPair(minutes) {
  const rows = await getJson("/measurements", {since: minutesAgo(minutes), limit: 2000});
  const latest = new Map();
  for (const row of rows) {
    const key = `${row.agent_id}|${row.target}`;
    if (!latest.has(key)) latest.set(key, row);  // rows come newest first
  }
  return [...latest.values()].sort((a, b) => a.agent_id.localeCompare(b.agent_id));
}

function renderCards(latest) {
  const container = document.getElementById("cards");
  container.replaceChildren();
  for (const row of latest) {
    const ageS = (Date.now() - new Date(row.timestamp_utc)) / 1000;
    const loss = (row.packets_sent - row.packets_received) * 100 / row.packets_sent;
    const card = document.createElement("div");
    card.className = "card";

    const name = document.createElement("div");
    name.className = "name";
    const dot = document.createElement("span");
    dot.className = ageS > STALE_AFTER_S ? "dot stale" : "dot";
    name.append(dot, row.agent_id);

    const target = document.createElement("div");
    target.className = "target";
    target.textContent = `${row.target} - ${ageS > STALE_AFTER_S ? "no data for " + Math.round(ageS) + " s" : "updated " + Math.round(ageS) + " s ago"}`;

    const list = document.createElement("dl");
    const entries = [
      ["RTT avg", `${formatNumber(row.rtt_avg_ms)} ms`],
      ["Loss", `${formatNumber(loss, 1)} %`],
      ["Jitter", `${formatNumber(row.jitter_ms)} ms`],
      ["Throughput", formatThroughput(row.throughput_mbps)],
    ];
    for (const [label, value] of entries) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      list.append(dt, dd);
    }
    card.append(name, target, list);
    container.append(card);
  }
}

async function loadSeries(latest, minutes) {
  const since = minutesAgo(minutes);
  return Promise.all(latest.map(async (row) => {
    const rows = await getJson("/measurements/aggregates", {agent_id: row.agent_id, target: row.target, since});
    return {label: row.agent_id, rows: rows.reverse()};  // API returns newest first
  }));
}

// Aggregate rows -> {x, y} points; a null point is inserted after a hole so the line breaks there.
function toPoints(rows, field) {
  const points = [];
  let previous = null;
  for (const row of rows) {
    const x = new Date(row.start).getTime();
    if (previous !== null && x - previous > GAP_MS) points.push({x: previous + 60000, y: null});
    points.push({x, y: row[field]});
    previous = x;
  }
  return points;
}

function logTick(value) {
  const exponent = Math.log10(value);
  return Math.abs(exponent - Math.round(exponent)) < 1e-9 ? value : "";
}

function updateChart(canvasId, series, field, {log, unit, metric, alerts, minutes}) {
  const total = series.reduce((sum, s) => sum + s.rows.length, 0);
  const datasets = series.map((s, i) => ({
    label: s.label,
    data: toPoints(s.rows, field),
    borderColor: COLORS[i % COLORS.length],
    backgroundColor: COLORS[i % COLORS.length],
    borderWidth: 1.5,
    pointRadius: total < 120 ? 3 : 0,
    spanGaps: false,
  }));
  const colors = Object.fromEntries(series.map((s, i) => [s.label, COLORS[i % COLORS.length]]));
  const stripAlerts = alerts.filter((a) => a.metric === metric);
  const xRange = {min: Date.now() - minutes * 60000, max: Date.now()};

  let chart = charts[canvasId];
  if (!chart) {
    chart = new Chart(document.getElementById(canvasId), {
      type: "line",
      data: {datasets},
      plugins: [alertStrips],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        layout: {padding: {top: 26}},
        interaction: {mode: "nearest", axis: "x", intersect: false},
        plugins: {legend: {position: "bottom", labels: {usePointStyle: true, boxWidth: 8}}},
        scales: {
          x: {type: "time", time: {tooltipFormat: "dd.MM HH:mm"}, ticks: {maxTicksLimit: 10}},
          y: log
            ? {type: "logarithmic", min: 0.1, title: {display: true, text: unit}, ticks: {callback: logTick}}
            : {beginAtZero: true, title: {display: true, text: unit}},
        },
      },
    });
    charts[canvasId] = chart;
  }
  chart.data.datasets = datasets;
  chart.options.scales.x.min = xRange.min;
  chart.options.scales.x.max = xRange.max;
  chart.$strips = {alerts: stripAlerts, colors};
  chart.update("none");
}

function renderAlerts(containerId, alerts, emptyText) {
  const container = document.getElementById(containerId);
  container.replaceChildren();
  if (alerts.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = emptyText;
    container.append(empty);
    return;
  }
  const table = document.createElement("table");
  const head = table.createTHead().insertRow();
  for (const title of ["Status", "Agent", "Target", "Metric", "Detector", "Value", "Opened", "Closed"]) {
    const th = document.createElement("th");
    th.textContent = title;
    head.append(th);
  }
  const body = table.createTBody();
  for (const alert of alerts) {
    const isOpen = alert.closed_at === null;
    const row = body.insertRow();
    const cells = [
      isOpen ? "open" : "closed",
      alert.agent_id,
      alert.target,
      alert.metric,
      alert.detector,
      formatNumber(alert.value_at_open),
      formatDateTime(alert.opened_at),
      formatDateTime(alert.closed_at),
    ];
    cells.forEach((text, i) => {
      const cell = row.insertCell();
      cell.textContent = text;
      if (i === 0 && isOpen) cell.className = "open";
    });
  }
  container.append(table);
}

async function refresh() {
  const minutes = Number(rangeSelect.value);
  try {
    const latest = await loadLatestPerPair(minutes);
    renderCards(latest);
    const [series, alerts] = await Promise.all([
      loadSeries(latest, minutes),
      getJson("/alerts", {limit: 1000}),  // newest first
    ]);
    updateChart("rtt-chart", series, "rtt_avg_ms",
        {log: true, unit: "ms (log scale)", metric: "rtt_avg_ms", alerts, minutes});
    updateChart("loss-chart", series, "packet_loss_percentage",
        {log: false, unit: "%", metric: "packet_loss_percentage", alerts, minutes});
    renderAlerts("open-alerts", alerts.filter((a) => a.closed_at === null), "No open alerts");
    renderAlerts("recent-alerts", alerts.slice(0, 30), "No alerts yet");
    statusEl.textContent = `updated ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    statusEl.textContent = `error: ${error.message}`;
  }
}

rangeSelect.addEventListener("change", refresh);
refresh();
setInterval(refresh, REFRESH_MS);
