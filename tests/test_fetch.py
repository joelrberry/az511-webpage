"""Tests for fetch.py — no real HTTP calls are made."""

import json
import types

import pytest

from fetch import (
    filter_cameras,
    filter_message_boards,
    load_cameras,
    load_message_boards,
    load_weather_stations,
    save_cameras,
    save_message_boards,
    save_weather_stations,
    serialize_camera,
    serialize_message_board,
    serialize_weather_station,
    sort_cameras,
)


# ---------------------------------------------------------------------------
# Helpers: fake model objects that mimic az511 Pydantic models
# ---------------------------------------------------------------------------

def _make_board(
    id="mb1",
    name="I-10 EB @ 43rd",
    roadway="I-10",
    direction_of_travel="Eastbound",
    messages=None,
    latitude=33.4,
    longitude=-112.1,
    last_updated=None,
):
    from datetime import datetime, timezone
    if messages is None:
        messages = ["CONSTRUCTION AHEAD", "EXPECT DELAYS"]
    return types.SimpleNamespace(
        id=id,
        name=name,
        roadway=roadway,
        direction_of_travel=direction_of_travel,
        messages=messages,
        latitude=latitude,
        longitude=longitude,
        last_updated=last_updated,
    )


def _make_view(id="v1", url="https://example.com/cam.jpg", description="NB", status="Enabled"):
    view = types.SimpleNamespace(id=id, url=url, description=description, status=status)
    return view


def _make_camera(
    roadway="I-10",
    location="I-10 WB at 43rd Ave",
    latitude=33.4,
    longitude=-112.1,
    source_id="abc-123",
    views=None,
):
    if views is None:
        views = [_make_view()]
    return types.SimpleNamespace(
        roadway=roadway,
        location=location,
        latitude=latitude,
        longitude=longitude,
        source_id=source_id,
        views=views,
    )


# ---------------------------------------------------------------------------
# serialize_camera
# ---------------------------------------------------------------------------

class TestSerializeCamera:
    def test_all_fields_present(self):
        cam = _make_camera()
        result = serialize_camera(cam)
        assert set(result.keys()) == {"roadway", "location", "latitude", "longitude", "source_id", "views"}

    def test_field_values(self):
        cam = _make_camera(roadway="SR-101", location="SR-101 NB at Bell Rd", latitude=33.6, longitude=-112.0)
        result = serialize_camera(cam)
        assert result["roadway"] == "SR-101"
        assert result["location"] == "SR-101 NB at Bell Rd"
        assert result["latitude"] == 33.6
        assert result["longitude"] == -112.0

    def test_enabled_views_included(self):
        views = [_make_view(id="v1", status="Enabled"), _make_view(id="v2", status="Enabled")]
        cam = _make_camera(views=views)
        result = serialize_camera(cam)
        assert len(result["views"]) == 2

    def test_disabled_views_excluded(self):
        views = [
            _make_view(id="v1", status="Enabled"),
            _make_view(id="v2", status="Disabled"),
        ]
        cam = _make_camera(views=views)
        result = serialize_camera(cam)
        assert len(result["views"]) == 1
        assert result["views"][0]["id"] == "v1"

    def test_all_views_disabled_returns_empty_list(self):
        views = [_make_view(status="Disabled")]
        cam = _make_camera(views=views)
        result = serialize_camera(cam)
        assert result["views"] == []

    def test_view_dict_has_expected_keys(self):
        cam = _make_camera()
        result = serialize_camera(cam)
        assert set(result["views"][0].keys()) == {"id", "url", "description", "status"}


# ---------------------------------------------------------------------------
# filter_cameras
# ---------------------------------------------------------------------------

