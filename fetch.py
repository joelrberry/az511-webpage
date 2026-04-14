"""
fetch.py — Phase 1
Calls the AZ511 API and writes data to JSON files.

Extensibility pattern: add a new endpoint by implementing three functions:
  load_<type>(api_key)   — calls AZ511Client.<method>(), returns list[dict]
  serialize_<type>(obj)  — converts a model instance to a plain dict
  save_<type>(items)     — writes the list to a JSON file
Then call them from main().
"""

import json
import sys

from az511 import AZ511Client
from az511.exceptions import AuthError, RateLimitError, APIError


# ---------------------------------------------------------------------------
# Cameras
# ---------------------------------------------------------------------------

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
    source_id is the ADOT UUID used to correlate cameras with weather stations.
    """
    return {
        "roadway": cam.roadway.upper() if cam.roadway else cam.roadway,
        "location": cam.location,
        "latitude": cam.latitude,
        "longitude": cam.longitude,
        "source_id": cam.source_id,
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


# ---------------------------------------------------------------------------
# Message Boards
# ---------------------------------------------------------------------------

def load_message_boards(api_key: str | None = None) -> list[dict]:
    """Instantiate AZ511Client, call get_message_boards(), return list of serialized dicts.

    Raises RuntimeError on auth failure, rate limiting, or other API errors.
    """
    try:
        client = AZ511Client(api_key=api_key) if api_key else AZ511Client()
        boards = client.get_message_boards()
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

    return [serialize_message_board(board) for board in boards]


def serialize_message_board(board) -> dict:
    """Convert a MessageBoard model instance to a plain dict."""
    return {
        "id": board.id,
        "name": board.name,
        "roadway": board.roadway.upper() if board.roadway else board.roadway,
        "direction_of_travel": board.direction_of_travel,
        "messages": board.messages,
        "latitude": board.latitude,
        "longitude": board.longitude,
        "last_updated": board.last_updated.isoformat() if board.last_updated else None,
    }


def filter_message_boards(boards: list[dict]) -> list[dict]:
    """Strip 'NO_MESSAGE' entries and drop boards with no remaining messages."""
    result = []
    for board in boards:
        messages = [m for m in board["messages"] if m != "NO_MESSAGE"]
        if messages:
            result.append({**board, "messages": messages})
    return result


def save_message_boards(boards: list[dict], path: str = "message_boards.json") -> None:
    """Write the message board list to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(boards, fh, indent=2)


# ---------------------------------------------------------------------------
# Weather Stations
# ---------------------------------------------------------------------------

def load_weather_stations(api_key: str | None = None) -> list[dict]:
    """Instantiate AZ511Client, call get_weather_stations(), return list of serialized dicts.

    Raises RuntimeError on auth failure, rate limiting, or other API errors.
    """
    try:
        client = AZ511Client(api_key=api_key) if api_key else AZ511Client()
        stations = client.get_weather_stations()
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

    return [serialize_weather_station(s) for s in stations]


def serialize_weather_station(station) -> dict:
    """Convert a WeatherStation model instance to a plain dict.

    camera_source_id is the ADOT UUID that matches Camera.source_id,
    used by build.py to annotate each station with a human-readable location.
    """
    return {
        "id": station.id,
        "camera_source_id": station.camera_source_id,
        "latitude": station.latitude,
        "longitude": station.longitude,
        "air_temperature": station.air_temperature,
        "surface_temperature": station.surface_temperature,
        "wind_speed": station.wind_speed,
        "wind_direction": station.wind_direction,
        "relative_humidity": station.relative_humidity,
        "level_of_grip": station.level_of_grip,
        "max_wind_speed": station.max_wind_speed,
        "last_updated": station.last_updated.isoformat() if station.last_updated else None,
    }


def save_weather_stations(stations: list[dict], path: str = "weather_stations.json") -> None:
    """Write the weather station list to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(stations, fh, indent=2)


# ---------------------------------------------------------------------------
# Rest Areas
# ---------------------------------------------------------------------------

def load_rest_areas(api_key: str | None = None) -> list[dict]:
    """Instantiate AZ511Client, call get_rest_areas(), return list of serialized dicts.

    Raises RuntimeError on auth failure, rate limiting, or other API errors.
    """
    try:
        client = AZ511Client(api_key=api_key) if api_key else AZ511Client()
        areas = client.get_rest_areas()
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

    return [serialize_rest_area(area) for area in areas]


def serialize_rest_area(area) -> dict:
    """Convert a RestArea model instance to a plain dict."""
    return {
        "id": area.id,
        "name": area.name,
        "status": area.status,
        "location": area.location,
        "city": area.city,
        "latitude": area.latitude,
        "longitude": area.longitude,
        "restroom": area.restroom,
        "ramada": area.ramada,
        "visitor_center": area.visitor_center,
        "travel_information": area.travel_information,
        "vending_machine": area.vending_machine,
        "total_truck_spaces": area.total_truck_spaces,
        "available_truck_spaces": area.available_truck_spaces,
    }


def save_rest_areas(areas: list[dict], path: str = "rest_areas.json") -> None:
    """Write the rest area list to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(areas, fh, indent=2)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def main() -> None:
    cameras = load_cameras()
    cameras = filter_cameras(cameras)
    cameras = sort_cameras(cameras)
    save_cameras(cameras)
    roadway_count = len({cam["roadway"] for cam in cameras})
    print(f"Saved {len(cameras)} cameras across {roadway_count} roadways to cameras.json")

    boards = load_message_boards()
    boards = filter_message_boards(boards)
    save_message_boards(boards)
    board_roadway_count = len({b["roadway"] for b in boards})
    print(f"Saved {len(boards)} message boards across {board_roadway_count} roadways to message_boards.json")

    stations = load_weather_stations()
    save_weather_stations(stations)
    print(f"Saved {len(stations)} weather stations to weather_stations.json")

    areas = load_rest_areas()
    save_rest_areas(areas)
    print(f"Saved {len(areas)} rest areas to rest_areas.json")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
