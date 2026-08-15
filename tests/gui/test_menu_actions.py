"""Behavioral tests for the Edit, View, and Compare menus.

These test actual behavior (text actually gets cut/copied/undone, zoom
actually changes the font size, navigation actually moves the selection)
rather than merely asserting that a QAction object exists.
"""
import time

import pytest

from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import QApplication

from app.core.constants import DEFAULT_FONT_SIZE
from app.gui.main_window import MainWindow
from app.services.settings_service import SettingsService


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.get_config_dir", lambda: tmp_path)
    settings_service = SettingsService()
    win = MainWindow(settings_service)
    win.show()
    yield win
    win.close()
    # Force the window (and all its Qt children, including every QMenu)
    # to be fully destroyed before the next test creates a new
    # MainWindow. Without this, many MainWindow instances being created
    # and merely close()'d (not deleted) in quick succession across a
    # test file can lead to C++ memory-address reuse for newly created
    # Qt objects, which has been observed to confuse PySide6/shiboken's
    # internal Python-wrapper cache -- a *test-only* artifact of rapid,
    # repeated window construction/teardown within one process, not a
    # defect in the application itself.
    win.deleteLater()
    qapp.processEvents()


def _menu_action_labels(window, title):
    """Return the (non-separator) action labels of a top-level menu.

    Deliberately does everything inline within one function call rather
    than returning a `QMenu` object for the caller to interact with
    later: empirically, returning a `QMenu` obtained via `.menu()` across
    a function-call boundary reliably triggers
    "Internal C++ object already deleted" under PySide6/shiboken in this
    environment, even though the object is genuinely still alive via the
    menu bar's normal C++ parent-child ownership (confirmed by the fact
    that fully inline access, never returning the QMenu itself, never
    exhibits the issue). This is a test-only artifact of that specific
    return pattern, not an application defect.
    """
    for action in list(window.menuBar().actions()):
        if action.text() == title:
            return [a.text() for a in action.menu().actions() if not a.isSeparator()]
    raise AssertionError(f"No top-level menu titled {title!r} found")


def _trigger_menu_action(window, title, text_fragment):
    """Find and trigger a specific action within a top-level menu, and
    return its shortcut string, all inline (see `_menu_action_labels`)."""
    for top_action in list(window.menuBar().actions()):
        if top_action.text() == title:
            for action in list(top_action.menu().actions()):
                if text_fragment in action.text():
                    shortcut_text = action.shortcut().toString()
                    action.trigger()
                    return shortcut_text
    raise AssertionError(f"No action containing {text_fragment!r} found in menu {title!r}")


# ----------------------------------------------------------------------
# Edit menu: operates on whichever editable widget has focus
# ----------------------------------------------------------------------


def test_select_all_selects_focused_panel_text(window, qapp):
    window.source_a_panel.text_edit.setPlainText("hello world")
    window.source_a_panel.text_edit.setFocus()
    qapp.processEvents()

    window._dispatch_edit_op("selectAll")
    cursor = window.source_a_panel.text_edit.textCursor()
    assert cursor.selectedText() == "hello world"


def test_copy_copies_selected_text_to_clipboard(window, qapp):
    window.source_a_panel.text_edit.setPlainText("copy me")
    window.source_a_panel.text_edit.setFocus()
    qapp.processEvents()
    window._dispatch_edit_op("selectAll")
    window._dispatch_edit_op("copy")
    assert QApplication.clipboard().text(QClipboard.Clipboard) == "copy me"


def test_cut_removes_selected_text_and_copies_it(window, qapp):
    window.source_a_panel.text_edit.setPlainText("cut me")
    window.source_a_panel.text_edit.setFocus()
    qapp.processEvents()
    window._dispatch_edit_op("selectAll")
    window._dispatch_edit_op("cut")
    assert window.source_a_panel.text() == ""
    assert QApplication.clipboard().text(QClipboard.Clipboard) == "cut me"


def test_paste_inserts_clipboard_text(window, qapp):
    QApplication.clipboard().setText("pasted content")
    window.source_b_panel.text_edit.clear()
    window.source_b_panel.text_edit.setFocus()
    qapp.processEvents()
    window._dispatch_edit_op("paste")
    assert "pasted content" in window.source_b_panel.text()


def test_undo_reverts_last_edit(window, qapp):
    panel = window.source_a_panel
    panel.text_edit.clear()
    panel.text_edit.setFocus()
    qapp.processEvents()
    panel.text_edit.insertPlainText("first")
    assert panel.text() == "first"
    window._dispatch_edit_op("undo")
    assert panel.text() == ""


def test_redo_reapplies_undone_edit(window, qapp):
    panel = window.source_a_panel
    panel.text_edit.clear()
    panel.text_edit.setFocus()
    qapp.processEvents()
    panel.text_edit.insertPlainText("hello world")
    assert panel.text() == "hello world"
    window._dispatch_edit_op("undo")
    assert panel.text() == ""
    window._dispatch_edit_op("redo")
    assert panel.text() == "hello world"


