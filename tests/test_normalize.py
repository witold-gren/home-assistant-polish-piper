"""Expected spoken forms. Each wrong reading found in practice gets a case here."""

import pytest

from pl_tts import normalize
from pl_tts.numbers import cardinal, declined, ordinal

CASES = [
    # --- times (espeak: "o dziewięć zero pięć", "czternaście trzydzieści")
    ("Spotkanie o 9:05.", "Spotkanie o dziewiątej pięć."),
    ("Jest 14:30.", "Jest czternasta trzydzieści."),
    ("O 17:30 Kuba ma robotykę.", "O siedemnastej trzydzieści Kuba ma robotykę."),
    ("Spotkanie o 10:00", "Spotkanie o dziesiątej"),
    ("do 21:15", "do dwudziestej pierwszej piętnaście"),
    ("przed 12:00", "przed dwunastą"),
    ("Godzina 9:05", "Godzina dziewiąta zero pięć"),
    ("0:15", "zero piętnaście"),
    ("10:00-10:30 Review PR", "od dziesiątej do dziesiątej trzydzieści riwju pi ar"),
    ("od 17:30 - 18:00", "od siedemnastej trzydzieści do osiemnastej"),
    # --- dates (espeak: "dwadzieścia dziesięć dwa tysiące...")
    ("Dziś jest 20.10.2026.", "Dziś jest dwudziestego października dwa tysiące dwudziestego szóstego roku."),
    ("Wtorek 21.10 o 17:30", "Wtorek dwudziestego pierwszego października o siedemnastej trzydzieści"),
    ("21 października", "dwudziestego pierwszego października"),
    ("1 stycznia 2027 r.", "pierwszego stycznia dwa tysiące dwudziestego siódmego roku"),
    ("w 2026 r.", "w dwa tysiące dwudziestym szóstym roku"),
    ("2026-10-20T15:30:00+02:00", "dwudziestego października dwa tysiące dwudziestego szóstego roku, piętnasta trzydzieści"),
    ("31.12.1999", "trzydziestego pierwszego grudnia tysiąc dziewięćset dziewięćdziesiątego dziewiątego roku"),
    ("3.03.2000", "trzeciego marca dwutysięcznego roku"),
    # --- temperatures (espeak: "sześć stopień ce", minus dropped)
    ("Na zewnątrz 6°C.", "Na zewnątrz sześć stopni Celsjusza."),
    ("Temperatura -3,5°C.", "Temperatura minus trzy i pół stopnia Celsjusza."),
    ("1 °C", "jeden stopień Celsjusza"),
    ("22°C", "dwadzieścia dwa stopnie Celsjusza"),
    ("21.75 °C", "dwadzieścia jeden przecinek osiem stopnia Celsjusza"),
    ("0°C", "zero stopni Celsjusza"),
    # --- units
    ("Jedzie 50 km/h.", "Jedzie pięćdziesiąt kilometrów na godzinę."),
    ("Waży 72 kg i ma 180 cm.", "Waży siedemdziesiąt dwa kilogramy i ma sto osiemdziesiąt centymetrów."),
    ("Zostało 40 km.", "Zostało czterdzieści kilometrów."),
    ("1 km", "jeden kilometr"),
    ("Bateria 92%.", "Bateria dziewięćdziesiąt dwa procent."),
    ("3,5%", "trzy i pół procent"),
    ("Ciśnienie 1013 hPa", "Ciśnienie tysiąc trzynaście hektopaskali"),
    ("Ciśnienie 1 013 hPa", "Ciśnienie tysiąc trzynaście hektopaskali"),
    ("Zużycie 12,4 kWh", "Zużycie dwanaście przecinek cztery kilowatogodziny"),
    ("2 kWh", "dwie kilowatogodziny"),
    ("Moc 350 W", "Moc trzysta pięćdziesiąt watów"),
    ("230 V", "dwieście trzydzieści woltów"),
    ("Za 2 min", "Za dwie minuty"),
    ("1 min", "jedna minuta"),
    ("5 s", "pięć sekund"),
    ("CO2 850 ppm", "CO2 osiemset pięćdziesiąt części na milion"),
    ("Cena 49,99 zł", "Cena czterdzieści dziewięć złotych dziewięćdziesiąt dziewięć groszy"),
    ("Koszt 11132.14 PLN", "Koszt jedenaście tysięcy sto trzydzieści dwa złote czternaście groszy"),
    ("1 zł", "jeden złoty"),
    ("2,50 zł", "dwa złote pięćdziesiąt groszy"),
    ("5 €", "pięć euro"),
    ("Spalanie 7,5 L/100 km", "Spalanie siedem i pół litra na sto kilometrów"),
    ("Wiatr 3 m/s", "Wiatr trzy metry na sekundę"),
    ("Mieszkanie 64 m²", "Mieszkanie sześćdziesiąt cztery metry kwadratowe"),
    ("Natężenie 450 lx", "Natężenie czterysta pięćdziesiąt luksów"),
    # --- numbers
    ("Mam 2 spotkania, a jutro 5 spotkań.", "Mam dwa spotkania, a jutro pięć spotkań."),
    ("Temperatura spadnie do -5", "Temperatura spadnie do minus pięć"),
    ("pi to 3,14", "pi to trzy przecinek czternaście"),
    ("2026", "dwa tysiące dwadzieścia sześć"),
    # --- numerals agreeing with the noun (gender_lexicon.json, Morfeusz 2)
    ("1 osoba", "jedna osoba"),
    ("2 osoby", "dwie osoby"),
    ("22 osoby", "dwadzieścia dwie osoby"),
    ("5 osób", "pięć osób"),
    ("21 osób", "dwadzieścia jeden osób"),
    ("1 okno", "jedno okno"),
    ("1 dziecko", "jedno dziecko"),
    ("1 spotkanie", "jedno spotkanie"),
    ("1 roleta", "jedna roleta"),
    ("2 rolety", "dwie rolety"),
    ("3 rolety", "trzy rolety"),
    ("32 kamery", "trzydzieści dwie kamery"),
    ("1 telefon", "jeden telefon"),
    ("2 telefony", "dwa telefony"),
    ("2 dzieci", "dwoje dzieci"),
    ("3 dzieci", "troje dzieci"),
    ("5 dzieci", "pięcioro dzieci"),
    ("2 drzwi", "dwoje drzwi"),
    ("2 mężczyzn", "dwóch mężczyzn"),
    ("5 chłopców", "pięciu chłopców"),
    ("21 mężczyzn", "dwudziestu jeden mężczyzn"),
    ("12 ludzi", "dwunastu ludzi"),
    ("1 wiadomość", "jedna wiadomość"),
    ("2 nowe wiadomości", "dwie nowe wiadomości"),
    ("3 otwarte okna", "trzy otwarte okna"),
    ("2 telefony Anny", "dwa telefony Anny"),
    ("2 córki i 3 synów", "dwie córki i trzech synów"),
    ("Za 2 godziny", "Za dwie godziny"),
    # --- numeral case from the noun and the preposition
    ("1 otwartą roletę", "jedną otwartą roletę"),
    ("z 2 osobami", "z dwiema osobami"),
    ("z 2 telefonami", "z dwoma telefonami"),
    ("z 22 osobami", "z dwudziestoma dwiema osobami"),
    ("bez 5 osób", "bez pięciu osób"),
    ("dla 2 osób", "dla dwóch osób"),
    ("dla 21 osób", "dla dwudziestu jeden osób"),
    ("do 3 lamp", "do trzech lamp"),
    ("o 3 kamerach", "o trzech kamerach"),
    ("po 3 dniach", "po trzech dniach"),
    ("przed 2 godzinami", "przed dwiema godzinami"),
    ("2 mężczyźni", "dwaj mężczyźni"),
    ("z 12 ludźmi", "z dwunastoma ludźmi"),
    ("o 3 dzieciach", "o trojgu dzieciach"),
    # --- live Morfeusz: any noun, adjective/noun ambiguity
    ("2 skarpety", "dwie skarpety"),
    ("1 kanapę", "jedną kanapę"),
    ("z 2 pralkami", "z dwiema pralkami"),
    ("z 3 hydraulikami", "z trzema hydraulikami"),
    ("o 2 termostatach", "o dwóch termostatach"),
    ("dla 4 sąsiadów", "dla czterech sąsiadów"),
    ("2 księży", "dwóch księży"),
    ("2 zmywarki i 3 lodówki", "dwie zmywarki i trzy lodówki"),
    # --- genitive from verbs and negation
    ("Brakuje 2 osób.", "Brakuje dwóch osób."),
    ("Nie ma 5 lamp.", "Nie ma pięciu lamp."),
    ("Ponad 5 osób.", "Ponad pięć osób."),
    # --- quantities in oblique cases
    ("Do 5 km stąd.", "Do pięciu kilometrów stąd."),
    ("Po 3 min wyłącz.", "Po trzech minutach wyłącz."),
    ("Przed 2 h było ciepło.", "Przed dwiema godzinami było ciepło."),
    # --- ranges
    ("Za 2-3 dni.", "Za dwa, trzy dni."),
    ("2-3 osoby", "dwie, trzy osoby"),
    ("Brakuje 2-3 osób.", "Brakuje dwóch, trzech osób."),
    ("2-3 mężczyzn", "dwóch, trzech mężczyzn"),
    ("5-10 minut", "pięć, dziesięć minut"),
    ("Od 10-15 km.", "Od dziesięciu, piętnastu kilometrów."),
    ("Temperatura 20-22°C", "Temperatura dwadzieścia, dwadzieścia dwa stopnie Celsjusza"),
    # --- times with a dot, "godz."
    ("Spotkanie o 17.30.", "Spotkanie o siedemnastej trzydzieści."),
    ("W godz. 17.30-18.00", "W godzinach od siedemnastej trzydzieści do osiemnastej"),
    ("O godz. 17.30 spotkanie.", "O godzinie siedemnastej trzydzieści spotkanie."),
    ("Do godz. 21:15", "Do godziny dwudziestej pierwszej piętnaście"),
    # --- ordinals and roman numerals
    ("Zajął 3. miejsce.", "Zajął trzecie miejsce."),
    ("Mieszkam na 2. piętrze.", "Mieszkam na drugim piętrze."),
    ("W XXI wieku.", "W dwudziestym pierwszym wieku."),
    ("Jan Paweł II był papieżem.", "Jan Paweł drugi był papieżem."),
    # --- scores and fractions
    ("Wynik 2:1 dla Legii.", "Wynik dwa do jednego dla Legii."),
    ("Mecz 3:0.", "Mecz trzy do zera."),
    ("Zostało 2/3 baterii i 1/4 wody, 5/8 cala.", "Zostało dwie trzecie baterii i jedna czwarta wody, pięć ósmych cala."),
    # --- phones, addresses, emojis, pronunciations
    ("Zadzwoń pod tel. 123 456 789", "Zadzwoń pod telefon sto dwadzieścia trzy, czterysta pięćdziesiąt sześć, siedemset osiemdziesiąt dziewięć"),
    ("+48 600-100-200", "plus czterdzieści osiem, sześćset, sto, dwieście"),
    ("Pisz na jan.kowalski@gmail.com", "Pisz na jan kropka kowalski małpa gmail kropka com"),
    ("Wejdź na https://www.home-assistant.io/docs.", "Wejdź na home-assistant kropka io"),
    ("Super! 🎉 Gotowe 👍", "Super! Gotowe"),
    ("Masz review PR o 10:00 na iPhone.", "Masz riwju pi ar o dziesiątej na ajfon."),
    # --- durations
    ("Pozostało 1:23:45", "Pozostało jedna godzina dwadzieścia trzy minuty czterdzieści pięć sekund"),
    ("Minutnik 0:05:00", "Minutnik pięć minut"),
    ("za 1:01:01", "za jedną godzinę jedną minutę jedną sekundę"),
    ("Trwa 2:00:00", "Trwa dwie godziny"),
    ("Pranie zakończy się za 0:45:00", "Pranie zakończy się za czterdzieści pięć minut"),
    ("Jest 14:30:00", "Jest czternasta trzydzieści"),
    # --- Home Assistant states (tools/ha_audit.py)
    ("2× AAA", "dwa razy AAA"),
    ("CR2450", "CR2450"),
    ("CO2 850 ppm", "CO2 osiemset pięćdziesiąt części na milion"),
    ("a4:c1:38:12:34:56", "a4:c1:38:12:34:56"),
    ("0F8A3C21-1B2C-4D5E-8F90-1A2B3C4D5E6F", "0F8A3C21-1B2C-4D5E-8F90-1A2B3C4D5E6F"),
    ("no_wake_word", "no wake word"),
    ("0 · HOME", "zero, HOME"),
    ("27.32 kg/m2", "dwadzieścia siedem przecinek trzy kilograma na metr kwadratowy"),
    ("0.4 UVI", "zero przecinek cztery w skali UV"),
    ("0.093 dB/m", "zero przecinek zero dziewięć decybela na metr"),
    ("3027.18552 kWh", "trzy tysiące dwadzieścia siedem kilowatogodzin"),
    ("42.347 kWh", "czterdzieści dwa przecinek trzy kilowatogodziny"),
    ("0.571 A", "zero przecinek pięćdziesiąt siedem ampera"),
    ("460.0 ohm", "czterysta sześćdziesiąt omów"),
    ("15min", "piętnaście minut"),
    ("Wersja 2026.10.1", "Wersja dwa tysiące dwadzieścia sześć kropka dziesięć kropka jeden"),
    ("Adres 192.168.1.10", "Adres sto dziewięćdziesiąt dwa kropka sto sześćdziesiąt osiem kropka jeden kropka dziesięć"),
    ("Kwiatowa 24, 31-150 Kraków", "Kwiatowa dwadzieścia cztery, trzydzieści jeden, sto pięćdziesiąt Kraków"),
    ("ul. Kwiatowa 30/2", "ulica Kwiatowa trzydzieści łamane przez dwa"),
    ("2026-10-20T02:01:06.344+00:00", "dwudziestego października dwa tysiące dwudziestego szóstego roku, czwarta zero jeden"),
    ("2026-01-15T12:00:00+00:00", "piętnastego stycznia dwa tysiące dwudziestego szóstego roku, trzynasta"),
    ("2026-10-20 15:30", "dwudziestego października dwa tysiące dwudziestego szóstego roku, piętnasta trzydzieści"),
    # --- abbreviations
    ("ul. Kwiatowa 30", "ulica Kwiatowa trzydzieści"),
    ("np. rolety, światło itd.", "na przykład rolety, światło i tak dalej."),
    ("ok. 40 km", "około czterdziestu kilometrów"),
    ("OK, zrobione", "okej, zrobione"),
    # --- unchanged text
    ("Witaj w domu, Anno!", "Witaj w domu, Anno!"),
    ("Włączam światło w salonie.", "Włączam światło w salonie."),
    ("10 minut temu", "dziesięć minut temu"),
]


