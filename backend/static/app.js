const REFRESH_MS = 15000;
const STALE_AFTER_S = 120;
const GAP_MS = 150000;
const COLORS = ["#2a6fdb", "#e8833a", "#2a9d8f", "#9b5de5", "#d1495b", "#6b7280"];
const DETECTORS = ["threshold", "zscore", "ewma"];
const DETECTOR_COLORS = {threshold: "#e8833a", zscore: "#9b5de5", ewma: "#2a9d8f"};
const METRIC_NAMES = {rtt_avg_ms: "RTT", packet_loss_percentage: "loss"};
const Y_AXIS_WIDTH = 48;
const TIMELINE_ROW_PX = 26;

const FAULT_COLOR = "rgba(214, 69, 69, 0.18)";

const rangeSelect = document.getElementById("range");
const logCheckbox = document.getElementById("log-scale");
const fromInput = document.getElementById("from");
const toInput = document.getElementById("to");
const experimentSelect = document.getElementById("experiment");
const statusEl = document.getElementById("status");
const charts = {};
let timelineChart = null;
let experiments = [];
let selectedExperiment = null;
let fixedWindow = readWindowFromUrl();

const bodyStyle = getComputedStyle(document.body);
Chart.defaults.color = bodyStyle.color;
Chart.defaults.borderColor = bodyStyle.getPropertyValue("--border");
Chart.defaults.font.family = bodyStyle.fontFamily;
Chart.defaults.font.size = 13;
Chart.defaults.font.weight = "normal";


Chart.register({
    id: "faultBands",
    beforeDatasetsDraw(chart) {
        const {ctx, chartArea, scales} = chart;
        const plotHeight = chartArea.bottom - chartArea.top;
        const draw = (bands, top, height) => {
            for (const band of bands) {
                const left = Math.max(scales.x.getPixelForValue(band.start), chartArea.left);
                const right = Math.min(scales.x.getPixelForValue(band.end), chartArea.right);
                if (right > left) ctx.fillRect(left, top, right - left, height);
            }
        };
        ctx.save();
        ctx.fillStyle = FAULT_COLOR;
        if (chart.$faults) draw(chart.$faults, chartArea.top, plotHeight);
        if (chart.$faultRows) {
            const rowHeight = plotHeight / chart.$faultRows.length;
            chart.$faultRows.forEach((bands, i) => draw(bands, chartArea.top + i * rowHeight, rowHeight));
        }
        ctx.restore();
    },
});

async function getJson(path, params = {}) {
    const response = await fetch(`${path}?${new URLSearchParams(params)}`);
    if (!response.ok) throw new Error(`${path} returned ${response.status}`);
    return response.json();
}

function readWindowFromUrl() {
    const params = new URLSearchParams(location.search);
    const from = new Date(params.get("since")).getTime();
    const to = new Date(params.get("until")).getTime();
    return from < to ? {from, to} : null;
}

function currentWindow() {
    if (fixedWindow) return fixedWindow;
    const to = Date.now();
    return {from: to - Number(rangeSelect.value) * 60000, to};
}