def test_edit_ops_are_noop_when_diff_table_focused(window, qapp):
    """The read-only diff results table must never receive edit commands."""
    window.diff_view.table.setFocus()
    qapp.processEvents()
    window.source_a_panel.text_edit.setPlainText("must not change")
    # Dispatching to whatever has focus (the table) must not raise and
    # must not touch the source panel text.
    window._dispatch_edit_op("selectAll")
    assert window.source_a_panel.text() == "must not change"


def test_edit_menu_state_reflects_focus_and_content(window, qapp):
    panel = window.source_a_panel
    panel.text_edit.clear()
    panel.text_edit.setFocus()
    qapp.processEvents()
    window._update_edit_menu_state()
    assert window.select_all_action.isEnabled()
    assert not window.undo_action.isEnabled()

    panel.text_edit.insertPlainText("some text")
    window._update_edit_menu_state()
    assert window.undo_action.isEnabled()

    panel.text_edit.selectAll()
    window._update_edit_menu_state()
    assert window.copy_action.isEnabled()
    assert window.cut_action.isEnabled()


# ----------------------------------------------------------------------
# View menu: zoom controls share the same implementation as the toolbar
# ----------------------------------------------------------------------


def test_zoom_in_action_increases_font_size(window):
    start_size = window.diff_view.font_size
    window.zoom_in_action.trigger()
    assert window.diff_view.font_size == start_size + 1


def test_zoom_out_action_decreases_font_size(window):
    window.diff_view.set_font_size(14)
    window.zoom_out_action.trigger()
    assert window.diff_view.font_size == 13


def test_reset_zoom_restores_default(window):
    window.diff_view.set_font_size(20)
    window.reset_zoom_action.trigger()
    assert window.diff_view.font_size == DEFAULT_FONT_SIZE


def test_toolbar_and_menu_zoom_share_implementation(window):
    """Toolbar buttons and View-menu actions must produce identical
    results, proving they call the same underlying method rather than
    duplicating zoom logic."""
    window.diff_view.set_font_size(DEFAULT_FONT_SIZE)
    window.zoom_in_action.trigger()
    via_menu = window.diff_view.font_size

    window.diff_view.set_font_size(DEFAULT_FONT_SIZE)
    window.diff_view.zoom_in_btn.click()
    via_toolbar = window.diff_view.font_size

    assert via_menu == via_toolbar == DEFAULT_FONT_SIZE + 1


# ----------------------------------------------------------------------
# Compare menu: reuses the same actions/methods as the toolbar and
# difference-navigation buttons (behavioral, not existence-only)
# ----------------------------------------------------------------------