class TestFilterCameras:
    def test_keeps_cameras_with_views(self):
        cameras = [
            {"roadway": "I-10", "location": "loc", "latitude": 0, "longitude": 0,
             "views": [{"id": "v1", "url": "http://x.com", "description": "NB", "status": "Enabled"}]},
        ]
        assert filter_cameras(cameras) == cameras

    def test_removes_cameras_without_views(self):
        cameras = [
            {"roadway": "I-10", "location": "loc", "latitude": 0, "longitude": 0, "views": []},
        ]
        assert filter_cameras(cameras) == []

    def test_mixed_input(self):
        with_views = {"roadway": "I-10", "location": "A", "latitude": 0, "longitude": 0,
                      "views": [{"id": "v1", "url": "http://x.com", "description": "NB", "status": "Enabled"}]}
        without_views = {"roadway": "SR-51", "location": "B", "latitude": 0, "longitude": 0, "views": []}
        result = filter_cameras([with_views, without_views])
        assert result == [with_views]


# ---------------------------------------------------------------------------
# sort_cameras
# ---------------------------------------------------------------------------

class TestSortCameras:
    def _cam(self, roadway, location):
        return {"roadway": roadway, "location": location, "latitude": 0, "longitude": 0, "views": []}

    def test_sorted_by_roadway_then_location(self):
        cameras = [
            self._cam("SR-101", "SR-101 at Scottsdale Rd"),
            self._cam("I-10", "I-10 at 43rd Ave"),
            self._cam("I-10", "I-10 at 19th Ave"),
        ]
        result = sort_cameras(cameras)
        assert result[0]["roadway"] == "I-10"
        assert result[0]["location"] == "I-10 at 19th Ave"
        assert result[1]["roadway"] == "I-10"
        assert result[1]["location"] == "I-10 at 43rd Ave"
        assert result[2]["roadway"] == "SR-101"

    def test_case_insensitive_sort(self):
        cameras = [
            self._cam("sr-101", "sr-101 at z"),
            self._cam("I-10", "I-10 at a"),
        ]
        result = sort_cameras(cameras)
        assert result[0]["roadway"] == "I-10"

    def test_empty_list(self):
        assert sort_cameras([]) == []


# ---------------------------------------------------------------------------
# load_cameras (mocked)
# ---------------------------------------------------------------------------

