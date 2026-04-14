"""
build.py — Phase 2
Reads cameras.json and generates a static cameras.html viewer.
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

def load_data(path: str = "cameras.json") -> list[dict]:
    """Load cameras from JSON file.

    Raises FileNotFoundError with a helpful message if the file is missing.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"'{path}' not found. Run 'python fetch.py' first to fetch camera data."
        )
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
# HTML rendering helpers
# ---------------------------------------------------------------------------

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: #f0f2f5;
  color: #1a1a2e;
  line-height: 1.5;
}

header {
  background: #1a1a2e;
  color: #fff;
  padding: 1.5rem 2rem;
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,.35);
}
header h1 { font-size: 1.6rem; font-weight: 700; letter-spacing: -.5px; }
.meta { font-size: 0.8rem; opacity: 0.65; margin-top: 0.2rem; }

main { max-width: 1400px; margin: 0 auto; padding: 1.25rem 1rem 3rem; }

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
  header { padding: 1rem; }
}
"""


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


def render_page(roadways: OrderedDict, total: int) -> str:
    """Assemble the complete HTML document."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    roadway_count = len(roadways)

    sections = "".join(
        render_roadway_section(roadway, cameras, first=(i == 0))
        for i, (roadway, cameras) in enumerate(roadways.items())
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AZ511 Traffic Cameras</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <h1>AZ511 Traffic Cameras</h1>
    <p class="meta">Generated {e(timestamp)} &mdash; {total} cameras on {roadway_count} roadways</p>
  </header>
  <main>
    {sections}
  </main>
  <footer>
    <p>Data from <a href="https://www.az511.com" target="_blank" rel="noopener">AZ511.com</a></p>
  </footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build(input_path: str = "cameras.json", output_path: str = "cameras.html") -> None:
    """Load data, group by roadway, render HTML, write to file."""
    cameras = load_data(input_path)
    roadways = group_by_roadway(cameras)
    total = sum(len(v) for v in roadways.values())
    html = render_page(roadways, total)
    Path(output_path).write_text(html, encoding="utf-8")
    print(
        f"Built {output_path} — {len(roadways)} roadways, {total} cameras total"
    )


def main() -> None:
    build()


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
