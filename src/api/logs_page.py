"""Log Viewer page (Kibana-like) — served at GET /dashboard/logs.

Searchable, filterable structured log viewer with auto-refresh.
"""
# ruff: noqa: E501

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.api._dashboard_shared import COLORS, full_page

router = APIRouter(tags=["dashboard-pages"])

_C = COLORS  # short alias for inline HTML


def _build_body() -> str:
    """Build the log viewer HTML body."""
    c = _C
    input_style = (
        f"background:{c['surface2']};color:{c['text']};"
        f"border:1px solid {c['border']};border-radius:4px;"
        "padding:6px 10px;font-size:13px;"
    )
    return f"""
<h2 style="margin-bottom:16px;font-size:18px;">Log Viewer</h2>

<!-- Controls -->
<div class="card" style="margin-bottom:16px;">
  <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;">
    <div>
      <label style="font-size:11px;color:{c['text_muted']};display:block;">Level</label>
      <select id="filter-level" style="{input_style}">
        <option value="">ALL</option>
        <option value="DEBUG">DEBUG</option>
        <option value="INFO">INFO</option>
        <option value="WARNING">WARNING</option>
        <option value="ERROR">ERROR</option>
        <option value="CRITICAL">CRITICAL</option>
      </select>
    </div>
    <div style="flex:1;min-width:150px;">
      <label style="font-size:11px;color:{c['text_muted']};display:block;">Event</label>
      <input id="filter-event" type="text" placeholder="e.g. prediction_recorded"
        style="width:100%;{input_style}">
    </div>
    <div style="flex:1;min-width:150px;">
      <label style="font-size:11px;color:{c['text_muted']};display:block;">Search</label>
      <input id="filter-search" type="text" placeholder="Free-text search..."
        style="width:100%;{input_style}">
    </div>
    <div style="min-width:120px;">
      <label style="font-size:11px;color:{c['text_muted']};display:block;">Session ID</label>
      <input id="filter-session" type="text" placeholder="UUID..."
        style="width:100%;{input_style}font-family:monospace;">
    </div>
    <div>
      <label style="font-size:11px;color:{c['text_muted']};display:block;">Limit</label>
      <select id="filter-limit" style="{input_style}">
        <option value="50">50</option>
        <option value="100">100</option>
        <option value="200" selected>200</option>
        <option value="500">500</option>
      </select>
    </div>
    <div style="display:flex;align-items:flex-end;gap:8px;padding-top:16px;">
      <button id="btn-search" style="background:{c['accent']};color:white;border:none;border-radius:4px;padding:7px 16px;font-size:13px;cursor:pointer;">Search</button>
      <label style="font-size:12px;display:flex;align-items:center;gap:4px;cursor:pointer;">
        <input type="checkbox" id="auto-refresh" checked> Auto-refresh
      </label>
    </div>
  </div>
</div>

<!-- Log count -->
<div style="margin-bottom:8px;font-size:12px;color:{c['text_muted']};">
  <span id="log-count">0</span> records &middot; <span id="last-refresh">-</span>
</div>

<!-- Log table -->
<div class="card" style="padding:0;overflow:hidden;">
  <table style="width:100%;border-collapse:collapse;font-size:12px;" id="log-table">
    <thead>
      <tr style="background:{c['surface2']};border-bottom:1px solid {c['border']};">
        <th style="text-align:left;padding:8px 12px;width:140px;">Timestamp</th>
        <th style="text-align:left;padding:8px 6px;width:70px;">Level</th>
        <th style="text-align:left;padding:8px 6px;width:200px;">Event</th>
        <th style="text-align:left;padding:8px 6px;width:140px;">Logger</th>
        <th style="text-align:left;padding:8px 12px;">Details</th>
      </tr>
    </thead>
    <tbody id="log-body">
      <tr><td colspan="5" style="padding:40px;text-align:center;color:{c['text_muted']};">Loading...</td></tr>
    </tbody>
  </table>
</div>
"""