function toLocalInput(ms) {
    return new Date(ms - new Date(ms).getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function syncControls() {
    rangeSelect.disabled = fixedWindow !== null;
    fromInput.value = fixedWindow ? toLocalInput(fixedWindow.from) : "";
    toInput.value = fixedWindow ? toLocalInput(fixedWindow.to) : "";
    experimentSelect.value = selectedExperiment ? selectedExperiment.name : "";
}


function setFixedWindow(window, experiment = null) {
    fixedWindow = window;
    selectedExperiment = experiment;
    const url = new URL(location.href);
    if (experiment) {
        url.search = new URLSearchParams({experiment: experiment.name});
    } else if (window) {
        url.search = new URLSearchParams({
            since: new Date(window.from).toISOString(),
            until: new Date(window.to).toISOString()
        });
    } else {
        url.search = "";
    }
    history.replaceState(null, "", url);
    syncControls();
    refresh();
}

function experimentWindow(experiment) {
    return {
        from: new Date(experiment.started_utc).getTime(),
        to: experiment.finished_utc ? new Date(experiment.finished_utc).getTime() : Date.now(),
    };
}


function faultWindows(experiment, agent) {
    const starts = new Map();
    const bands = [];
    for (const event of experiment.events.filter((e) => e.agent === agent)) {
        const key = `${event.scenario}|${event.repeat}`;
        if (event.event === "inject_start") starts.set(key, new Date(event.ts_utc).getTime());
        if (event.event === "inject_end" && starts.has(key)) {
            bands.push({start: starts.get(key), end: new Date(event.ts_utc).getTime()});
            starts.delete(key);
        }
    }
    for (const start of starts.values()) bands.push({start, end: Date.now()});
    return bands;
}

async function loadExperiments() {
    try {
        experiments = await getJson("/experiments");
    } catch (error) {
        experiments = [];
    }
    for (const experiment of experiments) {
        const option = document.createElement("option");
        option.value = experiment.name;
        option.textContent = `${new Date(experiment.started_utc).toLocaleString([], {hour12: false})} - ${experiment.scenarios.join(", ")} x${experiment.repeats * experiment.agents.length}`;
        experimentSelect.append(option);
    }
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


async function loadLatestPerPair(window) {
    const rows = await getJson("/measurements", {
        since: new Date(window.from).toISOString(),
        until: new Date(window.to).toISOString(),
        limit: 2000,
    });
    const latest = new Map();
    for (const row of rows) {
        const key = `${row.agent_id}|${row.target}`;
        if (!latest.has(key)) latest.set(key, row);
    }
    return [...latest.values()].sort((a, b) => a.agent_id.localeCompare(b.agent_id));
}

function renderCards(latest) {
    const container = document.getElementById("cards");
    container.replaceChildren();
    for (const row of latest) {
        const ageS = (Date.now() - new Date(row.timestamp_utc)) / 1000;
        const stale = !fixedWindow && ageS > STALE_AFTER_S;
        const loss = (row.packets_sent - row.packets_received) * 100 / row.packets_sent;
        const card = document.createElement("div");
        card.className = "card";

        const name = document.createElement("div");
        name.className = "name";
        const dot = document.createElement("span");
        dot.className = stale ? "dot stale" : "dot";
        name.append(dot, row.agent_id);

        const target = document.createElement("div");
        target.className = "target";
        if (fixedWindow) {
            target.textContent = `${row.target} - last sample ${formatDateTime(row.timestamp_utc)}`;
        } else {
            target.textContent = `${row.target} - ${stale ? "no data for " + Math.round(ageS) + " s" : "updated " + Math.round(ageS) + " s ago"}`;
        }

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

async function loadSeries(latest, window) {
    const since = new Date(window.from).toISOString();
    const until = new Date(window.to).toISOString();
    return Promise.all(latest.map(async (row) => {
        const rows = await getJson("/measurements/aggregates", {
            agent_id: row.agent_id,
            target: row.target,
            since,
            until
        });
        return {label: row.agent_id, rows: rows.reverse()};
    }));
}


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

function buildRow(containerId, label, index, isLast, unit) {
    const row = document.createElement("div");
    row.className = "chart-row";
    const name = document.createElement("div");
    name.className = "agent";
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.style.background = COLORS[index % COLORS.length];
    const unitEl = document.createElement("div");
    unitEl.className = "unit";
    unitEl.textContent = unit;
    name.append(swatch, label, unitEl);
    const box = document.createElement("div");
    box.className = "chart-box";
    box.style.height = isLast ? "250px" : "200px";
    const canvas = document.createElement("canvas");
    canvas.id = `${containerId}-${label}`;
    box.append(canvas);
    row.append(name, box);
    return row;
}

function createChart(canvasId, color, isLast, {log}) {
    return new Chart(document.getElementById(canvasId), {
        type: "line",
        data: {
            datasets: [{
                borderColor: color,
                backgroundColor: color,
                borderWidth: 1.5,
                spanGaps: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: {mode: "nearest", axis: "x", intersect: false},
            plugins: {legend: {display: false}},
            elements: {point: {radius: 0, hoverRadius: 4}},
            scales: {
                x: {type: "time", time: {tooltipFormat: "dd.MM HH:mm"}, ticks: {display: isLast, maxTicksLimit: 10}},
                y: {
                    ...(log ? {type: "logarithmic", min: 0.1, ticks: {callback: logTick}} : {beginAtZero: true}),
                    afterFit(scale) {
                        scale.width = Y_AXIS_WIDTH;
                    },
                },
            },
        },
    });
}

function updateCharts(containerId, series, field, {log, unit, metric, window}) {
    const container = document.getElementById(containerId);
    const layoutKey = `${series.map((s) => s.label).join(",")}|${log}`;
    if (container.dataset.layout !== layoutKey) {
        for (const id of Object.keys(charts)) {
            if (id.startsWith(`${containerId}-`)) {
                charts[id].destroy();
                delete charts[id];
            }
        }
        container.replaceChildren();
        container.dataset.layout = layoutKey;
        series.forEach((s, i) => container.append(buildRow(containerId, s.label, i, i === series.length - 1, unit)));
        series.forEach((s, i) => {
            const id = `${containerId}-${s.label}`;
            charts[id] = createChart(id, COLORS[i % COLORS.length], i === series.length - 1, {log});
        });
    }

    const values = series.flatMap((s) => s.rows.map((r) => r[field])).filter((v) => v !== null);
    const top = Math.max(0, ...values);
    const step = metric === "packet_loss_percentage" ? 5 : 10;
    const yMax = log ? Math.max(top, 1) * 1.3 : Math.max(Math.ceil(top / step) * step, step);
    const total = values.length;

    for (const s of series) {
        const chart = charts[`${containerId}-${s.label}`];
        chart.data.datasets[0].data = toPoints(s.rows, field);
        chart.options.elements.point.radius = total < 120 ? 3 : 0;
        chart.options.scales.x.min = window.from;
        chart.options.scales.x.max = window.to;
        chart.options.scales.y.max = yMax;
        chart.$faults = selectedExperiment ? faultWindows(selectedExperiment, s.label) : [];
        chart.update("none");
    }
}

function alertRowKey(alert) {
    return `${alert.agent_id} · ${METRIC_NAMES[alert.metric] ?? alert.metric}`;
}

function alertEnd(alert) {
    return alert.closed_at ? new Date(alert.closed_at).getTime() : Date.now();
}

function overlapsWindow(alert, window) {
    return new Date(alert.opened_at).getTime() <= window.to && alertEnd(alert) >= window.from;
}

function updateTimeline(alerts, agents, window) {
    const visible = alerts
        .filter((a) => agents.includes(a.agent_id) && overlapsWindow(a, window))
        .sort((a, b) => alertRowKey(a).localeCompare(alertRowKey(b))
            || DETECTORS.indexOf(a.detector) - DETECTORS.indexOf(b.detector));

    const box = document.getElementById("timeline-box");
    const empty = document.getElementById("timeline-empty");
    box.hidden = visible.length === 0;
    empty.hidden = visible.length > 0;
    if (visible.length === 0) return;

    const rowOf = (a) => `${alertRowKey(a)} · ${a.detector}`;
    const rows = [...new Set(visible.map(rowOf))];
    box.style.height = `${rows.length * TIMELINE_ROW_PX + 60}px`;

    const dataset = {
        data: visible.map((a) => ({
            x: [Math.max(new Date(a.opened_at).getTime(), window.from), Math.min(alertEnd(a), window.to)],
            y: rowOf(a),
        })),
        backgroundColor: visible.map((a) => DETECTOR_COLORS[a.detector]),
        minBarLength: 3,
        barPercentage: 0.7,
        categoryPercentage: 0.9,
    };
    if (!timelineChart) {
        timelineChart = new Chart(document.getElementById("timeline-chart"), {
            type: "bar",
            data: {labels: rows, datasets: [dataset]},
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: {
                    legend: {display: false},
                    tooltip: {
                        callbacks: {
                            title: (items) => items[0].raw.y,
                            label: (item) => {
                                const alert = timelineChart.$visible[item.dataIndex];
                                return `opened ${formatDateTime(alert.opened_at)}, ${alert.closed_at ? "closed " + formatDateTime(alert.closed_at) : "still open"}`;
                            },
                        },
                    },
                },
                scales: {
                    x: {type: "time", time: {tooltipFormat: "dd.MM HH:mm"}, ticks: {maxTicksLimit: 10}},
                    y: {type: "category", labels: rows},
                },
            },
        });
    }
    timelineChart.$visible = visible;
    timelineChart.data.labels = rows;
    timelineChart.data.datasets[0] = dataset;
    timelineChart.options.scales.y.labels = rows;
    timelineChart.options.scales.x.min = window.from;
    timelineChart.options.scales.x.max = window.to;
    timelineChart.$faultRows = selectedExperiment ? rows.map((row) => faultWindows(selectedExperiment, row.split(" · ")[0])) : null;
    timelineChart.resize();
    timelineChart.update("none");
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
    const window = currentWindow();
    try {
        const latest = await loadLatestPerPair(window);
        renderCards(latest);
        const [series, alerts] = await Promise.all([
            loadSeries(latest, window),
            getJson("/alerts", {limit: 1000}),
        ]);
        updateCharts("rtt-charts", series, "rtt_avg_ms",
            {log: logCheckbox.checked, unit: logCheckbox.checked ? "ms (log)" : "ms", metric: "rtt_avg_ms", window});
        updateCharts("loss-charts", series, "packet_loss_percentage",
            {log: false, unit: "%", metric: "packet_loss_percentage", window});
        updateTimeline(alerts, series.map((s) => s.label), window);
        renderAlerts("open-alerts", alerts.filter((a) => a.closed_at === null), "No open alerts");
        renderAlerts("recent-alerts", alerts.filter((a) => overlapsWindow(a, window)).slice(0, 30),
            fixedWindow ? "No alerts in this window" : "No alerts yet");
        statusEl.textContent = fixedWindow ? "fixed window" : `updated ${new Date().toLocaleTimeString()}`;
    } catch (error) {
        statusEl.textContent = `error: ${error.message}`;
    }
}

document.getElementById("apply-window").addEventListener("click", () => {
    const from = new Date(fromInput.value).getTime();
    const to = new Date(toInput.value).getTime();
    if (!(from < to)) {
        statusEl.textContent = "error: set From earlier than To";
        return;
    }
    setFixedWindow({from, to});
});
document.getElementById("live").addEventListener("click", () => setFixedWindow(null));
experimentSelect.addEventListener("change", () => {
    const experiment = experiments.find((e) => e.name === experimentSelect.value);
    setFixedWindow(experiment ? experimentWindow(experiment) : null, experiment ?? null);
});
rangeSelect.addEventListener("change", refresh);
logCheckbox.addEventListener("change", refresh);

async function start() {
    await loadExperiments();
    const name = new URLSearchParams(location.search).get("experiment");
    const experiment = experiments.find((e) => e.name === name);
    if (experiment) {
        fixedWindow = experimentWindow(experiment);
        selectedExperiment = experiment;
    }
    syncControls();
    refresh();
    setInterval(() => {
        if (!fixedWindow) refresh();
    }, REFRESH_MS);
}

start();