@pytest.mark.parametrize(("text", "expected"), CASES)
def test_normalize(text: str, expected: str) -> None:
    assert normalize(text) == expected


@pytest.mark.parametrize(("text", "_"), CASES)
def test_idempotent(text: str, _: str) -> None:
    once = normalize(text)
    assert normalize(once) == once


def test_no_digits_left() -> None:
    sample = "O 9:05, 20.10.2026: -3,5°C, 50 km/h, 92%, 1 013 hPa, 12345678901."  # bez tokenów typu CO2
    assert not any(c.isdigit() for c in normalize(sample))


@pytest.mark.parametrize(
    ("n", "words"),
    [
        (0, "zero"), (11, "jedenaście"), (21, "dwadzieścia jeden"), (100, "sto"),
        (215, "dwieście piętnaście"), (1000, "tysiąc"), (2002, "dwa tysiące dwa"),
        (5000, "pięć tysięcy"), (12000, "dwanaście tysięcy"), (1000000, "milion"),
    ],
)
def test_cardinal(n: int, words: str) -> None:
    assert cardinal(n) == words


@pytest.mark.parametrize(
    ("n", "form", "words"),
    [
        (1, "m_gen", "pierwszego"), (2, "m_gen", "drugiego"), (3, "m_gen", "trzeciego"),
        (21, "m_gen", "dwudziestego pierwszego"), (2026, "m_gen", "dwa tysiące dwudziestego szóstego"),
        (2000, "m_gen", "dwutysięcznego"), (1900, "m_gen", "tysiąc dziewięćsetnego"),
        (3, "f_nom", "trzecia"), (3, "f_gen", "trzeciej"), (12, "f_ins", "dwunastą"),
        (23, "f_ins", "dwudziestą trzecią"), (2, "f_nom", "druga"), (22, "f_gen", "dwudziestej drugiej"),
    ],
)
def test_ordinal(n: int, form: str, words: str) -> None:
    assert ordinal(n, form) == words


@pytest.mark.parametrize(
    ("n", "case", "gender", "words"),
    [
        (1, "acc", "f", "jedną"), (1, "inst", "m3", "jednym"), (1, "acc", "m2", "jednego"),
        (2, "inst", "f", "dwiema"), (2, "inst", "m3", "dwoma"), (2, "dat", "f", "dwóm"),
        (3, "gen", "n", "trzech"), (5, "inst", "f", "pięcioma"), (15, "gen", "f", "piętnastu"),
        (100, "inst", "m3", "stoma"), (500, "gen", "f", "pięciuset"), (25, "inst", "f", "dwudziestoma pięcioma"),
        (2, "nom", "m1", "dwaj"), (2, "acc", "m1", "dwóch"), (5, "nom", "m1", "pięciu"),
        (2, "nom", "col", "dwoje"), (4, "gen", "col", "czworga"), (5, "inst", "col", "pięciorgiem"),
    ],
)
def test_declined(n: int, case: str, gender: str, words: str) -> None:
    assert declined(n, case, gender) == words
