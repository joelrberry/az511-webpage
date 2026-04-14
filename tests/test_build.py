"""Tests for build.py — no file I/O against cameras.json during unit tests."""

import json
from collections import OrderedDict
from pathlib import Path
from unittest.mock import patch

import pytest

from build import (
    _grip_class,
    build,
    e,
    group_by_roadway,
    load_cameras_data,
    load_message_boards_data,
    load_weather_stations_data,
    render_message_board_card,
    render_message_boards_section,
    render_page,
    render_roadway_section,
    render_view_card,
    render_weather_card,
    render_weather_section,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_view():
    return {
        "id": "v1",
        "url": "https://az511.com/cam/snap.jpg",
        "description": "Northbound",
        "status": "Enabled",
    }


@pytest.fixture
def sample_camera(sample_view):
    return {
        "roadway": "I-10",
        "location": "I-10 WB at 43rd Ave",
        "latitude": 33.4484,
        "longitude": -112.0740,
        "views": [sample_view],
    }


@pytest.fixture
def sample_cameras(sample_view):
    return [
        {
            "roadway": "SR-101",
            "location": "SR-101 at Scottsdale Rd",
            "latitude": 33.5,
            "longitude": -111.9,
            "views": [sample_view],
        },
        {
            "roadway": "I-10",
            "location": "I-10 WB at 43rd Ave",
            "latitude": 33.4,
            "longitude": -112.1,
            "views": [sample_view],
        },
        {
            "roadway": "I-10",
            "location": "I-10 EB at 19th Ave",
            "latitude": 33.45,
            "longitude": -112.09,
            "views": [sample_view],
        },
    ]


@pytest.fixture
def sample_roadways(sample_cameras):
    return group_by_roadway(sample_cameras)


@pytest.fixture
def sample_station():
    return {
        "id": 42,
        "camera_source_id": "abc-uuid-123",
        "latitude": 33.4,
        "longitude": -112.1,
        "air_temperature": 22.0,
        "surface_temperature": 20.0,
        "wind_speed": 10.0,
        "wind_direction": "NE",
        "relative_humidity": 45.0,
        "level_of_grip": "DRY",
        "max_wind_speed": 18.0,
        "last_updated": "2024-06-15T12:00:00+00:00",
        "location": "I-40 @ 132.25",
    }


@pytest.fixture
def sample_station_no_data():
    return {
        "id": 99,
        "camera_source_id": None,
        "latitude": 33.6,
        "longitude": -111.9,
        "air_temperature": None,
        "surface_temperature": None,
        "wind_speed": None,
        "wind_direction": None,
        "relative_humidity": None,
        "level_of_grip": None,
        "max_wind_speed": None,
        "last_updated": None,
        "location": None,
    }


# ---------------------------------------------------------------------------
# e() — HTML escaping helper
# ---------------------------------------------------------------------------

class TestEscapeHelper:
    def test_escapes_ampersand(self):
        assert "&amp;" in e("a & b")

    def test_escapes_less_than(self):
        assert "&lt;" in e("<script>")

    def test_escapes_greater_than(self):
        assert "&gt;" in e(">")

    def test_escapes_double_quote(self):
        assert "&quot;" in e('"hello"')

    def test_non_string_converted(self):
        assert e(42) == "42"


# ---------------------------------------------------------------------------
# load_data
# ---------------------------------------------------------------------------

class TestLoadCamerasData:
    def test_loads_valid_json(self, tmp_path, sample_cameras):
        p = tmp_path / "cameras.json"
        p.write_text(json.dumps(sample_cameras), encoding="utf-8")
        result = load_cameras_data(str(p))
        assert result == sample_cameras

    def test_raises_file_not_found_for_missing_file(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        with pytest.raises(FileNotFoundError, match="fetch.py"):
            load_cameras_data(missing)


# ---------------------------------------------------------------------------
# group_by_roadway
# ---------------------------------------------------------------------------

class TestGroupByRoadway:
    def test_keys_are_sorted_alphabetically(self, sample_cameras):
        result = group_by_roadway(sample_cameras)
        keys = list(result.keys())
        assert keys == sorted(keys, key=str.lower)

    def test_i10_before_sr101(self, sample_cameras):
        result = group_by_roadway(sample_cameras)
        keys = list(result.keys())
        assert keys.index("I-10") < keys.index("SR-101")

    def test_cameras_grouped_correctly(self, sample_cameras):
        result = group_by_roadway(sample_cameras)
        assert len(result["I-10"]) == 2
        assert len(result["SR-101"]) == 1

    def test_returns_ordered_dict(self, sample_cameras):
        result = group_by_roadway(sample_cameras)
        assert isinstance(result, OrderedDict)

    def test_empty_input(self):
        result = group_by_roadway([])
        assert result == OrderedDict()


# ---------------------------------------------------------------------------
# render_view_card
# ---------------------------------------------------------------------------

class TestRenderViewCard:
    def test_contains_img_src(self, sample_camera, sample_view):
        html = render_view_card(sample_camera, sample_view)
        assert f'src="{sample_view["url"]}"' in html

    def test_contains_href(self, sample_camera, sample_view):
        html = render_view_card(sample_camera, sample_view)
        assert f'href="{sample_view["url"]}"' in html

    def test_has_lazy_loading(self, sample_camera, sample_view):
        html = render_view_card(sample_camera, sample_view)
        assert 'loading="lazy"' in html

    def test_opens_in_new_tab(self, sample_camera, sample_view):
        html = render_view_card(sample_camera, sample_view)
        assert 'target="_blank"' in html

    def test_contains_location(self, sample_camera, sample_view):
        html = render_view_card(sample_camera, sample_view)
        assert sample_camera["location"] in html

    def test_description_in_alt_and_label(self, sample_camera, sample_view):
        html = render_view_card(sample_camera, sample_view)
        assert sample_view["description"] in html

    def test_escapes_special_chars_in_description(self, sample_camera):
        view = {
            "id": "v1",
            "url": "https://az511.com/cam.jpg",
            "description": '<b>View & "Check"</b>',
            "status": "Enabled",
        }
        html = render_view_card(sample_camera, view)
        assert "<b>" not in html
        assert "&lt;b&gt;" in html
        assert "&amp;" in html
        assert "&quot;" in html

    def test_escapes_url_ampersands(self, sample_camera):
        view = {
            "id": "v1",
            "url": "https://az511.com/cam.jpg?a=1&b=2",
            "description": "NB",
            "status": "Enabled",
        }
        html = render_view_card(sample_camera, view)
        assert "a=1&b=2" not in html
        assert "a=1&amp;b=2" in html


# ---------------------------------------------------------------------------
# render_roadway_section
# ---------------------------------------------------------------------------

class TestRenderRoadwaySection:
    def test_first_section_has_open_attribute(self, sample_cameras):
        cameras = [c for c in sample_cameras if c["roadway"] == "I-10"]
        html = render_roadway_section("I-10", cameras, first=True)
        assert "<details open>" in html

    def test_non_first_section_has_no_open_attribute(self, sample_cameras):
        cameras = [c for c in sample_cameras if c["roadway"] == "SR-101"]
        html = render_roadway_section("SR-101", cameras, first=False)
        assert "<details>" in html
        assert "<details open>" not in html

    def test_roadway_name_in_summary(self, sample_cameras):
        cameras = [c for c in sample_cameras if c["roadway"] == "I-10"]
        html = render_roadway_section("I-10", cameras, first=True)
        assert "I-10" in html

    def test_view_count_in_summary(self, sample_cameras):
        # 2 I-10 cameras each with 1 view = 2 views total
        cameras = [c for c in sample_cameras if c["roadway"] == "I-10"]
        html = render_roadway_section("I-10", cameras, first=True)
        assert "2" in html

    def test_singular_noun_for_one_view(self, sample_camera):
        html = render_roadway_section("I-10", [sample_camera], first=False)
        assert "1 camera" in html

    def test_plural_noun_for_multiple_views(self, sample_cameras):
        cameras = [c for c in sample_cameras if c["roadway"] == "I-10"]
        html = render_roadway_section("I-10", cameras, first=False)
        assert "2 cameras" in html


# ---------------------------------------------------------------------------
# render_page
# ---------------------------------------------------------------------------

class TestRenderPage:
    def test_contains_doctype(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "<!DOCTYPE html>" in html

    def test_contains_title(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "<title>" in html
        assert "AZ511" in html

    def test_contains_main_element(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "<main>" in html

    def test_all_roadways_present(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "I-10" in html
        assert "SR-101" in html

    def test_contains_map_div(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert 'id="map"' in html

    def test_contains_leaflet_css(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "leaflet" in html.lower()

    def test_camera_coordinates_in_map_script(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        # Coordinates from sample cameras should appear in embedded JSON
        assert "33.4" in html or "33.5" in html

    def test_contains_lightbox_div(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert 'id="lightbox"' in html
        assert 'id="lightbox-img"' in html

    def test_contains_lightbox_js(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert 'openLightbox' in html
        assert 'closeLightbox' in html

    # --- Tab layout ---

    def test_contains_tab_bar(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert 'class="tab-bar"' in html

    def test_all_four_tab_buttons_present(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert 'id="tab-btn-map"' in html
        assert 'id="tab-btn-weather"' in html
        assert 'id="tab-btn-boards"' in html
        assert 'id="tab-btn-cameras"' in html

    def test_all_four_tab_panels_present(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert 'id="tab-map"' in html
        assert 'id="tab-weather"' in html
        assert 'id="tab-boards"' in html
        assert 'id="tab-cameras"' in html

    def test_tab_js_show_tab_function_present(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "showTab" in html

    def test_no_map_section_details_wrapper(self, sample_roadways):
        """Map is now a plain tab panel, not wrapped in <details id='map-section'>."""
        html = render_page(sample_roadways, total=3)
        assert 'id="map-section"' not in html

    def test_weather_stations_rendered_when_provided(self, sample_roadways, sample_station):
        html = render_page(sample_roadways, total=3, stations=[sample_station])
        assert "Station #42" in html

    def test_weather_tab_empty_message_when_no_stations(self, sample_roadways):
        html = render_page(sample_roadways, total=3, stations=[])
        assert "No weather station data" in html

    def test_legend_control_present(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "map-legend" in html
        assert "legendControl" in html

    def test_legend_layer_groups_present(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "cameraLayer" in html
        assert "boardLayer" in html
        assert "weatherLayer" in html


# ---------------------------------------------------------------------------
# build (end-to-end, no real cameras.json)
# ---------------------------------------------------------------------------

class TestBuild:
    def test_writes_html_file(self, tmp_path, sample_cameras):
        input_file = tmp_path / "cameras.json"
        output_file = tmp_path / "az511.html"
        input_file.write_text(json.dumps(sample_cameras), encoding="utf-8")

        build(cameras_path=str(input_file), output_path=str(output_file))

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_output_contains_camera_data(self, tmp_path, sample_cameras):
        input_file = tmp_path / "cameras.json"
        output_file = tmp_path / "az511.html"
        input_file.write_text(json.dumps(sample_cameras), encoding="utf-8")

        build(cameras_path=str(input_file), output_path=str(output_file))

        content = output_file.read_text(encoding="utf-8")
        assert "I-10" in content
        assert "SR-101" in content

    def test_missing_input_raises_file_not_found(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        output = str(tmp_path / "out.html")
        with pytest.raises(FileNotFoundError):
            build(cameras_path=missing, output_path=output)

    def test_weather_path_param_accepted(self, tmp_path, sample_cameras):
        cameras_file = tmp_path / "cameras.json"
        weather_file = tmp_path / "wx.json"
        output_file = tmp_path / "az511.html"
        cameras_file.write_text(json.dumps(sample_cameras), encoding="utf-8")
        # weather file missing — build should still succeed (optional)
        build(
            cameras_path=str(cameras_file),
            weather_path=str(weather_file),
            output_path=str(output_file),
        )
        assert output_file.exists()


# ---------------------------------------------------------------------------
# load_message_boards_data
# ---------------------------------------------------------------------------

class TestLoadMessageBoardsData:
    def test_loads_valid_json(self, tmp_path):
        boards = [{"id": "mb1", "name": "I-10 EB", "roadway": "I-10",
                   "direction_of_travel": "Eastbound", "messages": ["SLOW"],
                   "latitude": 33.4, "longitude": -112.1, "last_updated": None}]
        p = tmp_path / "message_boards.json"
        p.write_text(json.dumps(boards), encoding="utf-8")
        result = load_message_boards_data(str(p))
        assert result == boards

    def test_returns_empty_list_for_missing_file(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        result = load_message_boards_data(missing)
        assert result == []


# ---------------------------------------------------------------------------
# load_weather_stations_data
# ---------------------------------------------------------------------------

class TestLoadWeatherStationsData:
    def test_loads_valid_json(self, tmp_path, sample_station):
        p = tmp_path / "weather_stations.json"
        p.write_text(json.dumps([sample_station]), encoding="utf-8")
        result = load_weather_stations_data(str(p))
        assert result == [sample_station]

    def test_returns_empty_list_for_missing_file(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        result = load_weather_stations_data(missing)
        assert result == []


# ---------------------------------------------------------------------------
# Fixtures for message board tests
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_board():
    return {
        "id": "mb1",
        "name": "I-10 EB @ 43rd Ave",
        "roadway": "I-10",
        "direction_of_travel": "Eastbound",
        "messages": ["CONSTRUCTION AHEAD", "EXPECT DELAYS"],
        "latitude": 33.4,
        "longitude": -112.1,
        "last_updated": "2024-06-15T12:00:00+00:00",
    }


@pytest.fixture
def sample_board_empty_messages():
    return {
        "id": "mb2",
        "name": "SR-101 NB",
        "roadway": "SR-101",
        "direction_of_travel": "Northbound",
        "messages": [],
        "latitude": 33.6,
        "longitude": -111.9,
        "last_updated": None,
    }


# ---------------------------------------------------------------------------
# render_message_board_card
# ---------------------------------------------------------------------------

class TestRenderMessageBoardCard:
    def test_contains_roadway(self, sample_board):
        html = render_message_board_card(sample_board)
        assert "I-10" in html

    def test_contains_direction(self, sample_board):
        html = render_message_board_card(sample_board)
        assert "Eastbound" in html

    def test_message_lines_rendered(self, sample_board):
        html = render_message_board_card(sample_board)
        assert "CONSTRUCTION AHEAD" in html
        assert "EXPECT DELAYS" in html

    def test_vms_line_class_on_messages(self, sample_board):
        html = render_message_board_card(sample_board)
        assert 'class="vms-line"' in html

    def test_blank_class_when_no_messages(self, sample_board_empty_messages):
        html = render_message_board_card(sample_board_empty_messages)
        assert 'class="vms-line blank"' in html

    def test_updated_timestamp_shown(self, sample_board):
        html = render_message_board_card(sample_board)
        assert "2024-06-15" in html

    def test_no_updated_line_when_none(self, sample_board_empty_messages):
        html = render_message_board_card(sample_board_empty_messages)
        assert "Updated:" not in html

    def test_escapes_special_chars_in_messages(self, sample_board):
        board = {**sample_board, "messages": ['<b>GO SLOW & "MERGE"</b>']}
        html = render_message_board_card(board)
        assert "<b>" not in html
        assert "&lt;b&gt;" in html
        assert "&amp;" in html
        assert "&quot;" in html


# ---------------------------------------------------------------------------
# render_message_boards_section
# ---------------------------------------------------------------------------

class TestRenderMessageBoardsSection:
    def test_empty_boards_returns_empty_string(self):
        assert render_message_boards_section([]) == ""

    def test_roadway_name_in_summary(self, sample_board):
        html = render_message_boards_section([sample_board])
        assert "I-10" in html

    def test_count_in_summary(self, sample_board):
        html = render_message_boards_section([sample_board])
        assert "1 board" in html

    def test_plural_noun_for_multiple_boards_same_roadway(self, sample_board):
        board2 = {**sample_board, "id": "mb3"}
        html = render_message_boards_section([sample_board, board2])
        assert "2 boards" in html

    def test_each_roadway_gets_its_own_details(self, sample_board, sample_board_empty_messages):
        html = render_message_boards_section([sample_board, sample_board_empty_messages])
        assert html.count("<details") == 2

    def test_first_roadway_open(self, sample_board, sample_board_empty_messages):
        html = render_message_boards_section([sample_board, sample_board_empty_messages])
        assert "<details open>" in html

    def test_subsequent_roadway_closed(self, sample_board, sample_board_empty_messages):
        # I-10 sorts before SR-101; SR-101 section should not be open
        html = render_message_boards_section([sample_board, sample_board_empty_messages])
        assert html.count("<details open>") == 1

    def test_board_card_included(self, sample_board):
        html = render_message_boards_section([sample_board])
        assert "CONSTRUCTION AHEAD" in html


# ---------------------------------------------------------------------------
# _grip_class
# ---------------------------------------------------------------------------

class TestGripClass:
    def test_dry_variants(self):
        assert _grip_class("DRY") == "grip-dry"
        assert _grip_class("BARE_AND_DRY") == "grip-dry"
        assert _grip_class("GOOD") == "grip-dry"

    def test_wet_variants(self):
        assert _grip_class("WET") == "grip-wet"
        assert _grip_class("DAMP") == "grip-wet"
        assert _grip_class("TRACE_MOISTURE") == "grip-wet"

    def test_icy_variants(self):
        assert _grip_class("ICY") == "grip-icy"
        assert _grip_class("FROST") == "grip-icy"
        assert _grip_class("SNOW") == "grip-icy"
        assert _grip_class("SLIPPERY") == "grip-icy"

    def test_none_returns_empty(self):
        assert _grip_class(None) == ""

    def test_unknown_returns_empty(self):
        assert _grip_class("UNKNOWN_VALUE") == ""

    def test_case_insensitive(self):
        assert _grip_class("dry") == "grip-dry"
        assert _grip_class("wet") == "grip-wet"
        assert _grip_class("icy") == "grip-icy"


# ---------------------------------------------------------------------------
# render_weather_card
# ---------------------------------------------------------------------------

class TestRenderWeatherCard:
    def test_contains_station_id(self, sample_station):
        html = render_weather_card(sample_station)
        assert "Station #42" in html

    def test_contains_grip_badge(self, sample_station):
        html = render_weather_card(sample_station)
        assert "grip-badge" in html

    def test_grip_dry_class_applied(self, sample_station):
        html = render_weather_card(sample_station)
        assert "grip-dry" in html

    def test_grip_wet_class_applied(self, sample_station):
        station = {**sample_station, "level_of_grip": "WET"}
        html = render_weather_card(station)
        assert "grip-wet" in html

    def test_grip_icy_class_applied(self, sample_station):
        station = {**sample_station, "level_of_grip": "ICY"}
        html = render_weather_card(station)
        assert "grip-icy" in html

    def test_temperature_displayed(self, sample_station):
        # 22.0°F displayed directly (API already returns Fahrenheit)
        html = render_weather_card(sample_station)
        assert "22" in html

    def test_no_crash_on_all_none_fields(self, sample_station_no_data):
        html = render_weather_card(sample_station_no_data)
        assert "Station #99" in html

    def test_updated_timestamp_shown(self, sample_station):
        html = render_weather_card(sample_station)
        assert "2024-06-15" in html

    def test_no_updated_when_none(self, sample_station_no_data):
        html = render_weather_card(sample_station_no_data)
        assert "UTC" not in html

    def test_grip_label_in_html(self, sample_station):
        html = render_weather_card(sample_station)
        assert "DRY" in html

    def test_unknown_grip_label_when_none(self, sample_station_no_data):
        html = render_weather_card(sample_station_no_data)
        assert "Unknown" in html

    def test_location_shown_when_present(self, sample_station):
        html = render_weather_card(sample_station)
        assert "I-40 @ 132.25" in html

    def test_no_location_element_when_none(self, sample_station_no_data):
        html = render_weather_card(sample_station_no_data)
        assert "wx-location" not in html


# ---------------------------------------------------------------------------
# Camera → weather station location enrichment (happens in build())
# ---------------------------------------------------------------------------

class TestWeatherStationLocationEnrichment:
    """Verify that build() annotates stations with the matched camera location."""

    def _write_json(self, tmp_path, name, data):
        p = tmp_path / name
        p.write_text(json.dumps(data), encoding="utf-8")
        return str(p)

    def _sample_cameras(self, source_id="abc-uuid-123"):
        return [
            {
                "roadway": "I-40",
                "location": "I-40 @ 132.25",
                "latitude": 35.2,
                "longitude": -112.7,
                "source_id": source_id,
                "views": [{"id": "v1", "url": "http://x.com/cam.jpg",
                           "description": "NB", "status": "Enabled"}],
            }
        ]

    def _sample_stations(self, camera_source_id="abc-uuid-123"):
        return [
            {
                "id": 42,
                "camera_source_id": camera_source_id,
                "latitude": 35.2,
                "longitude": -112.7,
                "air_temperature": 22.0,
                "surface_temperature": 20.0,
                "wind_speed": 10.0,
                "wind_direction": "NE",
                "relative_humidity": 45.0,
                "level_of_grip": "DRY",
                "max_wind_speed": 18.0,
                "last_updated": None,
            }
        ]

    def test_matched_station_gets_location(self, tmp_path):
        cameras_path = self._write_json(tmp_path, "cameras.json", self._sample_cameras())
        stations_path = self._write_json(tmp_path, "wx.json", self._sample_stations())
        output_path = str(tmp_path / "out.html")

        build(cameras_path=cameras_path, weather_path=stations_path, output_path=output_path)

        html = (tmp_path / "out.html").read_text(encoding="utf-8")
        assert "I-40 @ 132.25" in html

    def test_unmatched_station_has_no_location_element(self, tmp_path):
        cameras_path = self._write_json(tmp_path, "cameras.json", self._sample_cameras("uuid-A"))
        stations_path = self._write_json(tmp_path, "wx.json", self._sample_stations("uuid-B"))
        output_path = str(tmp_path / "out.html")

        build(cameras_path=cameras_path, weather_path=stations_path, output_path=output_path)

        html = (tmp_path / "out.html").read_text(encoding="utf-8")
        # wx-location element only renders when a station has a matched location
        assert 'class="wx-location"' not in html


# ---------------------------------------------------------------------------
# render_weather_section
# ---------------------------------------------------------------------------

class TestRenderWeatherSection:
    def test_empty_returns_empty_string(self):
        assert render_weather_section([]) == ""

    def test_grid_class_present(self, sample_station):
        html = render_weather_section([sample_station])
        assert "wx-grid" in html

    def test_station_card_included(self, sample_station):
        html = render_weather_section([sample_station])
        assert "Station #42" in html

    def test_multiple_stations_all_rendered(self, sample_station, sample_station_no_data):
        html = render_weather_section([sample_station, sample_station_no_data])
        assert "Station #42" in html
        assert "Station #99" in html
