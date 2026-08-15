from app.config.settings import load_settings, save_settings
from app.core.enums import ComparisonMode, Theme
from app.core.models import ApplicationSettings, ComparisonSettings


def test_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.get_config_dir", lambda: tmp_path)

    settings = ApplicationSettings(
        theme=Theme.DARK,
        font_size=14,
        comparison_settings=ComparisonSettings(mode=ComparisonMode.WORD, case_sensitive=False),
    )
    save_settings(settings)

    loaded = load_settings()
    assert loaded.theme == Theme.DARK
    assert loaded.font_size == 14
    assert loaded.comparison_settings.mode == ComparisonMode.WORD
    assert loaded.comparison_settings.case_sensitive is False


def test_load_settings_falls_back_to_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.get_config_dir", lambda: tmp_path)
    loaded = load_settings()
    assert loaded.theme == Theme.LIGHT


def test_load_settings_falls_back_on_corrupted_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.get_config_dir", lambda: tmp_path)
    (tmp_path / "settings.json").write_text("{not valid json", encoding="utf-8")
    loaded = load_settings()
    assert loaded.theme == Theme.LIGHT
