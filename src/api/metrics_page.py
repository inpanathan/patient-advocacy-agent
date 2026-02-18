"""Metrics Explorer page (Grafana-like) — served at GET /dashboard/metrics.

Time-series charts for request traffic, latency, model performance,
and error breakdown. All data fetched from JSON API endpoints.
"""
# ruff: noqa: E501

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.api._dashboard_shared import COLORS, PLOTLY_LAYOUT_DEFAULTS, full_page

router = APIRouter(tags=["dashboard-pages"])

_LAYOUT = json.dumps(PLOTLY_LAYOUT_DEFAULTS)
_C = COLORS


def _build_body() -> str:
    """Build the metrics explorer HTML body."""
    c = _C
    input_style = (
        f"background:{c['surface2']};color:{c['text']};"
        f"border:1px solid {c['border']};border-radius:4px;"
        "padding:6px 10px;font-size:13px;"
    )
    return f"""
<h2 style="margin-bottom:16px;font-size:18px;">Metrics Explorer</h2>

<!-- Controls -->
<div class="card" style="margin-bottom:16px;">
  <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;">
    <div>
      <label style="font-size:11px;color:{c['text_muted']};display:block;">Time Range</label>
      <select id="time-range" style="{input_style}">
        <option value="300">Last 5 min</option>
        <option value="900">Last 15 min</option>
        <option value="3600" selected>Last 1 hour</option>
        <option value="0">All time</option>
      </select>
    </div>
    <div>
      <label style="font-size:11px;color:{c['text_muted']};display:block;">Bucket Size</label>
      <select id="bucket-size" style="{input_style}">
        <option value="10">10s</option>
        <option value="30">30s</option>
        <option value="60" selected>60s</option>
        <option value="300">5 min</option>
      </select>
    </div>
    <div style="display:flex;align-items:flex-end;gap:8px;padding-top:16px;">
      <button id="btn-refresh"
        style="background:{c['accent']};color:white;border:none;border-radius:4px;padding:7px 16px;font-size:13px;cursor:pointer;">
        Refresh
      </button>
      <label style="font-size:12px;display:flex;align-items:center;gap:4px;cursor:pointer;">
        <input type="checkbox" id="auto-refresh" checked> Auto-refresh (10s)
      </label>
    </div>
  </div>
</div>

<!-- Row 1: Request Traffic -->
<div style="margin-bottom:8px;font-size:13px;font-weight:600;color:{c['text_muted']};">
  Request Traffic
</div>
<div class="grid grid-3">
  <div class="card">
    <div class="card-title">Request Rate</div>
    <div id="request-rate-chart" style="height:240px;"></div>
  </div>
  <div class="card">
    <div class="card-title">Requests by Endpoint</div>
    <div id="requests-by-endpoint" style="height:240px;"></div>
  </div>
  <div class="card">
    <div class="card-title">Error Rate</div>
    <div id="error-rate-chart" style="height:240px;"></div>
  </div>
</div>

<!-- Row 2: Latency -->
<div style="margin-top:16px;margin-bottom:8px;font-size:13px;font-weight:600;color:{c['text_muted']};">
  Latency &amp; Performance
</div>
<div class="grid grid-3">
  <div class="card">
    <div class="card-title">Prediction Latency</div>
    <div id="pred-latency-chart" style="height:240px;"></div>
  </div>
  <div class="card">
    <div class="card-title">Retrieval Latency</div>
    <div id="retr-latency-chart" style="height:240px;"></div>
  </div>
  <div class="card">
    <div class="card-title">Response Time by Endpoint</div>
    <div id="response-time-chart" style="height:240px;"></div>
  </div>
</div>

<!-- Row 3: Model & System -->
<div style="margin-top:16px;margin-bottom:8px;font-size:13px;font-weight:600;color:{c['text_muted']};">
  Model &amp; System
</div>
<div class="grid grid-3">
  <div class="card">
    <div class="card-title">Confidence Scores</div>
    <div id="confidence-chart" style="height:240px;"></div>
  </div>
  <div class="card">
    <div class="card-title">Escalation Events</div>
    <div id="escalation-chart" style="height:240px;"></div>
  </div>
  <div class="card">
    <div class="card-title">Error Breakdown</div>
    <div id="error-breakdown-chart" style="height:240px;"></div>
  </div>
</div>
"""