class TestLoadCameras:
    def test_calls_get_cameras_once(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client = mock_client_cls.return_value
        mock_client.get_cameras.return_value = []

        load_cameras()

        mock_client.get_cameras.assert_called_once()

    def test_returns_serialized_dicts(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client = mock_client_cls.return_value
        mock_client.get_cameras.return_value = [_make_camera()]

        result = load_cameras()

        assert len(result) == 1
        assert result[0]["roadway"] == "I-10"

    def test_passes_api_key_when_provided(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_cameras.return_value = []

        load_cameras(api_key="test-key-123")

        mock_client_cls.assert_called_once_with(api_key="test-key-123")

    def test_no_api_key_uses_default_constructor(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_cameras.return_value = []

        load_cameras()

        mock_client_cls.assert_called_once_with()

    def test_auth_error_raises_runtime_error(self, mocker):
        from az511.exceptions import AuthError
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_cameras.side_effect = AuthError("bad key")

        with pytest.raises(RuntimeError, match="Invalid API key"):
            load_cameras()

    def test_rate_limit_error_raises_runtime_error(self, mocker):
        from az511.exceptions import RateLimitError
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_cameras.side_effect = RateLimitError("429")

        with pytest.raises(RuntimeError, match="rate limit"):
            load_cameras()

    def test_api_error_raises_runtime_error(self, mocker):
        from az511.exceptions import APIError
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_cameras.side_effect = APIError(500, "internal server error")

        with pytest.raises(RuntimeError, match="API error"):
            load_cameras()


# ---------------------------------------------------------------------------
# save_cameras
# ---------------------------------------------------------------------------

class TestSaveCameras:
    def test_writes_valid_json(self, tmp_path):
        cameras = [
            {"roadway": "I-10", "location": "loc", "latitude": 33.4, "longitude": -112.1,
             "views": [{"id": "v1", "url": "http://x.com/cam.jpg", "description": "NB", "status": "Enabled"}]},
        ]
        output = tmp_path / "cameras.json"
        save_cameras(cameras, path=str(output))

        assert output.exists()
        loaded = json.loads(output.read_text())
        assert loaded == cameras

    def test_file_is_pretty_printed(self, tmp_path):
        cameras = [{"roadway": "I-10", "location": "loc", "latitude": 0, "longitude": 0, "views": []}]
        output = tmp_path / "cameras.json"
        save_cameras(cameras, path=str(output))

        content = output.read_text()
        assert "\n" in content  # indented JSON has newlines


# ---------------------------------------------------------------------------
# serialize_message_board
# ---------------------------------------------------------------------------

class TestSerializeMessageBoard:
    def test_all_fields_present(self):
        board = _make_board()
        result = serialize_message_board(board)
        assert set(result.keys()) == {
            "id", "name", "roadway", "direction_of_travel",
            "messages", "latitude", "longitude", "last_updated",
        }

    def test_roadway_uppercased(self):
        board = _make_board(roadway="i-10")
        result = serialize_message_board(board)
        assert result["roadway"] == "I-10"

    def test_messages_preserved(self):
        board = _make_board(messages=["LINE ONE", "LINE TWO"])
        result = serialize_message_board(board)
        assert result["messages"] == ["LINE ONE", "LINE TWO"]

    def test_empty_messages_list(self):
        board = _make_board(messages=[])
        result = serialize_message_board(board)
        assert result["messages"] == []

    def test_last_updated_iso_format(self):
        from datetime import datetime, timezone
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        board = _make_board(last_updated=dt)
        result = serialize_message_board(board)
        assert result["last_updated"] == dt.isoformat()

    def test_last_updated_none(self):
        board = _make_board(last_updated=None)
        result = serialize_message_board(board)
        assert result["last_updated"] is None


# ---------------------------------------------------------------------------
# load_message_boards (mocked)
# ---------------------------------------------------------------------------

class TestLoadMessageBoards:
    def test_calls_get_message_boards_once(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client = mock_client_cls.return_value
        mock_client.get_message_boards.return_value = []

        load_message_boards()

        mock_client.get_message_boards.assert_called_once()

    def test_returns_serialized_dicts(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client = mock_client_cls.return_value
        mock_client.get_message_boards.return_value = [_make_board()]

        result = load_message_boards()

        assert len(result) == 1
        assert result[0]["roadway"] == "I-10"
        assert "messages" in result[0]

    def test_passes_api_key_when_provided(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_message_boards.return_value = []

        load_message_boards(api_key="test-key-123")

        mock_client_cls.assert_called_once_with(api_key="test-key-123")

    def test_auth_error_raises_runtime_error(self, mocker):
        from az511.exceptions import AuthError
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_message_boards.side_effect = AuthError("bad key")

        with pytest.raises(RuntimeError, match="Invalid API key"):
            load_message_boards()

    def test_rate_limit_error_raises_runtime_error(self, mocker):
        from az511.exceptions import RateLimitError
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_message_boards.side_effect = RateLimitError("429")

        with pytest.raises(RuntimeError, match="rate limit"):
            load_message_boards()

    def test_api_error_raises_runtime_error(self, mocker):
        from az511.exceptions import APIError
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_message_boards.side_effect = APIError(500, "error")

        with pytest.raises(RuntimeError, match="API error"):
            load_message_boards()


# ---------------------------------------------------------------------------
# save_message_boards
# ---------------------------------------------------------------------------

class TestSaveMessageBoards:
    def test_writes_valid_json(self, tmp_path):
        boards = [
            {"id": "mb1", "name": "I-10 EB", "roadway": "I-10",
             "direction_of_travel": "Eastbound", "messages": ["SLOW TRAFFIC"],
             "latitude": 33.4, "longitude": -112.1, "last_updated": None},
        ]
        output = tmp_path / "message_boards.json"
        save_message_boards(boards, path=str(output))

        assert output.exists()
        loaded = json.loads(output.read_text())
        assert loaded == boards

    def test_file_is_pretty_printed(self, tmp_path):
        boards = [{"id": "mb1", "name": "test", "roadway": "I-10",
                   "direction_of_travel": "EB", "messages": [],
                   "latitude": 0, "longitude": 0, "last_updated": None}]
        output = tmp_path / "message_boards.json"
        save_message_boards(boards, path=str(output))

        content = output.read_text()
        assert "\n" in content


# ---------------------------------------------------------------------------
# filter_message_boards
# ---------------------------------------------------------------------------

class TestFilterMessageBoards:
    def _board(self, messages):
        return {"id": "mb1", "name": "I-10 EB", "roadway": "I-10",
                "direction_of_travel": "Eastbound", "messages": messages,
                "latitude": 33.4, "longitude": -112.1, "last_updated": None}

    def test_keeps_board_with_real_messages(self):
        boards = [self._board(["CONSTRUCTION AHEAD", "SLOW TRAFFIC"])]
        assert filter_message_boards(boards) == boards

    def test_drops_board_with_only_no_message(self):
        boards = [self._board(["NO_MESSAGE"])]
        assert filter_message_boards(boards) == []

    def test_drops_board_with_multiple_no_message(self):
        boards = [self._board(["NO_MESSAGE", "NO_MESSAGE"])]
        assert filter_message_boards(boards) == []

    def test_drops_board_with_empty_messages(self):
        boards = [self._board([])]
        assert filter_message_boards(boards) == []

    def test_strips_no_message_from_mixed_list(self):
        boards = [self._board(["CONSTRUCTION AHEAD", "NO_MESSAGE"])]
        result = filter_message_boards(boards)
        assert len(result) == 1
        assert result[0]["messages"] == ["CONSTRUCTION AHEAD"]

    def test_mixed_boards(self):
        boards = [
            self._board(["SLOW TRAFFIC"]),
            self._board(["NO_MESSAGE"]),
            self._board([]),
        ]
        result = filter_message_boards(boards)
        assert len(result) == 1
        assert result[0]["messages"] == ["SLOW TRAFFIC"]

    def test_empty_input(self):
        assert filter_message_boards([]) == []


# ---------------------------------------------------------------------------
# Helpers for weather station tests
# ---------------------------------------------------------------------------

def _make_station(
    id=42,
    camera_source_id="abc-123",
    latitude=33.4,
    longitude=-112.1,
    air_temperature=22.0,
    surface_temperature=20.0,
    wind_speed=10.0,
    wind_direction="NE",
    relative_humidity=45.0,
    level_of_grip="DRY",
    max_wind_speed=18.0,
    last_updated=None,
):
    return types.SimpleNamespace(
        id=id,
        camera_source_id=camera_source_id,
        latitude=latitude,
        longitude=longitude,
        air_temperature=air_temperature,
        surface_temperature=surface_temperature,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        relative_humidity=relative_humidity,
        level_of_grip=level_of_grip,
        max_wind_speed=max_wind_speed,
        last_updated=last_updated,
    )


# ---------------------------------------------------------------------------
# serialize_weather_station
# ---------------------------------------------------------------------------

class TestSerializeWeatherStation:
    def test_all_fields_present(self):
        st = _make_station()
        result = serialize_weather_station(st)
        assert set(result.keys()) == {
            "id", "camera_source_id", "latitude", "longitude",
            "air_temperature", "surface_temperature",
            "wind_speed", "wind_direction",
            "relative_humidity", "level_of_grip",
            "max_wind_speed", "last_updated",
        }

    def test_camera_source_id_preserved(self):
        st = _make_station(camera_source_id="dead-beef-1234")
        result = serialize_weather_station(st)
        assert result["camera_source_id"] == "dead-beef-1234"

    def test_field_values(self):
        st = _make_station(id=7, latitude=33.5, longitude=-112.0, level_of_grip="WET")
        result = serialize_weather_station(st)
        assert result["id"] == 7
        assert result["latitude"] == 33.5
        assert result["longitude"] == -112.0
        assert result["level_of_grip"] == "WET"

    def test_last_updated_iso_format(self):
        from datetime import datetime, timezone
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        st = _make_station(last_updated=dt)
        result = serialize_weather_station(st)
        assert result["last_updated"] == dt.isoformat()

    def test_last_updated_none(self):
        st = _make_station(last_updated=None)
        result = serialize_weather_station(st)
        assert result["last_updated"] is None

    def test_none_optional_fields(self):
        st = _make_station(
            air_temperature=None,
            surface_temperature=None,
            wind_speed=None,
            wind_direction=None,
            relative_humidity=None,
            level_of_grip=None,
            max_wind_speed=None,
        )
        result = serialize_weather_station(st)
        assert result["air_temperature"] is None
        assert result["level_of_grip"] is None


# ---------------------------------------------------------------------------
# load_weather_stations (mocked)
# ---------------------------------------------------------------------------

class TestLoadWeatherStations:
    def test_calls_get_weather_stations_once(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client = mock_client_cls.return_value
        mock_client.get_weather_stations.return_value = []

        load_weather_stations()

        mock_client.get_weather_stations.assert_called_once()

    def test_returns_serialized_dicts(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client = mock_client_cls.return_value
        mock_client.get_weather_stations.return_value = [_make_station()]

        result = load_weather_stations()

        assert len(result) == 1
        assert result[0]["id"] == 42

    def test_passes_api_key_when_provided(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_weather_stations.return_value = []

        load_weather_stations(api_key="test-key-456")

        mock_client_cls.assert_called_once_with(api_key="test-key-456")

    def test_no_api_key_uses_default_constructor(self, mocker):
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_weather_stations.return_value = []

        load_weather_stations()

        mock_client_cls.assert_called_once_with()

    def test_auth_error_raises_runtime_error(self, mocker):
        from az511.exceptions import AuthError
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_weather_stations.side_effect = AuthError("bad key")

        with pytest.raises(RuntimeError, match="Invalid API key"):
            load_weather_stations()

    def test_rate_limit_error_raises_runtime_error(self, mocker):
        from az511.exceptions import RateLimitError
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_weather_stations.side_effect = RateLimitError("429")

        with pytest.raises(RuntimeError, match="rate limit"):
            load_weather_stations()

    def test_api_error_raises_runtime_error(self, mocker):
        from az511.exceptions import APIError
        mock_client_cls = mocker.patch("fetch.AZ511Client")
        mock_client_cls.return_value.get_weather_stations.side_effect = APIError(500, "error")

        with pytest.raises(RuntimeError, match="API error"):
            load_weather_stations()


# ---------------------------------------------------------------------------
# save_weather_stations
# ---------------------------------------------------------------------------

class TestSaveWeatherStations:
    def test_writes_valid_json(self, tmp_path):
        stations = [
            {"id": 42, "latitude": 33.4, "longitude": -112.1,
             "air_temperature": 22.0, "surface_temperature": 20.0,
             "wind_speed": 10.0, "wind_direction": "NE",
             "relative_humidity": 45.0, "level_of_grip": "DRY",
             "max_wind_speed": 18.0, "last_updated": None},
        ]
        output = tmp_path / "weather_stations.json"
        save_weather_stations(stations, path=str(output))

        assert output.exists()
        loaded = json.loads(output.read_text())
        assert loaded == stations

    def test_file_is_pretty_printed(self, tmp_path):
        stations = [{"id": 1, "latitude": 33.4, "longitude": -112.1,
                     "air_temperature": None, "surface_temperature": None,
                     "wind_speed": None, "wind_direction": None,
                     "relative_humidity": None, "level_of_grip": None,
                     "max_wind_speed": None, "last_updated": None}]
        output = tmp_path / "weather_stations.json"
        save_weather_stations(stations, path=str(output))

        content = output.read_text()
        assert "\n" in content
