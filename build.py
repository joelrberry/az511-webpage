"""
build.py — Phase 2
Reads cameras.json, message_boards.json, and weather_stations.json,
generates a static az511.html viewer with a 4-tab layout.

Extensibility pattern: add a new section by implementing three functions:
  load_<type>_data(path)          — reads JSON file, returns list[dict]
  render_<type>_card(item)        — returns HTML string for one item
  render_<type>_section(items)    — returns HTML string for the full section
Then include the section in render_page().
"""

import html as _html
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# HTML escaping helper
# ---------------------------------------------------------------------------

def e(value) -> str:
    """Escape a value for safe insertion into HTML text or attribute content."""
    return _html.escape(str(value), quote=True)


# ---------------------------------------------------------------------------
# Data loading & grouping
# ---------------------------------------------------------------------------

def load_cameras_data(path: str = "cameras.json") -> list[dict]:
    """Load cameras from JSON file.

    Raises FileNotFoundError with a helpful message if the file is missing.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"'{path}' not found. Run 'python fetch.py' first to fetch camera data."
        )
    return json.loads(p.read_text(encoding="utf-8"))


def load_message_boards_data(path: str = "message_boards.json") -> list[dict]:
    """Load message boards from JSON file.

    Returns an empty list if the file is missing — boards are optional.
    """
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def load_weather_stations_data(path: str = "weather_stations.json") -> list[dict]:
    """Load weather stations from JSON file.

    Returns an empty list if the file is missing — stations are optional.
    """
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def group_by_roadway(cameras: list[dict]) -> OrderedDict:
    """Group cameras by roadway, sorted alphabetically (case-insensitive)."""
    groups: dict[str, list[dict]] = {}
    for cam in cameras:
        groups.setdefault(cam["roadway"], []).append(cam)
    return OrderedDict(
        (k, groups[k]) for k in sorted(groups, key=str.lower)
    )


# ---------------------------------------------------------------------------
# Weather grip level helper
# ---------------------------------------------------------------------------

def _grip_class(level: str | None) -> str:
    """Map a level_of_grip string to a CSS class for color coding."""
    if not level:
        return ""
    u = level.upper()
    if any(k in u for k in ("DRY", "BARE", "GOOD")):
        return "grip-dry"
    if any(k in u for k in ("WET", "DAMP", "MOISTURE")):
        return "grip-wet"
    if any(k in u for k in ("ICY", "ICE", "FROST", "SNOW", "SLIP")):
        return "grip-icy"
    return ""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: #f0f2f5;
  color: #1a1a2e;
  line-height: 1.5;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* --- Header --- */
header {
  background: #1a1a2e;
  color: #fff;
  padding: 0.9rem 2rem 0;
  position: sticky;
  top: 0;
  z-index: 200;
  box-shadow: 0 2px 8px rgba(0,0,0,.35);
}
.header-top {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  flex-wrap: wrap;
}
header h1 { font-size: 1.4rem; font-weight: 700; letter-spacing: -.5px; }
.meta { font-size: 0.78rem; opacity: 0.65; }

/* --- Tab bar --- */
nav.tab-bar {
  display: flex;
  gap: 0;
  margin-top: 0.6rem;
}
button.tab-btn {
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  color: rgba(255,255,255,0.6);
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.5rem 1.1rem;
  transition: color 0.15s, border-color 0.15s;
  white-space: nowrap;
}
button.tab-btn:hover { color: #fff; }
button.tab-btn.active {
  color: #fff;
  border-bottom-color: #4a9eff;
}

/* --- Tab panels --- */
.tab-content { display: none; }
.tab-content.active { display: block; }

main { flex: 1; max-width: 1400px; width: 100%; margin: 0 auto; padding: 1.25rem 1rem 3rem; }

/* --- Map tab --- */
#map { height: 80vh; min-height: 400px; width: 100%; }

/* --- Camera accordions --- */
details {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  margin-bottom: 0.75rem;
  overflow: hidden;
}

summary {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.9rem 1.2rem;
  cursor: pointer;
  user-select: none;
  list-style: none;
  background: #16213e;
  color: #fff;
}
summary::-webkit-details-marker { display: none; }
summary::before {
  content: "\\25B6";
  font-size: 0.65rem;
  flex-shrink: 0;
  transition: transform 0.18s ease;
}
details[open] > summary::before { transform: rotate(90deg); }

.roadway-name { font-size: 1rem; font-weight: 600; flex: 1; }
.roadway-count { font-size: 0.75rem; opacity: 0.65; flex-shrink: 0; }

.camera-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 0.9rem;
  padding: 0.9rem;
}

.camera-card {
  background: #f8f9fb;
  border: 1px solid #dde2ee;
  border-radius: 8px;
  overflow: hidden;
}

.camera-location {
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.55rem 0.75rem;
  background: #e8ecf5;
  color: #1a1a2e;
  border-bottom: 1px solid #d0d6e8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.camera-img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
  background: #c8cfd8;
  transition: opacity 0.2s;
}
.camera-img:hover { opacity: 0.88; }

.view-label {
  font-size: 0.68rem;
  color: #555;
  text-align: center;
  padding: 0.25rem 0.5rem 0.4rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* --- Message Boards (VMS) --- */

.vms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 0.9rem;
  padding: 0.9rem;
}

.vms-card {
  background: #1c1c1c;
  border: 3px solid #4a4a4a;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,.6);
}

.vms-header {
  background: #2a2a2a;
  color: #999;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.35rem 0.6rem;
  border-bottom: 1px solid #3a3a3a;
  display: flex;
  justify-content: space-between;
  align-items: center;
  white-space: nowrap;
  overflow: hidden;
}

.vms-direction {
  background: #444;
  color: #bbb;
  font-size: 0.62rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  flex-shrink: 0;
  margin-left: 0.5rem;
}

.vms-display {
  background: #070707;
  padding: 0.8rem 1rem;
  box-shadow: inset 0 0 18px rgba(0,0,0,.95);
  min-height: 88px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.3rem;
}

.vms-line {
  font-family: 'Courier New', Courier, monospace;
  font-size: 1rem;
  font-weight: bold;
  letter-spacing: 3px;
  text-transform: uppercase;
  text-align: center;
  color: #FFB300;
  text-shadow: 0 0 6px #FFB300, 0 0 14px #FF8C00, 0 0 22px rgba(255,140,0,.4);
  min-height: 1.4em;
  line-height: 1.4;
}

.vms-line.blank {
  color: #1f1500;
  text-shadow: none;
}

.vms-updated {
  font-size: 0.62rem;
  color: #484848;
  text-align: right;
  padding: 0.2rem 0.5rem 0.3rem;
  background: #111;
  border-top: 1px solid #222;
}

/* --- Weather Stations --- */

.wx-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.9rem;
  padding: 1rem;
}

.wx-card {
  background: #fff;
  border-radius: 10px;
  border-top: 4px solid #718096;
  box-shadow: 0 1px 4px rgba(0,0,0,.1);
  overflow: hidden;
}
.wx-card.grip-dry  { border-top-color: #38A169; }
.wx-card.grip-wet  { border-top-color: #D97706; }
.wx-card.grip-icy  { border-top-color: #3182CE; }

.wx-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem 0.8rem 0.3rem;
}

.wx-station-id {
  font-size: 0.8rem;
  font-weight: 600;
  color: #555;
}

.grip-badge {
  font-size: 0.62rem;
  font-weight: 700;
  padding: 0.15rem 0.45rem;
  border-radius: 3px;
  background: #718096;
  color: #fff;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.grip-badge.grip-dry { background: #38A169; }
.grip-badge.grip-wet { background: #D97706; }
.grip-badge.grip-icy { background: #3182CE; }

.wx-location {
  font-size: 0.75rem;
  font-weight: 600;
  color: #1a1a2e;
  padding: 0 0.8rem 0.2rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wx-temp {
  font-size: 2.2rem;
  font-weight: 300;
  text-align: center;
  padding: 0.25rem 0.8rem 0.1rem;
  color: #1a1a2e;
  line-height: 1;
}
.wx-temp-unit { font-size: 1rem; }

.wx-stats {
  font-size: 0.75rem;
  color: #555;
  padding: 0.3rem 0.8rem 0.6rem;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.2rem 0.5rem;
}
.wx-stat { display: flex; align-items: baseline; gap: 0.25rem; }
.wx-stat-label { color: #888; font-size: 0.68rem; }

.wx-updated {
  font-size: 0.62rem;
  color: #aaa;
  text-align: right;
  padding: 0.2rem 0.8rem 0.4rem;
  border-top: 1px solid #eee;
}

/* --- Lightbox --- */
#lightbox {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.92);
  z-index: 9999;
  align-items: center;
  justify-content: center;
  cursor: zoom-out;
}

#lightbox-img {
  max-width: 95vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 3px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.8);
  cursor: default;
}

#lightbox-close {
  position: absolute;
  top: 1rem;
  right: 1.5rem;
  background: none;
  border: none;
  color: #fff;
  font-size: 2.5rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0.75;
  padding: 0;
}
#lightbox-close:hover { opacity: 1; }

/* --- Map legend --- */
.map-legend {
  background: rgba(255,255,255,0.96);
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,.2);
  padding: 0.55rem 0.65rem 0.45rem;
  min-width: 170px;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

.legend-title {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: #888;
  margin-bottom: 0.35rem;
  padding-bottom: 0.3rem;
  border-bottom: 1px solid #eee;
}

.legend-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  padding: 0.3rem 0.35rem;
  font-size: 0.8rem;
  color: #222;
  text-align: left;
  transition: background 0.12s, opacity 0.12s;
  line-height: 1.3;
}
.legend-btn:hover { background: #f3f4f6; }
.legend-btn.active { opacity: 1; }
.legend-btn:not(.active) { opacity: 0.38; }

.legend-swatch {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,.25);
}

.legend-label { flex: 1; }

.legend-count {
  font-size: 0.68rem;
  color: #888;
  background: #eef0f3;
  border-radius: 10px;
  padding: 0.05rem 0.4rem;
  flex-shrink: 0;
}

/* --- Map popup overrides --- */
.map-popup strong {
  display: block;
  font-size: 0.85rem;
  margin-bottom: 4px;
  color: #1a1a2e;
}

.popup-board-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0;
}

.popup-board-header strong { color: #888 !important; margin-bottom: 0; }

.leaflet-popup-content .vms-display {
  padding: 0.5rem 0.75rem;
  min-height: 55px;
  border-radius: 4px;
  margin-top: 6px;
}

.leaflet-popup-content .vms-line { font-size: 0.82rem; letter-spacing: 2px; }

footer {
  text-align: center;
  padding: 2rem;
  font-size: 0.78rem;
  color: #888;
}
footer a { color: #4a6fa5; text-decoration: none; }
footer a:hover { text-decoration: underline; }

@media (max-width: 480px) {
  .camera-grid { grid-template-columns: 1fr; }
  .wx-grid { grid-template-columns: 1fr; }
  header { padding: 0.75rem 1rem 0; }
  button.tab-btn { font-size: 0.75rem; padding: 0.5rem 0.7rem; }
}
"""


