# AZ511 Traffic Viewer — Project Guide

## What this project does

Two-phase static site pipeline that fetches live Arizona 511 traffic data and builds a single-file HTML viewer:

1. **`python fetch.py`** — Calls the AZ511 API, writes `cameras.json` + `message_boards.json` + `weather_stations.json`
2. **`python build.py`** — Reads those JSON files, generates `az511.html`

Open `az511.html` directly in a browser — no server needed.

## Architecture

```
fetch.py  →  cameras.json + message_boards.json + weather_stations.json
build.py  →  az511.html  (4-tab layout: Map | Weather | Message Boards | Cameras)
```

The HTML page has a sticky tab bar (URL hash navigation: `#map`, `#weather`, `#boards`, `#cameras`):
- **Map** — Leaflet.js (CartoDB Voyager tiles), blue pins for cameras, amber pins for VMS boards, color-coded pins for weather stations
- **Weather** — Grid of weather station cards color-coded by road grip level (green=dry, amber=wet, blue=icy)
- **Message Boards** — Amber LED / VMS-style cards, one collapsible `<details>` per roadway (first open, rest closed) — same layout pattern as Cameras
- **Cameras** — Image grids, one collapsible `<details>` per roadway (first open, rest closed)

## Extensibility pattern

Adding a new AZ511 endpoint (events, alerts, etc.) requires:

**`fetch.py`** — three functions:
```python
def load_<type>(api_key=None) -> list[dict]: ...
def serialize_<type>(obj) -> dict: ...
def save_<type>(items, path="<type>.json") -> None: ...
```
Then call them from `main()`.

**`build.py`** — three functions:
```python
def load_<type>_data(path="<type>.json") -> list[dict]: ...
def render_<type>_card(item: dict) -> str: ...
def render_<type>_section(items: list[dict]) -> str: ...
```
Then add a tab panel in `render_page()` and a tab button in the nav.

## Key files

| File | Purpose |
|------|---------|
| `fetch.py` | AZ511 API client wrapper, data serialization, saves JSON |
| `build.py` | HTML generation: CSS, JS templates, render functions |
| `cameras.json` | Fetched camera data (generated, not committed) |
| `message_boards.json` | Fetched VMS board data (generated, not committed) |
| `weather_stations.json` | Fetched weather station data (generated, not committed) |
| `az511.html` | Final output HTML (generated, not committed) |
| `tests/test_fetch.py` | Unit tests for fetch.py (mocked API) |
| `tests/test_build.py` | Unit tests for build.py (no file I/O) |

## Running

```bash
# Set up
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your AZ511_API_KEY

# Run
python fetch.py        # fetch data → cameras.json + message_boards.json + weather_stations.json
python build.py        # build → az511.html
open az511.html

# Test
pytest
```

## API key

Free key at https://www.az511.com/my511/register — stored in `.env` as `AZ511_API_KEY`.

## AZ511 API rate limit

10 requests per 60 seconds. `fetch.py` makes 3 requests (cameras + message boards + weather stations).

## JS template notes

`_MAP_JS_TEMPLATE` and `_TAB_JS` in `build.py` are **plain strings** (not f-strings). This is intentional:
- Leaflet's tile URL contains `{s}`, `{z}`, `{x}`, `{y}` which would be misinterpreted as Python f-string placeholders.
- Data is injected via `.replace("%%CAMERAS%%", ...)` etc. and concatenated outside the f-string in `render_page()`.

`window._az511Map` is set in the map JS so the tab switcher can call `map.invalidateSize()` when switching to the Map tab — necessary because Leaflet can't compute tile layout while the panel is hidden.

## Map legend / layer toggling

Each marker type (cameras, message boards, weather stations) is added to its own `L.layerGroup()` (`cameraLayer`, `boardLayer`, `weatherLayer`). A Leaflet custom control (`legendControl`, positioned `topright`) renders toggle buttons — one per type. Clicking a button calls `map.addLayer()` / `map.removeLayer()` and toggles an `active` CSS class that dims the button when the layer is hidden. The control is only shown for types that have at least one mapped marker.

## Weather station ↔ camera correlation

Weather stations are correlated to cameras via a shared ADOT UUID:

- `Camera.source_id` (in `cameras.json`) = `WeatherStation.camera_source_id` (in `weather_stations.json`)

`build()` builds a `source_id → location` lookup from `cameras.json` and writes a `location` field onto each weather station dict before passing them to `render_page()`. This means `weather_stations.json` does **not** contain the location string — it is enriched at build time. All 17 current weather stations match a camera.

## Weather temperature note

The AZ511 API returns temperatures in **Celsius**. Both the Python card renderer (`render_weather_card`) and the JS map popup convert to Fahrenheit for display.