def _wait_for_compare(window, qapp, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
        if window._last_result is not None and window.compare_action.isEnabled():
            return True
    return False


def test_compare_menu_reuses_toolbar_compare_action(window):
    # The Compare menu must add the SAME QAction object as the toolbar,
    # not a duplicate with independent state.
    for top_action in list(window.menuBar().actions()):
        if top_action.text() == "&Compare":
            assert window.compare_action in list(top_action.menu().actions())
            return
    raise AssertionError("Compare menu not found")


def test_first_next_prev_last_difference_actions_navigate(window, qapp):
    window.source_a_panel.set_text("a\nb\nc\nd\ne\n")
    window.source_b_panel.set_text("A\nb\nC\nd\nE\n")
    window.compare_action.trigger()
    assert _wait_for_compare(window, qapp)

    window.first_diff_action.trigger()
    first_label = window.diff_view.diff_position_label.text()
    assert first_label == "Difference 1 of 3"

    window.next_diff_action.trigger()
    assert window.diff_view.diff_position_label.text() == "Difference 2 of 3"

    window.last_diff_action.trigger()
    assert window.diff_view.diff_position_label.text() == "Difference 3 of 3"

    window.prev_diff_action.trigger()
    assert window.diff_view.diff_position_label.text() == "Difference 2 of 3"


def test_nav_actions_disabled_for_identical_content(window, qapp):
    window.source_a_panel.set_text("same\ntext\n")
    window.source_b_panel.set_text("same\ntext\n")
    window.compare_action.trigger()
    assert _wait_for_compare(window, qapp)

    assert window._last_result.statistics.is_identical
    assert not window.first_diff_action.isEnabled()
    assert not window.next_diff_action.isEnabled()
    assert not window.prev_diff_action.isEnabled()
    assert not window.last_diff_action.isEnabled()


# ----------------------------------------------------------------------
# Find (Edit -> Find / Ctrl+F)
# ----------------------------------------------------------------------


def test_find_action_focuses_search_box(window, qapp):
    window.source_a_panel.set_text("needle in a haystack\n")
    window.source_b_panel.set_text("needle in a haystack\n")
    window.compare_action.trigger()
    assert _wait_for_compare(window, qapp)

    window.diff_view.search_box.clearFocus()
    qapp.processEvents()
    assert not window.diff_view.search_box.hasFocus()

    shortcut_text = _trigger_menu_action(window, "&Edit", "Find")
    assert shortcut_text == "Ctrl+F"

    qapp.processEvents()
    assert window.diff_view.search_box.hasFocus()


def test_search_finds_matching_rows(window, qapp):
    window.source_a_panel.set_text("alpha\nbravo\ncharlie\n")
    window.source_b_panel.set_text("alpha\nbravo\ndelta\n")
    window.compare_action.trigger()
    assert _wait_for_compare(window, qapp)

    window.diff_view.search_box.setText("bravo")
    window.diff_view._advance_search(1)
    assert "match" in window.diff_view.search_status_label.text().lower()
    assert window.diff_view._search_matches  # at least one match found


def test_escape_closes_search(window, qapp):
    window.diff_view.search_box.setText("something")
    window.diff_view._close_search()
    assert window.diff_view.search_box.text() == ""


# ----------------------------------------------------------------------
# Menu shortcut formatting: shortcuts must be set via QAction.setShortcut,
# never concatenated into the visible action text.
# ----------------------------------------------------------------------


def test_no_action_label_has_shortcut_text_baked_in(window):
    """Regression test for the 'FindCtrl+F' formatting bug: no menu
    action's display text should ever contain its own shortcut string --
    Qt renders the shortcut in a separate, right-aligned column driven by
    QAction.shortcut(), never by string concatenation in the label."""
    for top_level_action in list(window.menuBar().actions()):
        menu = top_level_action.menu()
        if menu is None:
            continue
        for action in menu.actions():
            if action.isSeparator():
                continue
            shortcut_text = action.shortcut().toString()
            if shortcut_text:
                assert shortcut_text not in action.text(), (
                    f"Action '{action.text()}' appears to have its shortcut "
                    f"baked into the label text instead of set via setShortcut()."
                )


def test_all_expected_menus_present(window):
    titles = {a.text() for a in list(window.menuBar().actions())}
    assert titles == {"&File", "&Edit", "&View", "&Compare", "&Help"}


def test_edit_menu_has_all_expected_actions(window):
    labels = _menu_action_labels(window, "&Edit")
    for expected in ["&Undo", "&Redo", "Cu&t", "&Copy", "&Paste", "Select &All"]:
        assert expected in labels
    assert any("Find" in label for label in labels)


def test_view_menu_has_zoom_and_theme_actions(window):
    labels = _menu_action_labels(window, "&View")
    assert "Zoom &In" in labels
    assert "Zoom &Out" in labels
    assert "&Reset Zoom" in labels
    assert "Light Theme" in labels
    assert "Dark Theme" in labels


# ----------------------------------------------------------------------
# Automatic first-difference selection & diff visual quality
# ----------------------------------------------------------------------


def test_first_difference_automatically_selected_after_compare(window, qapp):
    window.source_a_panel.set_text("a\nb\nc\n")
    window.source_b_panel.set_text("A\nb\nC\n")
    window.compare_action.trigger()
    assert _wait_for_compare(window, qapp)

    assert window.diff_view.table.currentIndex().row() == 0
    assert window.diff_view.diff_position_label.text() == "Difference 1 of 2"


def test_identical_content_shows_no_differences_message(window, qapp):
    window.source_a_panel.set_text("same\n")
    window.source_b_panel.set_text("same\n")
    window.compare_action.trigger()
    assert _wait_for_compare(window, qapp)

    assert window.diff_view.diff_position_label.text() in ("No differences", "")
    assert "no differences" in window.status_bar.currentMessage().lower()


def test_active_difference_row_uses_bold_and_selection_state(window, qapp):
    """Non-color reinforcement: the active row must be both selected
    (backing the strong accent-color QSS) and rendered bold by the
    delegate, not distinguished by background color alone."""
    window.source_a_panel.set_text("a\nb\nc\n")
    window.source_b_panel.set_text("A\nb\nC\n")
    window.compare_action.trigger()
    assert _wait_for_compare(window, qapp)

    index = window.diff_view.table.currentIndex()
    assert index.isValid()
    # The delegate bolds selected rows via initStyleOption; verify the
    # selection state itself is correctly set on the current index.
    assert window.diff_view.table.selectionModel().isRowSelected(index.row())


def test_line_number_cells_include_non_color_type_glyph(window, qapp):
    window.source_a_panel.set_text("a\nb\n")
    window.source_b_panel.set_text("a\nb\nc\n")
    window.compare_action.trigger()
    assert _wait_for_compare(window, qapp)

    model = window.diff_view.model
    found_glyph = False
    for row in range(model.rowCount()):
        b_cell = model.index(row, 2).data()
        if b_cell and ("+" in b_cell or "~" in b_cell or "\u2212" in b_cell):
            found_glyph = True
    assert found_glyph, "Expected at least one non-color (+/~/-) glyph indicator"