# ---------------------------------------------------------------------------
# Tab navigation JS
# NOTE: plain string (not f-string) — no interpolation needed here.
# ---------------------------------------------------------------------------

_TAB_JS = """\
<script>
(function () {
  'use strict';

  var TABS = ['map', 'weather', 'boards', 'cameras'];

  function showTab(name) {
    if (TABS.indexOf(name) === -1) name = 'map';
    TABS.forEach(function (t) {
      var btn = document.getElementById('tab-btn-' + t);
      var panel = document.getElementById('tab-' + t);
      if (btn)   btn.classList.toggle('active', t === name);
      if (panel) panel.classList.toggle('active', t === name);
    });
    if (name === 'map' && window._az511Map) {
      setTimeout(function () { window._az511Map.invalidateSize(); }, 10);
    }
    history.replaceState(null, '', '#' + name);
  }

  document.querySelector('.tab-bar').addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-tab]');
    if (btn) showTab(btn.dataset.tab);
  });

  var hash = location.hash.replace('#', '');
  showTab(TABS.indexOf(hash) !== -1 ? hash : 'map');
}());
</script>"""


# ---------------------------------------------------------------------------
# Leaflet map JS template
# NOTE: plain string (not f-string) so Leaflet's {s}/{z}/{x}/{y} tile URL
# placeholders are left untouched.  Data is injected via .replace().
# ---------------------------------------------------------------------------

