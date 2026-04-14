"""
fetch.py — Phase 1
Calls the AZ511 API and writes camera data to cameras.json.
"""

import json
import sys

from az511 import AZ511Client
from az511.exceptions import AuthError, RateLimitError, APIError


def load_cameras(api_key: str | None = None) -> list[dict]:
    """Instantiate AZ511Client, call get_cameras(), return list of serialized dicts.

    AZ511Client automatically loads .env via python-dotenv, so passing api_key
    is optional — it is exposed here mainly to allow test injection.

    Raises RuntimeError on auth failure, rate limiting, or other API errors.
    """
    try:
        client = AZ511Client(api_key=api_key) if api_key else AZ511Client()
        cameras = client.get_cameras()
    except AuthError:
        raise RuntimeError(
            "Invalid API key. Check AZ511_API_KEY in your .env file. "
            "Get a free key at https://www.az511.com/my511/register"
        )
    except RateLimitError:
        raise RuntimeError(
            "AZ511 rate limit exceeded (10 requests / 60 seconds). "
            "Wait a moment and retry."
        )
    except APIError as exc:
        raise RuntimeError(f"AZ511 API error: {exc}") from exc

    return [serialize_camera(cam) for cam in cameras]


def serialize_camera(cam) -> dict:
    """Convert a Camera model instance to a plain dict.

    Only views with status == 'Enabled' are included.
    """
    return {
        "roadway": cam.roadway.upper() if cam.roadway else cam.roadway,
        "location": cam.location,
        "latitude": cam.latitude,
        "longitude": cam.longitude,
        "views": [
            {
                "id": view.id,
                "url": view.url,
                "description": view.description,
                "status": view.status,
            }
            for view in cam.views
            if view.status == "Enabled"
        ],
    }


def filter_cameras(cameras: list[dict]) -> list[dict]:
    """Drop cameras that have no enabled views."""
    return [cam for cam in cameras if cam["views"]]


def sort_cameras(cameras: list[dict]) -> list[dict]:
    """Sort by (roadway, location), case-insensitive, for deterministic output."""
    return sorted(
        cameras,
        key=lambda c: (c["roadway"].lower(), c["location"].lower()),
    )


def save_cameras(cameras: list[dict], path: str = "cameras.json") -> None:
    """Write the camera list to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cameras, fh, indent=2)


def main() -> None:
    cameras = load_cameras()
    cameras = filter_cameras(cameras)
    cameras = sort_cameras(cameras)
    save_cameras(cameras)
    roadway_count = len({cam["roadway"] for cam in cameras})
    print(f"Saved {len(cameras)} cameras across {roadway_count} roadways to cameras.json")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
