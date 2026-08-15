"""GUI-level smoke tests, run headlessly via the Qt 'offscreen' platform.

These verify the application actually starts, the main window builds,
and basic user flows (typing text, comparing, exporting) work end to end
through real Qt signal/slot wiring and a real (short-lived) worker
thread — not mocked out. Requires `QT_QPA_PLATFORM=offscreen` in the
test environment (set automatically by `conftest.py`).
"""
import time

import pytest

from app.core.enums import ExportFormat
from app.gui.main_window import MainWindow
from app.services.settings_service import SettingsService


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.get_config_dir", lambda: tmp_path)
    settings_service = SettingsService()
    win = MainWindow(settings_service)
    yield win
    win.close()


def test_main_window_constructs_and_shows(window):
    window.show()
    assert window.isVisible()
    assert "Enterprise Text Compare" in window.windowTitle()


def test_panels_accept_pasted_text(window):
    window.source_a_panel.set_text("hello\nworld\n")
    window.source_b_panel.set_text("hello\nthere\n")
    assert window.source_a_panel.text() == "hello\nworld\n"
    assert window.source_b_panel.text() == "hello\nthere\n"


def test_compare_action_disabled_state_management(window, qapp):
    window.source_a_panel.set_text("a\nb\n")
    window.source_b_panel.set_text("a\nc\n")
    assert window.compare_action.isEnabled()

    window.compare_action.trigger()
    assert not window.compare_action.isEnabled()

    for _ in range(300):
        qapp.processEvents()
        time.sleep(0.005)
        if window._last_result is not None:
            break

    assert window._last_result is not None
    assert window.compare_action.isEnabled()
    assert window.export_action.isEnabled()


def test_export_after_compare(window, qapp, tmp_path):
    window.source_a_panel.set_text("a\nb\n")
    window.source_b_panel.set_text("a\nc\n")
    window.compare_action.trigger()
    for _ in range(300):
        qapp.processEvents()
        time.sleep(0.005)
        if window._last_result is not None:
            break

    out_path = tmp_path / "report.html"
    window._export_service.export(window._last_result, out_path, ExportFormat.HTML)
    assert out_path.exists()
    assert "Comparison Report" in out_path.read_text(encoding="utf-8")


def test_theme_switch_applies_stylesheet(window, qapp):
    from app.core.enums import Theme

    window._change_theme(Theme.DARK)
    assert window._settings_service.current.theme == Theme.DARK
    assert qapp.styleSheet() != ""


def test_clear_source_panel(window):
    window.source_a_panel.set_text("some content")
    window.source_a_panel.clear()
    assert window.source_a_panel.text() == ""


# ----------------------------------------------------------------------
# Persistent-worker regression tests.
#
# An earlier implementation created a brand-new QThread + ComparisonWorker
# for every single comparison. Under repeated comparisons this proved
# genuinely racy (confirmed via a 20-run app.exec()-driven stress test):
# tearing down one QThread and immediately starting another could
# intermittently leave the old thread not fully joined, producing
# "QThread: Destroyed while thread is still running" and, occasionally, a
# second comparison that never completed at all. The fix was to make the
# comparison and file-load workers persistent (created once, reused for
# every job via a queued `start(...)` dispatch) rather than one-shot. The
# tests below exercise exactly the scenario that used to fail: repeated,
# real comparisons through the actual QThread-backed worker pipeline.
# ----------------------------------------------------------------------


def _run_compare_and_wait(window, qapp, source_a, source_b, timeout_s=5.0):
    window.source_a_panel.set_text(source_a)
    window.source_b_panel.set_text(source_b)
    window._last_result = None
    window.compare_action.trigger()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
        if window._last_result is not None and window.compare_action.isEnabled():
            return True
    return False


def test_repeated_comparisons_reuse_persistent_worker(window, qapp):
    """The same worker/thread must correctly handle many sequential jobs."""
    assert window._compare_thread.isRunning()
    thread_identity = id(window._compare_thread)

    for i in range(5):
        ok = _run_compare_and_wait(window, qapp, f"a{i}\nsame\n", f"A{i}\nsame\n")
        assert ok, f"comparison #{i} did not complete"
        assert window._last_result.statistics.modified == 1
        # The thread identity must never change between jobs -- there is
        # exactly one persistent worker thread for the app's lifetime,
        # never a freshly created one per comparison.
        assert id(window._compare_thread) == thread_identity
        assert window._compare_thread.isRunning()


def test_repeated_comparisons_with_navigation_between_them(window, qapp):
    for i in range(5):
        ok = _run_compare_and_wait(
            window, qapp, f"a{i}\nb\nc{i}\nd\n", f"A{i}\nb\nC{i}\nd\n"
        )
        assert ok, f"comparison #{i} did not complete"
        window.first_diff_action.trigger()
        window.next_diff_action.trigger()
        window.prev_diff_action.trigger()
        window.last_diff_action.trigger()
        assert window._last_result.statistics.modified == 2


def test_cancel_then_immediate_new_comparison_completes(window, qapp):
    big_a = "\n".join(str(i) for i in range(200000))
    big_b = "\n".join(str(i) + "x" for i in range(200000))
    window.source_a_panel.set_text(big_a)
    window.source_b_panel.set_text(big_b)
    window.compare_action.trigger()

    # Cancel almost immediately, then wait for cancellation to settle.
    deadline = time.monotonic() + 5.0
    window._cancel_comparison()
    while time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
        if window.compare_action.isEnabled() and not window.cancel_action.isEnabled():
            break
    assert window._last_result is None

    # A fresh comparison right after cancellation must complete normally.
    ok = _run_compare_and_wait(window, qapp, "p\nq\n", "p\nQ\n")
    assert ok, "comparison after cancellation did not complete"
    assert window._last_result.statistics.modified == 1


def test_close_during_active_comparison_does_not_hang(window, qapp):
    big_a = "\n".join(str(i) for i in range(200000))
    big_b = "\n".join(str(i) + "x" for i in range(200000))
    window.source_a_panel.set_text(big_a)
    window.source_b_panel.set_text(big_b)
    window.compare_action.trigger()
    qapp.processEvents()

    start = time.monotonic()
    window.close()
    elapsed = time.monotonic() - start
    # closeEvent's bounded wait caps at 5s per thread; closing must return
    # well within that, not hang indefinitely.
    assert elapsed < 6.0