_MAP_JS_TEMPLATE = """\
<script>
(function () {
  'use strict';

  // --- Lightbox ---
  window.openLightbox = function (src, alt) {
    document.getElementById('lightbox-img').src = src;
    document.getElementById('lightbox-img').alt = alt || '';
    document.getElementById('lightbox').style.display = 'flex';
    document.body.style.overflow = 'hidden';
  };
  window.closeLightbox = function () {
    document.getElementById('lightbox').style.display = 'none';
    document.getElementById('lightbox-img').src = '';
    document.body.style.overflow = '';
  };
  document.getElementById('lightbox').addEventListener('click', function (e) {
    if (e.target !== document.getElementById('lightbox-img')) window.closeLightbox();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') window.closeLightbox();
  });

  // --- Map ---
  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  var CAMERAS = %%CAMERAS%%;
  var BOARDS  = %%BOARDS%%;
  var WEATHER = %%WEATHER%%;

  var map = L.map('map').setView([34.0, -111.5], 7);
  window._az511Map = map;

  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '\\u00a9 <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors \\u00a9 <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
  }).addTo(map);

  var CAM_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 42" width="30" height="42">'
    + '<path d="M15 0C6.7 0 0 6.7 0 15c0 10 15 27 15 27S30 25 30 15C30 6.7 23.3 0 15 0z"'
    + ' fill="#3182CE" stroke="#1A365D" stroke-width="1.5"/>'
    + '<rect x="6" y="10" width="18" height="12" rx="2" fill="white"/>'
    + '<circle cx="15" cy="16" r="4" fill="#3182CE"/>'
    + '<circle cx="15" cy="16" r="2.2" fill="white"/>'
    + '<rect x="8" y="7.5" width="6" height="3" rx="1" fill="white"/>'
    + '<rect x="22" y="14" width="2.5" height="2" rx="0.5" fill="white"/>'
    + '</svg>';

  var VMS_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 42" width="30" height="42">'
    + '<path d="M15 0C6.7 0 0 6.7 0 15c0 10 15 27 15 27S30 25 30 15C30 6.7 23.3 0 15 0z"'
    + ' fill="#D97706" stroke="#92400E" stroke-width="1.5"/>'
    + '<rect x="4" y="8" width="22" height="14" rx="2" fill="#0a0a0a"/>'
    + '<text x="15" y="18.5" text-anchor="middle" fill="#FFB300"'
    + ' font-size="7" font-family="Courier New,monospace" font-weight="bold">VMS</text>'
    + '</svg>';

  function gripColor(level) {
    if (!level) return '#718096';
    var u = level.toUpperCase();
    if (u.indexOf('DRY') !== -1 || u.indexOf('BARE') !== -1 || u.indexOf('GOOD') !== -1) return '#38A169';
    if (u.indexOf('WET') !== -1 || u.indexOf('DAMP') !== -1 || u.indexOf('MOISTURE') !== -1) return '#D97706';
    if (u.indexOf('ICY') !== -1 || u.indexOf('ICE') !== -1 || u.indexOf('FROST') !== -1
        || u.indexOf('SNOW') !== -1 || u.indexOf('SLIP') !== -1) return '#3182CE';
    return '#718096';
  }

  function makeWeatherSvg(level) {
    var fill = gripColor(level);
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 42" width="30" height="42">'
      + '<path d="M15 0C6.7 0 0 6.7 0 15c0 10 15 27 15 27S30 25 30 15C30 6.7 23.3 0 15 0z"'
      + ' fill="' + fill + '" stroke="#2d3748" stroke-width="1.5"/>'
      + '<text x="15" y="20" text-anchor="middle" fill="white"'
      + ' font-size="10" font-family="sans-serif" font-weight="bold">W</text>'
      + '</svg>';
  }

  function makeIcon(svg) {
    return L.divIcon({
      html: svg, className: '',
      iconSize: [30, 42], iconAnchor: [15, 42], popupAnchor: [0, -44]
    });
  }

  // --- Layer groups (one per data type for legend toggling) ---
  var cameraLayer  = L.layerGroup();
  var boardLayer   = L.layerGroup();
  var weatherLayer = L.layerGroup();

  CAMERAS.forEach(function (cam) {
    if (cam.latitude == null || cam.longitude == null) return;
    var imgs = cam.views.map(function (v) {
      return '<img src="' + esc(v.url) + '"'
        + ' style="width:100%;display:block;margin:3px 0;cursor:zoom-in"'
        + ' loading="lazy" alt="' + esc(v.description) + '"'
        + ' onclick="openLightbox(this.src,this.alt)">';
    }).join('');
    var popup = '<div class="map-popup"><strong>' + esc(cam.location) + '</strong>' + imgs + '</div>';
    L.marker([cam.latitude, cam.longitude], { icon: makeIcon(CAM_SVG) })
      .bindPopup(popup, { maxWidth: 300 }).addTo(cameraLayer);
  });

  BOARDS.forEach(function (board) {
    if (board.latitude == null || board.longitude == null) return;
    var lines = board.messages.length
      ? board.messages.map(function (m) {
          return '<div class="vms-line">' + esc(m) + '</div>';
        }).join('')
      : '<div class="vms-line blank">&#9632; &nbsp; &#9632; &nbsp; &#9632;</div>';
    var popup = '<div class="map-popup">'
      + '<div class="popup-board-header"><strong>' + esc(board.roadway) + '</strong>'
      + ' <span class="vms-direction">' + esc(board.direction_of_travel) + '</span></div>'
      + '<div class="vms-display" style="margin-top:6px;border-radius:4px">' + lines + '</div>'
      + '</div>';
    L.marker([board.latitude, board.longitude], { icon: makeIcon(VMS_SVG) })
      .bindPopup(popup, { maxWidth: 300 }).addTo(boardLayer);
  });

  WEATHER.forEach(function (st) {
    if (st.latitude == null || st.longitude == null) return;
    var temp = st.air_temperature != null ? Math.round(st.air_temperature) + '\\u00b0F' : '--';
    var surf = st.surface_temperature != null ? Math.round(st.surface_temperature) + '\\u00b0F' : '--';
    var wind = st.wind_speed != null ? st.wind_speed.toFixed(0) + ' mph' : '--';
    var dir  = st.wind_direction || '';
    var grip = st.level_of_grip || 'Unknown';
    var locLine = st.location ? '<div style="font-size:0.78rem;font-weight:600;margin-bottom:4px">' + esc(st.location) + '</div>' : '';
    var popup = '<div class="map-popup">'
      + '<strong>Station #' + esc(st.id) + '</strong>'
      + locLine
      + '<div style="font-size:0.8rem;color:#555">'
      + 'Air: ' + temp + ' &nbsp; Surface: ' + surf + '<br>'
      + 'Wind: ' + wind + (dir ? ' ' + esc(dir) : '') + '<br>'
      + 'Grip: <strong>' + esc(grip) + '</strong>'
      + '</div></div>';
    L.marker([st.latitude, st.longitude], { icon: makeIcon(makeWeatherSvg(st.level_of_grip)) })
      .bindPopup(popup, { maxWidth: 240 }).addTo(weatherLayer);
  });

  // Add all layers to map (all visible by default)
  cameraLayer.addTo(map);
  boardLayer.addTo(map);
  weatherLayer.addTo(map);

  // --- Legend control ---
  var legendControl = L.control({ position: 'topright' });
  legendControl.onAdd = function () {
    var div = L.DomUtil.create('div', 'map-legend');
    L.DomEvent.disableClickPropagation(div);

    var title = L.DomUtil.create('div', 'legend-title', div);
    title.textContent = 'Layers';

    function addToggle(color, label, count, layer) {
      if (count === 0) return;
      var btn = L.DomUtil.create('button', 'legend-btn active', div);
      btn.innerHTML = '<span class="legend-swatch" style="background:' + color + '"></span>'
        + '<span class="legend-label">' + label + '</span>'
        + '<span class="legend-count">' + count + '</span>';
      L.DomEvent.on(btn, 'click', function () {
        if (map.hasLayer(layer)) {
          map.removeLayer(layer);
          L.DomUtil.removeClass(btn, 'active');
        } else {
          map.addLayer(layer);
          L.DomUtil.addClass(btn, 'active');
        }
      });
    }

    var camCount = CAMERAS.filter(function (c) { return c.latitude != null && c.longitude != null; }).length;
    var brdCount = BOARDS.filter(function (b) { return b.latitude != null && b.longitude != null; }).length;
    var wxCount  = WEATHER.filter(function (w) { return w.latitude != null && w.longitude != null; }).length;

    addToggle('#3182CE', 'Cameras',        camCount, cameraLayer);
    addToggle('#D97706', 'Message Boards', brdCount, boardLayer);
    addToggle('#718096', 'Weather',        wxCount,  weatherLayer);

    return div;
  };
  legendControl.addTo(map);
}());
</script>"""


