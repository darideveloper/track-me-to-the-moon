import asyncio
import threading

from moon_tracker import ui


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
