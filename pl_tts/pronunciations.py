"""Pronunciation overrides: foreign words and names spelled the Polish way.

espeak-ng (Polish) reads English words letter by letter or with Polish rules
("Review" -> "rewiew"). Each entry is written as it should sound in Polish;
matching is case-insensitive and whole-word, Polish case endings are carried
over ("Jarvisa" -> "Dżarwisa", see normalize.py). Add words heard wrong in
`docker logs piper | grep normalize`. Own words without rebuilding the image go
to a YAML file (default /data/pronunciations.yaml), read by UserPronunciations.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

_LOGGER = logging.getLogger("pl_tts")

PRONUNCIATIONS: dict[str, str] = {
    # Work / calendar
    "standup": "stendap",
    "stand-up": "stendap",
    "review": "riwju",
    "meeting": "miting",
    "call": "kol",
    "sync": "sink",
    "PR": "pi ar",
    "1:1": "łan on łan",
    # Home / devices
    "Home Assistant": "Hołm Asystent",
    "HomePod": "Hołm Pod",
    "HomeKit": "Hołm Kit",
    "iPhone": "ajfon",
    "iPad": "ajpad",
    "MacBook": "Mekbuk",
    "Apple": "Epl",
    "Google": "Gugl",
    "YouTube": "Jutub",
    "Netflix": "Netfliks",
    "Spotify": "Spotifaj",
    "Wi-Fi": "łifi",
    "WiFi": "łifi",
    "Bluetooth": "blutut",
    "smart": "smart",
    "Volvo": "Wolwo",
    "Frigate": "Frigejt",
    "Reolink": "Riolink",
    "eufy": "jufi",
    "Netatmo": "Netatmo",
    "Philips Hue": "Filips Hju",
    "Hue": "Hju",
    "Jarvis": "Dżarwis",
    "OK": "okej",
    "e-mail": "imejl",
    "email": "imejl",
}


def load_file(path: str | Path) -> dict[str, str]:
    """Read a YAML mapping "word: spoken form". Entries that are not text are
    skipped with a warning; a missing file gives no entries. Raises ValueError
    when the file is not valid YAML or not a mapping."""
    import yaml  # in the image (wyoming-piper dependency); checked at build time

    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as err:
        raise ValueError(f"{path}: {err}") from err
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping 'word: spoken form', got {type(data).__name__}")
    entries: dict[str, str] = {}
    for word, spoken in data.items():
        # 1:1 or 12:30 unquoted are numbers in YAML - they must be quoted
        if not isinstance(word, str) or not isinstance(spoken, str) or not word.strip() or not spoken.strip():
            _LOGGER.warning("%s: skipping %r: %r (word and spoken form must be quoted text)", path, word, spoken)
            continue
        entries[word.strip()] = spoken.strip()
    return entries


class UserPronunciations:
    """Own pronunciations from a YAML file, reloaded when the file changes, so
    edits work without restarting the container."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.environ.get("PL_TTS_PRONUNCIATIONS", "/data/pronunciations.yaml"))
        self._mtime: float | None = None

    def refresh(self) -> dict[str, str] | None:
        """New entries when the file was added, changed or removed since the last
        call, otherwise None. A broken file is logged and the previous entries stay."""
        try:
            mtime: float | None = self.path.stat().st_mtime
        except OSError:
            mtime = None
        if mtime == self._mtime:
            return None
        self._mtime = mtime
        if mtime is None:
            return {}
        try:
            entries = load_file(self.path)
        except ValueError:
            _LOGGER.exception("Own pronunciations not loaded, keeping the previous ones")
            return None
        _LOGGER.info("Loaded %d own pronunciations from %s", len(entries), self.path)
        return entries