# ---------------------------------------------------------------------------
# Camera renderers
# ---------------------------------------------------------------------------

def render_view_card(cam: dict, view: dict) -> str:
    """Return HTML for one view as a standalone card (location header + full-width image)."""
    location = e(cam.get("location") or "")
    url = e(view["url"])
    desc = e(view.get("description") or "")
    return (
        f'<div class="camera-card">'
        f'<h3 class="camera-location" title="{location}">{location}</h3>'
        f'<a href="{url}" target="_blank" rel="noopener noreferrer">'
        f'<img class="camera-img" src="{url}" alt="{desc}" loading="lazy"'
        f' onerror="this.style.display=\'none\'">'
        f"</a>"
        f'<p class="view-label">{desc}</p>'
        f"</div>"
    )


def render_roadway_section(roadway: str, cameras: list[dict], first: bool) -> str:
    """Return a <details> section for one roadway group."""
    open_attr = " open" if first else ""
    views = [view for cam in cameras for view in cam["views"]]
    count = len(views)
    noun = "camera" if count == 1 else "cameras"
    cards_html = "".join(
        render_view_card(cam, view)
        for cam in cameras
        for view in cam["views"]
    )
    return (
        f"<details{open_attr}>"
        f"<summary>"
        f'<span class="roadway-name">{e(roadway)}</span>'
        f'<span class="roadway-count">{count} {noun}</span>'
        f"</summary>"
        f'<div class="camera-grid">{cards_html}</div>'
        f"</details>"
    )


