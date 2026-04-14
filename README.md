# AZ511 Traffic Viewer

A static single-file web app that pulls live Arizona 511 traffic data — cameras, message boards, and weather stations — and bakes it into a self-contained HTML file you can open directly in a browser. No server, no build toolchain, no dependencies at runtime.

---

## Features

- **Traffic cameras** — Live snapshots grouped by roadway, with a click-to-expand lightbox
- **Message boards** — Freeway VMS signs rendered as amber LED displays
- **Weather stations** — Road condition cards color-coded by surface grip level (dry / wet / icy)
- **Interactive map** — Leaflet.js map with color-coded pins for all three data types; camera images load inline in map popups
- **4-tab layout** — Map, Weather, Message Boards, and Cameras tabs with URL hash navigation (`#map`, `#weather`, `#boards`, `#cameras`)
- **Zero runtime dependencies** — The output is one `.html` file; Leaflet loads from CDN

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A free [AZ511 API key](https://www.az511.com/my511/register)

### 2. Install

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and paste your AZ511_API_KEY
```

### 4. Run

```bash
python fetch.py   # Fetches data → cameras.json, message_boards.json, weather_stations.json
python build.py   # Builds → az511.html
open az511.html   # macOS; or just double-click the file
```

---

## How It Works

The project is a two-phase pipeline:

```
fetch.py ──► cameras.json
         ──► message_boards.json       ──► build.py ──► az511.html
         ──► weather_stations.json
```

**`fetch.py`** calls the AZ511 REST API (via the [`az511`](https://pypi.org/project/az511-client/) Python client), filters and normalises the responses, and writes three JSON files. Running fetch again refreshes the data.

**`build.py`** reads those JSON files and generates a single self-contained HTML file. All CSS, JavaScript, and data are inlined — no assets directory, no network requests beyond the Leaflet CDN and live camera image URLs.

To refresh the page, re-run both scripts and reload the HTML file.

---

## Project Structure

```
.
├── fetch.py                # Phase 1: API → JSON
├── build.py                # Phase 2: JSON → HTML
├── requirements.txt
├── .env.example            # API key template
├── tests/
│   ├── test_fetch.py       # Unit tests for fetch.py (mocked API)
│   └── test_build.py       # Unit tests for build.py (no file I/O)
└── CLAUDE.md               # Developer reference (AI coding assistant context)
```

Generated files (`.gitignore`d):

| File | Description |
|---|---|
| `cameras.json` | Fetched camera data |
| `message_boards.json` | Fetched VMS board data |
| `weather_stations.json` | Fetched weather station data |
| `az511.html` | Final output — open this in a browser |

---

## Running Tests

```bash
pytest
```

142 tests covering serialization, filtering, sorting, HTML rendering, escaping, and the end-to-end build. No real API calls are made — the AZ511 client is mocked throughout.

---

## Adding a New Data Type

The codebase follows a consistent 3+3 function pattern. To add a new AZ511 endpoint (events, alerts, rest areas, etc.):

**`fetch.py`** — add three functions and call them from `main()`:

```python
def load_<type>(api_key=None) -> list[dict]:
    """Call AZ511Client.<method>(), return serialized list."""
    ...

def serialize_<type>(obj) -> dict:
    """Convert model instance to plain dict."""
    ...

def save_<type>(items, path="<type>.json") -> None:
    """Write list to JSON file."""
    ...
```

**`build.py`** — add three functions, a tab panel in `render_page()`, and a tab button:

```python
def load_<type>_data(path="<type>.json") -> list[dict]:
    """Load from JSON; return [] if file missing (optional data)."""
    ...

def render_<type>_card(item: dict) -> str:
    """Return HTML string for one item."""
    ...

def render_<type>_section(items: list[dict]) -> str:
    """Return HTML string for the full section."""
    ...
```

See the existing camera, message board, and weather station implementations for reference.

---

## AZ511 API Notes

- **Free key** — register at [az511.com/my511/register](https://www.az511.com/my511/register)
- **Rate limit** — 10 requests per 60 seconds; `fetch.py` uses 3 (cameras, message boards, weather stations)
- **Data freshness** — AZ511 updates camera snapshots every 1–2 minutes; re-run `fetch.py` + `build.py` to get fresh data

---

## Development Notes

**Leaflet / f-string conflict** — `_MAP_JS_TEMPLATE` and `_TAB_JS` in `build.py` are plain Python strings, not f-strings. Leaflet's tile URL template uses `{s}`, `{z}`, `{x}`, `{y}` which Python would try to evaluate as f-string placeholders. Data is injected via `.replace("%%PLACEHOLDER%%", value)` and the JS is concatenated outside any f-string context.

**Temperature units** — The AZ511 API returns temperatures in Celsius. Both `render_weather_card()` in `build.py` and the map popup JS convert to Fahrenheit for display.

**Map resize on tab switch** — Leaflet can't calculate tile layout while a panel is hidden (CSS `display: none`). The map is exposed as `window._az511Map` so the tab switcher can call `invalidateSize()` with a short delay when the Map tab becomes active.
