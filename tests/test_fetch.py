"""Tests for fetch.py — no real HTTP calls are made."""

import json
import types

import pytest

from fetch import (
    filter_cameras,
    load_cameras,
    save_cameras,
    serialize_camera,
    sort_cameras,
)


# ---------------------------------------------------------------------------
# Helpers: fake model objects that mimic az511 Pydantic models
# ---------------------------------------------------------------------------

def _make_view(id="v1", url="https://example.com/cam.jpg", description="NB", status="Enabled"):
    view = types.SimpleNamespace(id=id, url=url, description=description, status=status)
    return view


def _make_camera(
    roadway="I-10",
    location="I-10 WB at 43rd Ave",
    latitude=33.4,
    longitude=-112.1,
    views=None,
):
    if views is None:
        views = [_make_view()]
    return types.SimpleNamespace(
        roadway=roadway,
        location=location,
        latitude=latitude,
        longitude=longitude,
        views=views,
    )


# ---------------------------------------------------------------------------
# serialize_camera
# ---------------------------------------------------------------------------

class TestSerializeCamera:
    def test_all_fields_present(self):
        cam = _make_camera()
        result = serialize_camera(cam)
        assert set(result.keys()) == {"roadway", "location", "latitude", "longitude", "views"}

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