# ---------------------------------------------------------------------------
# Message board renderers
# ---------------------------------------------------------------------------

def render_message_board_card(board: dict) -> str:
    """Return HTML for one VMS board rendered as an amber-LED display panel."""
    roadway = e(board.get("roadway") or "")
    name = e(board.get("name") or "")
    direction = e(board.get("direction_of_travel") or "")
    messages = board.get("messages") or []
    last_updated = board.get("last_updated") or ""

    if messages:
        lines_html = "".join(
            f'<div class="vms-line">{e(msg)}</div>'
            for msg in messages
        )
    else:
        lines_html = '<div class="vms-line blank">&#9632; &nbsp; &#9632; &nbsp; &#9632;</div>'

    updated_html = (
        f'<div class="vms-updated">Updated: {e(last_updated[:16].replace("T", " "))} UTC</div>'
        if last_updated
        else ""
    )

    return (
        f'<div class="vms-card">'
        f'<div class="vms-header">'
        f'<span title="{name}">{roadway}</span>'
        f'<span class="vms-direction">{direction}</span>'
        f"</div>"
        f'<div class="vms-display">{lines_html}</div>'
        f"{updated_html}"
        f"</div>"
    )


def render_message_boards_section(boards: list[dict]) -> str:
    """Return HTML for all message boards, one <details> per roadway (mirrors camera layout)."""
    if not boards:
        return ""

    groups: dict[str, list[dict]] = {}
    for board in boards:
        groups.setdefault(board.get("roadway") or "Unknown", []).append(board)

    sections = []
    for i, roadway in enumerate(sorted(groups, key=str.lower)):
        roadway_boards = groups[roadway]
        count = len(roadway_boards)
        noun = "board" if count == 1 else "boards"
        open_attr = " open" if i == 0 else ""
        cards_html = "".join(render_message_board_card(b) for b in roadway_boards)
        sections.append(
            f"<details{open_attr}>"
            f"<summary>"
            f'<span class="roadway-name">{e(roadway)}</span>'
            f'<span class="roadway-count">{count} {noun}</span>'
            f"</summary>"
            f'<div class="vms-grid">{cards_html}</div>'
            f"</details>"
        )

    return "".join(sections)


