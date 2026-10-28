"""Start wyoming-piper with Polish text normalization in front of synthesis.

Same arguments as `python -m wyoming_piper`. Two hooks in PiperEventHandler:
- handle_event: a whole non-streaming `synthesize` text is normalized before the
  sentence splitter sees it (so "ul. Kwiatowa" or "20.10.2026" are not split);
- _handle_synthesize: every sentence, which also covers the streaming mode
  (synthesize-start/chunk/stop). normalize() is idempotent, so the second pass
  over already normalized text changes nothing.
Own pronunciations come from PL_TTS_PRONUNCIATIONS (default
/data/pronunciations.yaml) and are reloaded when the file changes.
"""

from __future__ import annotations

import logging
import os

from wyoming.event import Event
from wyoming.tts import Synthesize
from wyoming_piper import __main__ as piper_main
from wyoming_piper.handler import PiperEventHandler

from .normalize import normalize, set_user_pronunciations
from .pronunciations import UserPronunciations

_LOGGER = logging.getLogger("pl_tts")
_ENABLED = os.environ.get("PL_TTS_NORMALIZE", "1").lower() not in ("0", "false", "no", "off")
_USER_PRONUNCIATIONS = UserPronunciations()


def _normalized(text: str) -> str:
    if not _ENABLED or not text:
        return text
    try:
        entries = _USER_PRONUNCIATIONS.refresh()
        if entries is not None:
            set_user_pronunciations(entries)
        result = normalize(text)
    except Exception:  # never lose speech because of a normalization bug
        _LOGGER.exception("Normalization failed, using original text: %r", text)
        return text
    if result != text:
        _LOGGER.info("normalize: %r -> %r", text, result)
    return result


_orig_handle_event = PiperEventHandler.handle_event
_orig_handle_synthesize = PiperEventHandler._handle_synthesize


async def _handle_event(self: PiperEventHandler, event: Event) -> bool:
    if Synthesize.is_type(event.type) and not self.is_streaming:
        synthesize = Synthesize.from_event(event)
        synthesize.text = _normalized(synthesize.text)
        event = synthesize.event()
    return await _orig_handle_event(self, event)


async def _handle_synthesize(self: PiperEventHandler, synthesize: Synthesize, *args, **kwargs) -> bool:
    text = _normalized(synthesize.text)
    if text != synthesize.text:
        synthesize = Synthesize(text=text, voice=synthesize.voice)
    return await _orig_handle_synthesize(self, synthesize, *args, **kwargs)


PiperEventHandler.handle_event = _handle_event  # type: ignore[method-assign]
PiperEventHandler._handle_synthesize = _handle_synthesize  # type: ignore[method-assign]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        piper_main.run()
    except KeyboardInterrupt:
        pass