@router.get("/dashboard/metrics", response_class=HTMLResponse)
async def metrics_page() -> str:
    """Render the metrics explorer page."""
    body = _build_body()

    js = f"""
const BASE = '/api/v1/dashboard';
const LAYOUT = {_LAYOUT};
const COLORS = {json.dumps(COLORS)};
let refreshTimer = null;

function getBucket() {{
  return parseInt(document.getElementById('bucket-size').value);
}}

function toTimestamps(buckets) {{
  return buckets.map(b => new Date(b.timestamp * 1000)
    .toLocaleTimeString('en-GB', {{
      hour:'2-digit', minute:'2-digit', second:'2-digit'
    }}));
}}

function emptyMsg(id, msg) {{
  document.getElementById(id).innerHTML =
    '<div style="display:flex;align-items:center;'
    + 'justify-content:center;height:100%;color:'
    + COLORS.text_muted + ';">' + msg + '</div>';
}}

async function loadTimeSeries(metric, chartId, opts) {{
  const bucket = getBucket();
  const d = await fetchJSON(
    BASE + '/time-series?metric=' + metric + '&bucket=' + bucket
  );
  if (!d || !d.buckets || d.buckets.length === 0) {{
    emptyMsg(chartId, 'No data for ' + metric);
    return;
  }}
  const x = toTimestamps(d.buckets);
  const traces = [];

  if (opts.bands) {{
    traces.push({{
      x, y: d.buckets.map(b => b.max),
      type: 'scatter', mode: 'lines',
      line: {{ width: 0 }}, showlegend: false, name: 'max',
    }});
    traces.push({{
      x, y: d.buckets.map(b => b.min),
      type: 'scatter', mode: 'lines',
      fill: 'tonexty', fillcolor: COLORS.accent + '22',
      line: {{ width: 0 }}, showlegend: false, name: 'min',
    }});
  }}

  traces.push({{
    x, y: d.buckets.map(b => b.mean),
    type: 'scatter', mode: 'lines+markers',
    line: {{ color: opts.color || COLORS.accent, width: 2 }},
    marker: {{ size: 4 }}, name: opts.label || metric,
  }});

  Plotly.newPlot(chartId, traces, {{
    ...LAYOUT,
    yaxis: {{ ...LAYOUT.yaxis, title: opts.yTitle || '' }},
    showlegend: false,
  }}, {{ responsive: true, displayModeBar: false }});
}}

async function loadRequestStats() {{
  const d = await fetchJSON(BASE + '/request-stats');
  if (!d) return;

  const eps = Object.entries(d.endpoints)
    .sort((a,b) => b[1].count - a[1].count);

  if (eps.length > 0) {{
    Plotly.newPlot('requests-by-endpoint', [{{
      y: eps.map(e => e[0]),
      x: eps.map(e => e[1].count),
      type: 'bar', orientation: 'h',
      marker: {{ color: COLORS.accent }},
    }}], {{
      ...LAYOUT,
      yaxis: {{ ...LAYOUT.yaxis, automargin: true }},
      xaxis: {{ ...LAYOUT.xaxis, title: 'Requests' }},
    }}, {{ responsive: true, displayModeBar: false }});

    const withLat = eps.filter(
      e => e[1].latency_stats && e[1].latency_stats.count > 0
    );
    if (withLat.length > 0) {{
      Plotly.newPlot('response-time-chart', [
        {{
          y: withLat.map(e => e[0]),
          x: withLat.map(e => e[1].latency_stats.p50),
          type: 'bar', orientation: 'h', name: 'p50',
          marker: {{ color: COLORS.success }},
        }},
        {{
          y: withLat.map(e => e[0]),
          x: withLat.map(
            e => e[1].latency_stats.p95 - e[1].latency_stats.p50
          ),
          type: 'bar', orientation: 'h', name: 'p95',
          marker: {{ color: COLORS.warning }},
        }},
      ], {{
        ...LAYOUT, barmode: 'stack',
        yaxis: {{ ...LAYOUT.yaxis, automargin: true }},
        xaxis: {{ ...LAYOUT.xaxis, title: 'Latency (ms)' }},
        showlegend: true,
        legend: {{ font: {{ size: 10 }} }},
      }}, {{ responsive: true, displayModeBar: false }});
    }} else {{
      emptyMsg('response-time-chart', 'No latency data');
    }}
  }} else {{
    emptyMsg('requests-by-endpoint', 'No request data');
    emptyMsg('response-time-chart', 'No request data');
  }}

  const errEps = eps.filter(e => e[1].errors > 0);
  if (errEps.length > 0) {{
    Plotly.newPlot('error-breakdown-chart', [{{
      labels: errEps.map(e => e[0]),
      values: errEps.map(e => e[1].errors),
      type: 'pie', hole: 0.4,
      marker: {{ colors: [
        COLORS.error, COLORS.warning,
        COLORS.accent, COLORS.info,
      ] }},
    }}], {{
      ...LAYOUT, showlegend: true,
      legend: {{ font: {{ size: 10 }} }},
    }}, {{ responsive: true, displayModeBar: false }});
  }} else {{
    emptyMsg('error-breakdown-chart', 'No errors recorded');
  }}
}}

async function refresh() {{
  await Promise.all([
    loadTimeSeries('request_latency_ms', 'request-rate-chart', {{
      color: COLORS.info, yTitle: 'Requests/bucket',
      label: 'Request Count',
    }}),
    loadRequestStats(),
    loadTimeSeries('request_latency_ms', 'error-rate-chart', {{
      color: COLORS.error, yTitle: 'ms',
      label: 'Request Latency',
    }}),
    loadTimeSeries('prediction_latency_ms', 'pred-latency-chart', {{
      color: COLORS.warning, yTitle: 'ms',
      label: 'Prediction Latency', bands: true,
    }}),
    loadTimeSeries('retrieval_latency_ms', 'retr-latency-chart', {{
      color: COLORS.accent, yTitle: 'ms',
      label: 'Retrieval Latency', bands: true,
    }}),
    loadTimeSeries('prediction_confidence', 'confidence-chart', {{
      color: COLORS.success, yTitle: 'Confidence',
      label: 'Confidence',
    }}),
  ]);

  const bucket = getBucket();
  const escD = await fetchJSON(
    BASE + '/time-series?metric=prediction_latency_ms&bucket=' + bucket
  );
  if (escD && escD.buckets && escD.buckets.length > 0) {{
    const x = toTimestamps(escD.buckets);
    Plotly.newPlot('escalation-chart', [{{
      x, y: escD.buckets.map(b => b.count),
      type: 'scatter', mode: 'lines+markers',
      line: {{ color: COLORS.error, width: 2 }},
      marker: {{ size: 5 }}, name: 'Events/bucket',
    }}], {{
      ...LAYOUT,
      yaxis: {{ ...LAYOUT.yaxis, title: 'Count' }},
    }}, {{ responsive: true, displayModeBar: false }});
  }} else {{
    emptyMsg('escalation-chart', 'No escalation data');
  }}
}}

function setupAutoRefresh() {{
  const cb = document.getElementById('auto-refresh');
  if (refreshTimer) clearInterval(refreshTimer);
  if (cb.checked) {{
    refreshTimer = setInterval(refresh, 10000);
    document.getElementById('refresh-indicator').textContent = 'Live';
  }} else {{
    document.getElementById('refresh-indicator').textContent =
      'Paused';
  }}
}}

document.getElementById('auto-refresh').addEventListener(
  'change', setupAutoRefresh
);
document.getElementById('btn-refresh').addEventListener(
  'click', refresh
);
document.getElementById('time-range').addEventListener(
  'change', refresh
);
document.getElementById('bucket-size').addEventListener(
  'change', refresh
);

refresh();
setupAutoRefresh();
"""
    return full_page("Metrics", "metrics", body, js)