# ---------------------------------------------------------------------------
# Weather station renderers
# ---------------------------------------------------------------------------

def render_weather_card(station: dict) -> str:
    """Return HTML for one weather station card."""
    station_id = e(station.get("id") or "")
    location = station.get("location") or ""
    level = station.get("level_of_grip") or ""
    cls = _grip_class(level)
    badge_cls = f"grip-badge {cls}" if cls else "grip-badge"
    card_cls = f"wx-card {cls}" if cls else "wx-card"
    grip_label = e(level) if level else "Unknown"

    # Temperature: API returns Fahrenheit directly
    air_f_val = station.get("air_temperature")
    surf_f_val = station.get("surface_temperature")
    air_f = f"{air_f_val:.0f}" if air_f_val is not None else None
    surf_f = f"{surf_f_val:.0f}" if surf_f_val is not None else None

    temp_html = (
        f'<div class="wx-temp">{e(air_f)}<span class="wx-temp-unit">&deg;F</span></div>'
        if air_f is not None
        else '<div class="wx-temp" style="color:#ccc">--</div>'
    )

    wind_speed = station.get("wind_speed")
    wind_dir = station.get("wind_direction") or ""
    max_wind = station.get("max_wind_speed")
    humidity = station.get("relative_humidity")

    def _stat(label: str, value) -> str:
        if value is None:
            return ""
        return (
            f'<span class="wx-stat">'
            f'<span class="wx-stat-label">{label}</span>'
            f'{e(value)}'
            f"</span>"
        )

    surf_str = f"{surf_f}&deg;F" if surf_f is not None else None
    wind_str = (
        f"{e(f'{wind_speed:.0f}')} mph {e(wind_dir)}".strip()
        if wind_speed is not None else None
    )
    max_wind_str = f"{e(f'{max_wind:.0f}')} mph" if max_wind is not None else None
    humidity_str = f"{e(f'{humidity:.0f}')}%" if humidity is not None else None

    stats_html = (
        _stat("Surface", surf_str)
        + _stat("Wind", wind_str)
        + _stat("Max wind", max_wind_str)
        + _stat("Humidity", humidity_str)
    )

    last_updated = station.get("last_updated") or ""
    updated_html = (
        f'<div class="wx-updated">{e(last_updated[:10])} UTC</div>'
        if last_updated
        else ""
    )

    location_html = (
        f'<div class="wx-location">{e(location)}</div>'
        if location else ""
    )

    return (
        f'<div class="{card_cls}">'
        f'<div class="wx-card-header">'
        f'<span class="wx-station-id">Station #{station_id}</span>'
        f'<span class="{badge_cls}">{grip_label}</span>'
        f"</div>"
        f"{location_html}"
        f"{temp_html}"
        f'<div class="wx-stats">{stats_html}</div>'
        f"{updated_html}"
        f"</div>"
    )


