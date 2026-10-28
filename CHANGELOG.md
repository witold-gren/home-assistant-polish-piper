# Zmiany

Format: [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/). Numer wersji to wersja
`wyoming-piper` w obrazie; poprawki samej normalizacji na tym samym Piperze dostają dopisek
`-2`, `-3`… (np. `2.5.2-2`).

## [2.5.2-2] - 2026-10-28

### Dodane
- Własna wymowa bez przebudowy obrazu: plik `pronunciations.yaml` w katalogu głosów (`/data`),
  ścieżka do zmiany przez `PL_TTS_PRONUNCIATIONS`, wczytywany na nowo po każdej zmianie.
  Wzór: `pronunciations.example.yaml`.
- Odmiana słów ze słownika wymowy: „Jarvisa” → „Dżarwisa”, „na iPhonie” → „ajfonie”,
  „iPhone'a” → „ajfona”, „Alexę” → „Aleksę”.
- „Jarvis” → „Dżarwis” w słowniku wymowy.
- Sekcja „Konfiguracja” w README (spis treści linkował do niej, a jej nie było) i FAQ dla
  własnej wymowy.

### Zmienione
- „ppm” czytane jako skrót: „tysiąc dwieście pięćdziesiąt ppm” zamiast „części na milion”.

### Poprawione
- Tysiące w przypadkach zależnych: „do 1000 km” → „do tysiąca kilometrów” (było „do tysiąc”).
- Przedział „od 400 do 1000 ppm”: pierwsza liczba też w dopełniaczu („od czterystu”).
- Jednostki nieodmienne (ppm) po przyimku: „do 5 ppm” → „do pięciu ppm”.
- 434 testy.

## [2.5.2] - 2026-10-24

Pierwsze publiczne wydanie: `wyoming-piper` 2.5.2 (silnik `piper-tts` 1.8.0), Morfeusz 2
ze słownikiem SGJP 20261018. Wcześniejsze etapy prac (wersje 1–3 z października 2026) opisuje
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
