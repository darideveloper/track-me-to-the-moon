import asyncio
import threading

from moon_tracker import ui


def test_track_geometry_keeps_knob_inside_track():
    from moon_tracker import brand

    geo = ui.track_geometry()
    assert geo["knob_left"] == geo["pad"]
    assert geo["knob_right"] + geo["knob"] + geo["pad"] == geo["track_w"]
    assert geo["knob"] < geo["track_h"]
    assert geo["track_w"] <= brand.px(340)


def test_format_hms():
    assert ui.format_hms(0) == "00:00:00"
    assert ui.format_hms(3) == "00:00:03"
    assert ui.format_hms(65) == "00:01:05"
    assert ui.format_hms(3661) == "01:01:01"
    assert ui.format_hms(-5) == "00:00:00"


def test_format_duration():
    assert ui.format_duration(5400) == "1h 30m"
    assert ui.format_duration(2700) == "45m"
    assert ui.format_duration(45) == "45s"


def test_format_session_row_closed():
    title, subtitle = ui.format_session_row(
        "2026-09-27T09:00:00+00:00", "2026-09-27T10:30:00+00:00"
    )
    assert "→" in title and "now" not in title
    assert "1h 30m" in subtitle


def test_ticker_does_not_refresh_after_close_begins():
    closing = threading.Event()
    ticks = []

    async def sleep_then_close(_):
        closing.set()

    asyncio.run(ui._run_ticker_until_closed(closing, ticks.append, sleep_then_close))

    assert ticks == []


def test_begin_close_is_idempotent():
    closing = threading.Event()
    lifecycle = {"close_started": False}
    lock = threading.Lock()

    assert ui._begin_close(closing, lock, lifecycle) is True
    assert closing.is_set()
    assert ui._begin_close(closing, lock, lifecycle) is False


def test_format_session_row_running():
    title, subtitle = ui.format_session_row("2026-09-27T13:00:00+00:00", None)
    assert title.endswith("→ now")
    assert "2026-09-27" in subtitle


def test_blocks_visible_sheds_decorations_before_history():
    from moon_tracker import ui

    full = ui.blocks_visible(420, hint_needed=True)
    assert full["history"] and full["rows"] >= 3
    assert full["history_header"] and full["footer"] and full["hint"] and full["sync"]

    assert ui.blocks_visible(220, hint_needed=True)["footer"] is False
    assert ui.blocks_visible(220, hint_needed=True)["hint"] is False
    assert ui.blocks_visible(220, hint_needed=True)["history"] is True
    assert ui.blocks_visible(170, hint_needed=True)["history"] is False


def test_blocks_visible_is_monotonic_and_whole_rows():
    from moon_tracker import ui

    keys = ("sync", "hint", "footer", "history_header", "history")
    prev = ui.blocks_visible(500, hint_needed=True)
    for h in range(500, 100, -10):
        cur = ui.blocks_visible(h, hint_needed=True)
        for k in keys:
            assert not (cur[k] and not prev[k]), f"{k} came back at {h}"
        assert cur["rows"] <= prev["rows"]
        assert cur["rows"] >= 0
        if not cur["history_header"]:
            assert cur["rows"] >= 0
        prev = cur


def test_core_height_is_the_floor():
    from moon_tracker import ui

    m = ui.layout_metrics()
    core = ui.blocks_visible(m["core"], hint_needed=True)
    assert core["history"] is False and core["rows"] == 0
    assert core["sync"] is False and core["hint"] is False and core["footer"] is False
    # One row above the floor must already be useful again.
    assert ui.blocks_visible(m["core"] + m["row"] * 2, hint_needed=True)["history"] is True


def test_fill_absorbs_the_remainder():
    from moon_tracker import ui

    m = ui.layout_metrics()
    for h in (420, 400, 380, 360, 330, 300):
        b = ui.blocks_visible(h, hint_needed=True, metrics=m)
        fixed = (m["core"]
                 + (m["sync"] if b["sync"] else 0)
                 + (m["hint"] if b["hint"] else 0)
                 + (m["footer"] if b["footer"] else 0)
                 + (m["label"] if b["history_header"] else 0))
        assert b["fill"] >= 0
        assert b["fill"] < m["row"] or b["rows"] == 0
        assert fixed + b["rows"] * m["row"] + b["fill"] == h


def test_snug_default_is_a_three_row_layout():
    from moon_tracker import ui

    m = ui.layout_metrics()
    h = ui.default_height(m)
    b = ui.blocks_visible(h, hint_needed=False, metrics=m)
    assert b["rows"] == 3
    assert b["footer"] and b["sync"] and b["history_header"]
    assert b["fill"] == 0  # no dead space at the default window size
    assert h > m["core"]