def render_weather_section(stations: list[dict]) -> str:
    """Return HTML for the weather stations grid."""
    if not stations:
        return ""
    cards_html = "".join(render_weather_card(s) for s in stations)
    return f'<div class="wx-grid">{cards_html}</div>'


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------

def render_page(
    roadways: OrderedDict,
    total: int,
    boards: list[dict] | None = None,
    stations: list[dict] | None = None,
) -> str:
    """Assemble the complete HTML document with 4-tab layout."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    roadway_count = len(roadways)
    boards = boards or []
    stations = stations or []

    camera_sections = "".join(
        render_roadway_section(roadway, cameras, first=(i == 0))
        for i, (roadway, cameras) in enumerate(roadways.items())
    )
    boards_html = render_message_boards_section(boards)
    weather_html = render_weather_section(stations)

    # Build JSON data for the map (injected into the JS template via .replace,
    # NOT via f-string, to avoid conflicts with Leaflet's {s}/{z}/{x}/{y} tile URL).
    all_cameras = [cam for cams in roadways.values() for cam in cams]
    cameras_json = json.dumps(all_cameras).replace("</", "<\\/")
    boards_json = json.dumps(boards).replace("</", "<\\/")
    weather_json = json.dumps(stations).replace("</", "<\\/")
    map_js = (
        _MAP_JS_TEMPLATE
        .replace("%%CAMERAS%%", cameras_json)
        .replace("%%BOARDS%%", boards_json)
        .replace("%%WEATHER%%", weather_json)
    )

    meta_parts = [f"{total} cameras on {roadway_count} roadways"]
    if boards:
        meta_parts.append(f"{len(boards)} message boards")
    if stations:
        meta_parts.append(f"{len(stations)} weather stations")
    meta_str = " &mdash; ".join(e(p) for p in meta_parts)

    # The f-string ends before the Leaflet/tab script tags so that Leaflet's
    # {s}/{z}/{x}/{y} tile-URL placeholders are never seen by Python's f-string parser.
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AZ511 Traffic Info</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
  <style>{CSS}</style>
</head>
<body>
  <div id="lightbox">
    <button id="lightbox-close" onclick="closeLightbox()" aria-label="Close">&times;</button>
    <img id="lightbox-img" src="" alt="">
  </div>
  <header>
    <div class="header-top">
      <h1>AZ511 Traffic Info</h1>
      <span class="meta">Generated {e(timestamp)}</span>
    </div>
    <nav class="tab-bar" role="tablist">
      <button id="tab-btn-map"     class="tab-btn" data-tab="map"     role="tab">Map</button>
      <button id="tab-btn-weather" class="tab-btn" data-tab="weather" role="tab">Weather</button>
      <button id="tab-btn-boards"  class="tab-btn" data-tab="boards"  role="tab">Message Boards</button>
      <button id="tab-btn-cameras" class="tab-btn" data-tab="cameras" role="tab">Cameras</button>
    </nav>
  </header>
  <main>
    <div id="tab-map" class="tab-content">
      <p class="meta" style="padding:0.5rem 0 0.75rem;color:#555">{meta_str}</p>
      <div id="map"></div>
    </div>
    <div id="tab-weather" class="tab-content">
      {weather_html if weather_html else '<p style="padding:1rem;color:#888">No weather station data available.</p>'}
    </div>
    <div id="tab-boards" class="tab-content">
      {boards_html if boards_html else '<p style="padding:1rem;color:#888">No message board data available.</p>'}
    </div>
    <div id="tab-cameras" class="tab-content">
      {camera_sections}
    </div>
  </main>
  <footer>
    <p>Data from <a href="https://www.az511.com" target="_blank" rel="noopener">AZ511.com</a></p>
  </footer>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
"""
    return page + map_js + "\n" + _TAB_JS + "\n</body>\n</html>"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build(
    cameras_path: str = "cameras.json",
    boards_path: str = "message_boards.json",
    weather_path: str = "weather_stations.json",
    output_path: str = "az511.html",
) -> None:
    """Load all data sources, render HTML, write to file."""
    cameras = load_cameras_data(cameras_path)
    roadways = group_by_roadway(cameras)
    total = sum(len(v) for v in roadways.values())
    boards = load_message_boards_data(boards_path)
    stations = load_weather_stations_data(weather_path)

    # Correlate weather stations with camera locations via shared ADOT source_id.
    source_id_to_location = {
        cam["source_id"]: cam["location"]
        for cam in cameras
        if cam.get("source_id")
    }
    for station in stations:
        if not station.get("location"):
            station["location"] = source_id_to_location.get(
                station.get("camera_source_id")
            )

    html = render_page(roadways, total, boards, stations)
    Path(output_path).write_text(html, encoding="utf-8")
    print(
        f"Built {output_path} — {len(roadways)} roadways, {total} cameras, "
        f"{len(boards)} message boards, {len(stations)} weather stations"
    )


def main() -> None:
    build()


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
