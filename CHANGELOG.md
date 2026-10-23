# Zmiany

Format: [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/), wersje: [SemVer](https://semver.org/lang/pl/).

## [0.1.0] - 2026-10-24

Pierwsze publiczne wydanie. Wcześniejsze etapy prac (wersje 1–3 z października 2026) opisuje
README, rozdział „Jak do tego doszliśmy”.

### Dodane
- Obraz na bazie `rhasspy/wyoming-piper:2.5.2` z polską normalizacją tekstu (`pl_tts`) przed
  syntezą: godziny, daty, czas z HA, jednostki, kwoty, liczby ujemne i dziesiętne, ułamki,
  wyniki, liczebniki porządkowe i rzymskie, skróty, telefony, e-maile, adresy WWW, emotikony.
- Zgodność liczebnika z rzeczownikiem w rodzaju i przypadku dzięki Morfeuszowi 2 (IPI PAN,
  słownik SGJP), kompilowanemu w obrazie (także arm64).
- Słownik wymowy obcych słów i nazw (`pl_tts/pronunciations.py`).
- `PL_TTS_NORMALIZE=0` wyłącza normalizację bez przebudowy; każda zmiana tekstu trafia do
  dziennika.
- Narzędzie `tools/ha_audit.py` do sprawdzenia normalizacji na stanach encji z Home Assistant.
- 378 testów.