@router.get("/dashboard/logs", response_class=HTMLResponse)
async def logs_page() -> str:
    """Render the log viewer page."""
    body = _build_body()

    js = f"""
const COLORS = {json.dumps(COLORS)};
const LEVEL_BADGE = {{
  'DEBUG': 'badge-debug',
  'INFO': 'badge-info',
  'WARNING': 'badge-warn',
  'ERROR': 'badge-error',
  'CRITICAL': 'badge-error',
}};
let refreshTimer = null;

function buildUrl() {{
  const params = new URLSearchParams();
  const level = document.getElementById('filter-level').value;
  const event = document.getElementById('filter-event').value.trim();
  const search = document.getElementById('filter-search').value.trim();
  const session = document.getElementById('filter-session').value.trim();
  const limit = document.getElementById('filter-limit').value;
  if (level) params.set('level', level);
  if (event) params.set('event', event);
  if (search) params.set('search', search);
  if (session) params.set('session_id', session);
  params.set('limit', limit);
  return '/api/v1/dashboard/logs?' + params.toString();
}}

function highlightText(text, search) {{
  if (!search) return escapeHtml(text);
  const escaped = escapeHtml(text);
  const re = new RegExp(
    '(' + search.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')',
    'gi'
  );
  return escaped.replace(
    re,
    '<mark style="background:#f59e0b33;color:#f59e0b;">$1</mark>'
  );
}}

function renderFields(fields) {{
  if (!fields || Object.keys(fields).length === 0) {{
    return '<span style="color:' + COLORS.text_muted + ';">-</span>';
  }}
  return Object.entries(fields).map(([k,v]) =>
    '<span style="color:' + COLORS.accent + ';">'
    + escapeHtml(k) + '</span>='
    + '<span>' + escapeHtml(String(v)) + '</span>'
  ).join(' &middot; ');
}}

function renderExpanded(fields) {{
  return '<pre style="background:' + COLORS.bg
    + ';padding:12px;border-radius:6px;font-size:11px;'
    + 'overflow-x:auto;margin:0;white-space:pre-wrap;">'
    + escapeHtml(JSON.stringify(fields, null, 2)) + '</pre>';
}}

async function loadLogs() {{
  const url = buildUrl();
  const data = await fetchJSON(url);
  if (!data) return;

  document.getElementById('log-count').textContent = data.length;
  document.getElementById('last-refresh').textContent =
    new Date().toLocaleTimeString();

  const search = document.getElementById('filter-search').value.trim();
  const tbody = document.getElementById('log-body');

  if (data.length === 0) {{
    tbody.innerHTML = '<tr><td colspan="5" style="padding:40px;'
      + 'text-align:center;color:' + COLORS.text_muted
      + ';">No matching log records</td></tr>';
    return;
  }}

  tbody.innerHTML = data.map((rec, i) => {{
    const badge = LEVEL_BADGE[rec.level] || 'badge-debug';
    const fc = rec.fields ? Object.keys(rec.fields).length : 0;
    return '<tr class="log-row" data-index="' + i + '" '
      + 'style="border-bottom:1px solid ' + COLORS.border
      + ';cursor:pointer;transition:background 0.1s;" '
      + 'onmouseover="this.style.background=\\'' + COLORS.surface2
      + '\\'" onmouseout="this.style.background=\\'transparent\\'">'
      + '<td style="padding:6px 12px;font-family:monospace;'
      + 'font-size:11px;white-space:nowrap;">'
      + fmtTime(rec.timestamp) + '</td>'
      + '<td style="padding:6px;"><span class="badge ' + badge
      + '">' + rec.level + '</span></td>'
      + '<td style="padding:6px;font-weight:500;">'
      + highlightText(rec.event, search) + '</td>'
      + '<td style="padding:6px;color:' + COLORS.text_muted
      + ';font-size:11px;">'
      + escapeHtml(rec.logger_name || '') + '</td>'
      + '<td style="padding:6px;font-size:11px;">'
      + renderFields(rec.fields)
      + (fc > 0 ? ' <span style="color:' + COLORS.text_muted
        + ';font-size:10px;">(' + fc + ')</span>' : '')
      + '</td></tr>'
      + '<tr class="log-detail" id="detail-' + i
      + '" style="display:none;"><td colspan="5" style="padding:'
      + '8px 12px;background:' + COLORS.surface2 + ';">'
      + renderExpanded(rec.fields)
      + '</td></tr>';
  }}).join('');

  document.querySelectorAll('.log-row').forEach(row => {{
    row.addEventListener('click', () => {{
      const idx = row.dataset.index;
      const d = document.getElementById('detail-' + idx);
      d.style.display = d.style.display === 'none'
        ? 'table-row' : 'none';
    }});
  }});
}}

function setupAutoRefresh() {{
  const cb = document.getElementById('auto-refresh');
  if (refreshTimer) clearInterval(refreshTimer);
  if (cb.checked) {{
    refreshTimer = setInterval(loadLogs, 5000);
    document.getElementById('refresh-indicator').textContent = 'Live';
  }} else {{
    document.getElementById('refresh-indicator').textContent = 'Paused';
  }}
}}

document.getElementById('auto-refresh').addEventListener(
  'change', setupAutoRefresh
);
document.getElementById('btn-search').addEventListener(
  'click', loadLogs
);

['filter-event', 'filter-search', 'filter-session'].forEach(id => {{
  document.getElementById(id).addEventListener('keydown', e => {{
    if (e.key === 'Enter') loadLogs();
  }});
}});
document.getElementById('filter-level').addEventListener(
  'change', loadLogs
);

loadLogs();
setupAutoRefresh();
"""
    return full_page("Logs", "logs", body, js)
