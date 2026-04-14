"""Tests for build.py — no file I/O against cameras.json during unit tests."""

import json
from collections import OrderedDict
from pathlib import Path
from unittest.mock import patch

import pytest

from build import (
    build,
    e,
    group_by_roadway,
    load_data,
    render_page,
    render_roadway_section,
    render_view_card,
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

class TestLoadData:
    def test_loads_valid_json(self, tmp_path, sample_cameras):
        p = tmp_path / "cameras.json"
        p.write_text(json.dumps(sample_cameras), encoding="utf-8")
        result = load_data(str(p))
        assert result == sample_cameras

    def test_raises_file_not_found_for_missing_file(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        with pytest.raises(FileNotFoundError, match="fetch.py"):
            load_data(missing)


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

    def test_total_camera_count_in_page(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "3" in html

    def test_roadway_count_in_page(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "2" in html  # 2 roadways (I-10, SR-101)

    def test_all_roadways_present(self, sample_roadways):
        html = render_page(sample_roadways, total=3)
        assert "I-10" in html
        assert "SR-101" in html


# ---------------------------------------------------------------------------
# build (end-to-end, no real cameras.json)
# ---------------------------------------------------------------------------

class TestBuild:
    def test_writes_html_file(self, tmp_path, sample_cameras):
        input_file = tmp_path / "cameras.json"
        output_file = tmp_path / "cameras.html"
        input_file.write_text(json.dumps(sample_cameras), encoding="utf-8")

        build(input_path=str(input_file), output_path=str(output_file))

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_output_contains_camera_data(self, tmp_path, sample_cameras):
        input_file = tmp_path / "cameras.json"
        output_file = tmp_path / "cameras.html"
        input_file.write_text(json.dumps(sample_cameras), encoding="utf-8")

        build(input_path=str(input_file), output_path=str(output_file))

        content = output_file.read_text(encoding="utf-8")
        assert "I-10" in content
        assert "SR-101" in content

    def test_missing_input_raises_file_not_found(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        output = str(tmp_path / "out.html")
        with pytest.raises(FileNotFoundError):
            build(input_path=missing, output_path=output)
