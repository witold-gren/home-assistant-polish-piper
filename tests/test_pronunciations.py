"""Own pronunciations from a YAML file (PL_TTS_PRONUNCIATIONS)."""

import os
from pathlib import Path

import pytest

from pl_tts import normalize
from pl_tts.normalize import set_user_pronunciations
from pl_tts.pronunciations import UserPronunciations, load_file


@pytest.fixture(autouse=True)
def _reset_pronunciations():
    yield
    set_user_pronunciations({})


def _write(path: Path, text: str, mtime: float) -> None:
    path.write_text(text, encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_user_word_with_endings() -> None:
    set_user_pronunciations({"Kaczmarczyk": "Kaczmarczyk", "Alexa": "Aleksa", "Nest": "Nest"})
    assert normalize("Alexa, zapytaj Alexę") == "Aleksa, zapytaj Aleksę"
    assert normalize("Powiedz Alexie, nie ma Alexy, z Alexą, Alexo!") == "Powiedz Aleksie, nie ma Aleksy, z Aleksą, Alekso!"


def test_user_word_overrides_builtin_written_differently() -> None:
    set_user_pronunciations({"jarvis": "Jarwis"})
    assert normalize("Hej Jarvis, zapytaj Jarvisa") == "Hej Jarwis, zapytaj Jarwisa"


def test_user_full_form_wins_over_ending() -> None:
    set_user_pronunciations({"Home Assistancie": "Hołm Asystencie"})
    assert normalize("w Home Assistancie") == "w Hołm Asystencie"
    assert normalize("Home Assistant działa") == "Hołm Asystent działa"


def test_reset_restores_builtins() -> None:
    set_user_pronunciations({"Jarvis": "Jarwis"})
    set_user_pronunciations({})
    assert normalize("Jarvis") == "Dżarwis"


def test_user_word_is_idempotent() -> None:
    set_user_pronunciations({"Alexa": "Aleksa"})
    once = normalize("Zapytaj Alexę o Jarvisa")
    assert normalize(once) == once


def test_load_file(tmp_path: Path) -> None:
    path = tmp_path / "pronunciations.yaml"
    path.write_text('# komentarz\nJarvis: Dżarwis\n"1:1": łan on łan\n  \n', encoding="utf-8")
    assert load_file(path) == {"Jarvis": "Dżarwis", "1:1": "łan on łan"}


def test_load_file_skips_entries_that_are_not_text(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = tmp_path / "pronunciations.yaml"
    # unquoted 1:1 is a number in YAML 1.1, an empty value is None
    path.write_text("1:1: łan on łan\nPusty:\nLista: [a, b]\nAlexa: Aleksa\n", encoding="utf-8")
    assert load_file(path) == {"Alexa": "Aleksa"}
    assert caplog.text.count("skipping") == 3


@pytest.mark.parametrize("text", ["", "# tylko komentarz\n"])
def test_load_empty_file(tmp_path: Path, text: str) -> None:
    path = tmp_path / "pronunciations.yaml"
    path.write_text(text, encoding="utf-8")
    assert load_file(path) == {}


def test_load_missing_file(tmp_path: Path) -> None:
    assert load_file(tmp_path / "missing.yaml") == {}


@pytest.mark.parametrize("text", ["- Jarvis\n- Alexa\n", "Jarvis: [Dżarwis\n", "just text\n"])
def test_load_invalid_file(tmp_path: Path, text: str) -> None:
    path = tmp_path / "pronunciations.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load_file(path)


def test_refresh_follows_file_changes(tmp_path: Path) -> None:
    path = tmp_path / "pronunciations.yaml"
    user = UserPronunciations(path)
    assert user.refresh() is None  # no file from the start: built-ins only

    _write(path, "Alexa: Aleksa\n", 1000)
    assert user.refresh() == {"Alexa": "Aleksa"}
    assert user.refresh() is None  # unchanged

    _write(path, "Alexa: Aleksa\nNest: Nest\n", 2000)
    assert user.refresh() == {"Alexa": "Aleksa", "Nest": "Nest"}

    _write(path, "Alexa: [broken\n", 3000)
    assert user.refresh() is None  # broken file: previous entries stay

    path.unlink()
    assert user.refresh() == {}  # removed: back to built-ins


def test_path_from_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PL_TTS_PRONUNCIATIONS", str(tmp_path / "own.yaml"))
    assert UserPronunciations().path == tmp_path / "own.yaml"
    monkeypatch.delenv("PL_TTS_PRONUNCIATIONS")
    assert UserPronunciations().path == Path("/data/pronunciations.yaml")


def test_run_uses_user_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from pl_tts import run

    path = tmp_path / "pronunciations.yaml"
    monkeypatch.setattr(run, "_USER_PRONUNCIATIONS", UserPronunciations(path))
    assert run._normalized("Hej Alexa") == "Hej Alexa"
    _write(path, "Alexa: Aleksa\n", 1000)
    assert run._normalized("Hej Alexa") == "Hej Aleksa"
    path.unlink()
    assert run._normalized("Hej Alexa") == "Hej Alexa"


def test_example_file_is_valid() -> None:
    example = Path(__file__).resolve().parent.parent / "pronunciations.example.yaml"
    if not example.exists():  # tests mounted without the repo root
        pytest.skip("pronunciations.example.yaml not available")
    entries = load_file(example)
    assert entries["Jarvis"] == "Dżarwis"
    assert entries["1:1"] == "łan on łan"
