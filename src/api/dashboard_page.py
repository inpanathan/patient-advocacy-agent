"""Overview Dashboard page — served at GET /dashboard.

Displays health, performance, vector space, safety, and bias metrics
with interactive Plotly charts. All data fetched from JSON API endpoints.
"""
# ruff: noqa: E501

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.api._dashboard_shared import COLORS, PLOTLY_LAYOUT_DEFAULTS, full_page

router = APIRouter(tags=["dashboard-pages"])

_LAYOUT = json.dumps(PLOTLY_LAYOUT_DEFAULTS)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_overview() -> str:
    """Render the overview dashboard page."""
    body = """
<h2 style="margin-bottom:16px;font-size:18px;">System Overview</h2>

<!-- Row 1: Health + Alerts -->
<div class="grid grid-2">
  <div class="card" id="health-card">
    <div class="card-title">Health Overview</div>
    <div id="health-content">Loading...</div>
  </div>
  <div class="card" id="alerts-card">
    <div class="card-title">Active Alerts</div>
    <div id="alerts-content">Loading...</div>
  </div>
</div>

<!-- Row 2: Latency + Confidence -->
<div class="grid grid-2" style="margin-top:16px;">
  <div class="card">
    <div class="card-title">Prediction Latency (ms)</div>
    <div id="latency-chart" style="height:260px;"></div>
  </div>
  <div class="card">
    <div class="card-title">Confidence Distribution</div>
    <div id="confidence-chart" style="height:260px;"></div>
  </div>
</div>

<!-- Row 3: ICD codes (full width) -->
<div class="grid grid-full" style="margin-top:16px;">
  <div class="card">
    <div class="card-title">ICD Code Distribution</div>
    <div id="icd-chart" style="height:280px;"></div>
  </div>
</div>

<!-- Row 4: Vector space (full width) -->
<div class="grid grid-full" style="margin-top:16px;">
  <div class="card">
    <div class="card-title" id="vector-title">Vector Space (PCA 2D Projection)</div>
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px;flex-wrap:wrap;">
      <label style="font-size:12px;display:flex;align-items:center;gap:6px;">
        Points: <span id="points-label" style="min-width:36px;font-weight:600;">500</span>
        <input type="range" id="points-slider" min="10" max="5000" value="500" step="10" style="width:160px;">
      </label>
      <label style="font-size:12px;display:flex;align-items:center;gap:6px;">
        Method:
        <select id="method-select" style="padding:3px 6px;border-radius:4px;border:1px solid #555;background:#1e1e2e;color:#cdd6f4;font-size:12px;">
          <option value="pca" selected>PCA</option>
          <option value="tsne">t-SNE</option>
          <option value="umap">UMAP</option>
        </select>
      </label>
      <label style="font-size:12px;display:flex;align-items:center;gap:6px;">
        Case overlay:
        <input type="text" id="case-id-input" placeholder="Case UUID" style="padding:3px 6px;border-radius:4px;border:1px solid #555;background:#1e1e2e;color:#cdd6f4;font-size:12px;width:260px;">
        <button id="case-overlay-btn" style="padding:3px 10px;border-radius:4px;border:1px solid #555;background:#313244;color:#cdd6f4;font-size:12px;cursor:pointer;">Show</button>
        <button id="case-clear-btn" style="padding:3px 10px;border-radius:4px;border:1px solid #555;background:#313244;color:#cdd6f4;font-size:12px;cursor:pointer;display:none;">Clear</button>
      </label>
    </div>
    <div id="vector-chart" style="height:400px;"></div>
  </div>
</div>

<!-- Row 5: Safety + Bias -->
<div class="grid grid-2" style="margin-top:16px;">
  <div class="card">
    <div class="card-title">Safety Compliance</div>
    <div id="safety-content">Loading...</div>
    <div id="safety-chart" style="height:220px;margin-top:12px;"></div>
  </div>
  <div class="card">
    <div class="card-title">Bias by Fitzpatrick Type</div>
    <div id="bias-fitz-chart" style="height:300px;"></div>
  </div>
</div>

<!-- Row 6: Bias by language + Audit -->
<div class="grid grid-2" style="margin-top:16px;">
  <div class="card">
    <div class="card-title">Bias by Language</div>
    <div id="bias-lang-chart" style="height:300px;"></div>
  </div>
  <div class="card">
    <div class="card-title">Recent Audit Records</div>
    <div id="audit-content" style="max-height:300px;overflow-y:auto;">Loading...</div>
  </div>
</div>
"""

    js = f"""
const BASE = '/api/v1/dashboard';
const LAYOUT = {_LAYOUT};
const COLORS = {json.dumps(COLORS)};

async function loadHealth() {{
  const d = await fetchJSON(BASE + '/health-overview');
  if (!d) return;
  document.getElementById('health-content').innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
      <div><div class="stat-value">${{d.active_sessions}}</div><div class="stat-label">Active Sessions</div></div>
      <div><div class="stat-value">${{d.scin_records}}</div><div class="stat-label">SCIN Records</div></div>
      <div><div class="stat-value">${{d.predictions_total}}</div><div class="stat-label">Predictions</div></div>
      <div><div class="stat-value">${{d.escalations_total}}</div><div class="stat-label">Escalations</div></div>
      <div><div class="stat-value">${{d.retrievals_total}}</div><div class="stat-label">Retrievals</div></div>
      <div><div class="stat-value">${{fmtDuration(d.uptime_seconds)}}</div><div class="stat-label">Uptime</div></div>
    </div>
    <div style="margin-top:12px;">
      <span class="badge badge-ok">${{d.status}}</span>
      <span class="badge badge-info">${{d.env}}</span>
      <span class="badge badge-debug">${{d.model_backend}}</span>
    </div>`;
}}

async function loadAlerts() {{
  const d = await fetchJSON(BASE + '/alerts');
  if (!d) return;
  const el = document.getElementById('alerts-content');
  if (d.length === 0) {{
    el.innerHTML = '<div style="color:' + COLORS.success + ';font-weight:600;">No active alerts</div>';
    return;
  }}
  el.innerHTML = d.map(a => `
    <div style="padding:8px;margin-bottom:6px;background:${{COLORS.surface2}};border-radius:6px;border-left:3px solid ${{
      a.severity === 'critical' ? COLORS.error : a.severity === 'warning' ? COLORS.warning : COLORS.info
    }};">
      <div style="font-weight:600;font-size:13px;">${{escapeHtml(a.name)}}</div>
      <div style="font-size:12px;color:${{COLORS.text_muted}};">${{escapeHtml(a.description)}}</div>
      <div style="font-size:11px;margin-top:4px;">
        <span class="badge badge-${{a.severity === 'critical' ? 'error' : a.severity === 'warning' ? 'warn' : 'info'}}">${{a.severity}}</span>
        Value: ${{a.actual_value}} (threshold: ${{a.threshold}})
      </div>
    </div>
  `).join('');
}}

async function loadPerformance() {{
  const d = await fetchJSON(BASE + '/performance');
  if (!d) return;

  // Latency bar chart
  const lat = d.prediction_latency;
  Plotly.newPlot('latency-chart', [{{
    x: ['p50', 'p95', 'p99', 'mean'],
    y: [lat.p50, lat.p95, lat.p99, lat.mean],
    type: 'bar',
    marker: {{ color: [COLORS.success, COLORS.warning, COLORS.error, COLORS.info] }}
  }}], {{...LAYOUT, title: ''}}, {{responsive: true, displayModeBar: false}});

  // Confidence histogram
  if (d.confidence_values.length > 0) {{
    Plotly.newPlot('confidence-chart', [{{
      x: d.confidence_values, type: 'histogram',
      marker: {{ color: COLORS.accent }}, nbinsx: 20
    }}], {{...LAYOUT, xaxis: {{...LAYOUT.xaxis, title: 'Confidence'}}, yaxis: {{...LAYOUT.yaxis, title: 'Count'}}}},
    {{responsive: true, displayModeBar: false}});
  }} else {{
    document.getElementById('confidence-chart').innerHTML = '<div style="text-align:center;padding:80px 0;color:' + COLORS.text_muted + ';">No predictions yet</div>';
  }}

  // ICD codes
  const codes = Object.entries(d.icd_code_counts).sort((a,b) => b[1] - a[1]);
  if (codes.length > 0) {{
    Plotly.newPlot('icd-chart', [{{
      x: codes.map(c => c[0]), y: codes.map(c => c[1]),
      type: 'bar', marker: {{ color: COLORS.accent }}
    }}], {{...LAYOUT, xaxis: {{...LAYOUT.xaxis, title: 'ICD Code'}}, yaxis: {{...LAYOUT.yaxis, title: 'Count'}}}},
    {{responsive: true, displayModeBar: false}});
  }} else {{
    document.getElementById('icd-chart').innerHTML = '<div style="text-align:center;padding:80px 0;color:' + COLORS.text_muted + ';">No ICD codes recorded</div>';
  }}
}}

async function loadVectorSpace() {{
  const slider = document.getElementById('points-slider');
  const methodSel = document.getElementById('method-select');
  const maxPts = slider ? slider.value : 500;
  const method = methodSel ? methodSel.value : 'pca';
  const d = await fetchJSON(BASE + `/vector-space?max_points=${{maxPts}}&method=${{method}}`);
  if (!d || d.points.length === 0) {{
    document.getElementById('vector-chart').innerHTML = '<div style="text-align:center;padding:120px 0;color:' + COLORS.text_muted + ';">No embeddings indexed</div>';
    return;
  }}
  const usedMethod = (d.method || method).toUpperCase();
  document.getElementById('vector-title').textContent = `Vector Space (${{usedMethod}} 2D Projection)`;
  // Group by diagnosis
  const groups = {{}};
  d.points.forEach(p => {{
    const key = p.diagnosis || 'Unknown';
    if (!groups[key]) groups[key] = {{x:[], y:[], text:[], icd:[]}};
    groups[key].x.push(p.x);
    groups[key].y.push(p.y);
    groups[key].text.push(`${{p.diagnosis}} (${{p.icd_code}})\\nFitzpatrick: ${{p.fitzpatrick_type}}`);
    groups[key].icd.push(p.icd_code || '');
  }});
  const traces = Object.entries(groups).map(([name, g]) => ({{
    x: g.x, y: g.y, text: g.icd, name: name,
    mode: 'markers+text', type: 'scatter',
    marker: {{ size: 6, opacity: 0.7 }},
    textposition: 'top center',
    textfont: {{ size: 8, color: COLORS.text_muted }},
    hovertext: g.text,
    hovertemplate: '%{{hovertext}}<extra></extra>'
  }}));
  Plotly.newPlot('vector-chart', traces,
    {{...LAYOUT, title: `${{d.sampled}} of ${{d.total_embeddings}} embeddings`, showlegend: true,
      legend: {{font: {{size: 10}}, bgcolor: 'rgba(0,0,0,0)'}}}},
    {{responsive: true, displayModeBar: false}});
}}

async function loadCaseOverlay() {{
  const caseIdInput = document.getElementById('case-id-input');
  const caseId = caseIdInput ? caseIdInput.value.trim() : '';
  if (!caseId) return;
  const slider = document.getElementById('points-slider');
  const methodSel = document.getElementById('method-select');
  const maxPts = slider ? slider.value : 500;
  const method = methodSel ? methodSel.value : 'pca';
  const d = await fetchJSON(BASE + `/case-overlay?case_id=${{encodeURIComponent(caseId)}}&method=${{method}}&max_points=${{maxPts}}`);
  if (!d || d.error) {{
    alert(d && d.error ? d.error : 'Failed to load case overlay');
    return;
  }}
  if (d.points.length === 0) return;
  const usedMethod = (d.method || method).toUpperCase();
  document.getElementById('vector-title').textContent = `Vector Space (${{usedMethod}} 2D Projection) — Case Overlay`;
  // Split reference vs case points
  const refGroups = {{}};
  const casePts = {{x:[], y:[], text:[], icd:[]}};
  d.points.forEach(p => {{
    if (p.is_case) {{
      casePts.x.push(p.x);
      casePts.y.push(p.y);
      casePts.text.push(`CASE: ${{p.diagnosis}} (${{p.icd_code}})`);
      casePts.icd.push(p.icd_code || 'CASE');
    }} else {{
      const key = p.diagnosis || 'Unknown';
      if (!refGroups[key]) refGroups[key] = {{x:[], y:[], text:[], icd:[]}};
      refGroups[key].x.push(p.x);
      refGroups[key].y.push(p.y);
      refGroups[key].text.push(`${{p.diagnosis}} (${{p.icd_code}})\\nFitzpatrick: ${{p.fitzpatrick_type}}`);
      refGroups[key].icd.push(p.icd_code || '');
    }}
  }});
  const traces = Object.entries(refGroups).map(([name, g]) => ({{
    x: g.x, y: g.y, text: g.icd, name: name,
    mode: 'markers+text', type: 'scatter',
    marker: {{ size: 6, opacity: 0.5 }},
    textposition: 'top center',
    textfont: {{ size: 8, color: COLORS.text_muted }},
    hovertext: g.text,
    hovertemplate: '%{{hovertext}}<extra></extra>'
  }}));
  // Add case overlay as star markers
  if (casePts.x.length > 0) {{
    traces.push({{
      x: casePts.x, y: casePts.y, text: casePts.icd,
      name: 'Case (overlay)',
      mode: 'markers+text', type: 'scatter',
      marker: {{ size: 16, symbol: 'star', color: '#f38ba8', line: {{ width: 2, color: '#fff' }} }},
      textposition: 'top center',
      textfont: {{ size: 10, color: '#f38ba8' }},
      hovertext: casePts.text,
      hovertemplate: '%{{hovertext}}<extra></extra>'
    }});
  }}
  Plotly.newPlot('vector-chart', traces,
    {{...LAYOUT, title: `${{d.sampled}} of ${{d.total_embeddings}} embeddings (case overlaid)`, showlegend: true,
      legend: {{font: {{size: 10}}, bgcolor: 'rgba(0,0,0,0)'}}}},
    {{responsive: true, displayModeBar: false}});
  document.getElementById('case-clear-btn').style.display = 'inline';
}}

async function loadSafety() {{
  const d = await fetchJSON(BASE + '/safety');
  if (!d) return;
  const rateColor = d.pass_rate >= 0.95 ? COLORS.success : d.pass_rate >= 0.8 ? COLORS.warning : COLORS.error;
  document.getElementById('safety-content').innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
      <div><div class="stat-value" style="color:${{rateColor}}">${{(d.pass_rate * 100).toFixed(1)}}%</div><div class="stat-label">Pass Rate</div></div>
      <div><div class="stat-value">${{d.total_checked}}</div><div class="stat-label">Total Checked</div></div>
      <div><div class="stat-value">${{d.escalations_total}}</div><div class="stat-label">Escalations</div></div>
    </div>`;

  // Violations pie chart
  const viol = Object.entries(d.violations_by_type);
  if (viol.length > 0) {{
    Plotly.newPlot('safety-chart', [{{
      labels: viol.map(v => v[0]), values: viol.map(v => v[1]),
      type: 'pie', hole: 0.4,
      marker: {{ colors: [COLORS.error, COLORS.warning, COLORS.info, COLORS.accent] }}
    }}], {{...LAYOUT, showlegend: true, legend: {{font: {{size: 10}}}}}},
    {{responsive: true, displayModeBar: false}});
  }} else {{
    document.getElementById('safety-chart').innerHTML = '<div style="text-align:center;padding:40px 0;color:' + COLORS.success + ';">No violations</div>';
  }}
}}

async function loadBias() {{
  const d = await fetchJSON(BASE + '/bias');
  if (!d) return;

  // Fitzpatrick chart
  const fitz = Object.entries(d.by_fitzpatrick);
  if (fitz.length > 0) {{
    Plotly.newPlot('bias-fitz-chart', [{{
      x: fitz.map(f => f[0]),
      y: fitz.map(f => f[1].mean_confidence),
      type: 'bar', name: 'Mean Confidence',
      marker: {{ color: COLORS.accent }},
      error_y: {{
        type: 'data', symmetric: false,
        array: fitz.map(f => f[1].max_confidence - f[1].mean_confidence),
        arrayminus: fitz.map(f => f[1].mean_confidence - f[1].min_confidence),
      }}
    }}], {{...LAYOUT, yaxis: {{...LAYOUT.yaxis, title: 'Confidence', range: [0, 1]}}}},
    {{responsive: true, displayModeBar: false}});
  }} else {{
    document.getElementById('bias-fitz-chart').innerHTML = '<div style="text-align:center;padding:80px 0;color:' + COLORS.text_muted + ';">No bias data</div>';
  }}

  // Language chart
  const langs = Object.entries(d.by_language);
  if (langs.length > 0) {{
    Plotly.newPlot('bias-lang-chart', [{{
      x: langs.map(l => l[0]),
      y: langs.map(l => l[1].mean_confidence),
      type: 'bar', name: 'Mean Confidence',
      marker: {{ color: COLORS.info }},
      text: langs.map(l => `n=${{l[1].count}}`),
      textposition: 'outside'
    }}], {{...LAYOUT, yaxis: {{...LAYOUT.yaxis, title: 'Confidence', range: [0, 1]}}}},
    {{responsive: true, displayModeBar: false}});
  }} else {{
    document.getElementById('bias-lang-chart').innerHTML = '<div style="text-align:center;padding:80px 0;color:' + COLORS.text_muted + ';">No language data</div>';
  }}
}}

async function loadAudit() {{
  const d = await fetchJSON(BASE + '/audit-trail?limit=20');
  if (!d || d.length === 0) {{
    document.getElementById('audit-content').innerHTML = '<div style="color:' + COLORS.text_muted + ';">No audit records</div>';
    return;
  }}
  document.getElementById('audit-content').innerHTML = '<table style="width:100%;font-size:12px;border-collapse:collapse;">' +
    '<tr style="border-bottom:1px solid ' + COLORS.border + ';"><th style="text-align:left;padding:4px;">Time</th><th style="text-align:left;">Session</th><th>ICD</th><th>Conf</th><th>Esc</th></tr>' +
    d.map(r => `<tr style="border-bottom:1px solid ${{COLORS.border}};">
      <td style="padding:4px;">${{fmtTime(r.timestamp)}}</td>
      <td style="font-family:monospace;font-size:11px;">${{r.session_id ? r.session_id.slice(0,8) : '-'}}...</td>
      <td>${{(r.icd_codes || []).join(', ') || '-'}}</td>
      <td>${{r.confidence ? r.confidence.toFixed(2) : '-'}}</td>
      <td>${{r.escalated ? '<span class="badge badge-error">YES</span>' : '<span class="badge badge-ok">NO</span>'}}</td>
    </tr>`).join('') + '</table>';
}}

async function refresh() {{
  await Promise.all([loadHealth(), loadAlerts(), loadPerformance(), loadVectorSpace(), loadSafety(), loadBias(), loadAudit()]);
}}

refresh();
setInterval(refresh, 30000);

// Vector space controls
const _slider = document.getElementById('points-slider');
const _label = document.getElementById('points-label');
const _methodSel = document.getElementById('method-select');
const _caseBtn = document.getElementById('case-overlay-btn');
const _caseClearBtn = document.getElementById('case-clear-btn');
if (_slider) {{
  _slider.addEventListener('input', () => {{ _label.textContent = _slider.value; }});
  _slider.addEventListener('change', () => {{ loadVectorSpace(); }});
}}
if (_methodSel) {{
  _methodSel.addEventListener('change', () => {{ loadVectorSpace(); }});
}}
if (_caseBtn) {{
  _caseBtn.addEventListener('click', () => {{ loadCaseOverlay(); }});
}}
if (_caseClearBtn) {{
  _caseClearBtn.addEventListener('click', () => {{
    document.getElementById('case-id-input').value = '';
    _caseClearBtn.style.display = 'none';
    loadVectorSpace();
  }});
}}
"""
    return full_page("Overview", "overview", body, js)
