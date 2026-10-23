"""Polish text normalization for TTS: written forms -> spoken words.

espeak-ng (Piper's phonemizer) reads "o 9:05" as "o dziewięć zero pięć",
"6°C" as "sześć stopień ce" and drops the minus in "-3,5". This module rewrites
times, dates, quantities with units, negative and decimal numbers and common
abbreviations into words before Piper sees the text. Rules are deterministic,
so a wrong reading is fixed with one rule plus a test.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Callable

from .numbers import cardinal, decimal_words, declined, ordinal, plural_index

from . import morph
from .numbers import ordinal_form
from .pronunciations import PRONUNCIATIONS

# Prepositions taking the genitive: "bez 5 osób" -> bez pięciu osób (after 5+
# the noun is genitive anyway, so the preposition decides the numeral's case)
_GEN_PREPS = {
    "bez", "dla", "do", "od", "z", "ze", "u", "koło", "obok", "około", "wokół", "spośród",
    "wśród", "podczas", "według", "zamiast", "oprócz", "naprzeciw", "sprzed", "spod", "znad", "zza",
    "powyżej", "poniżej", "blisko", "niedaleko",
    # verbs and nouns governing the genitive: "brakuje 2 osób" -> dwóch osób
    "brakuje", "brakowało", "zabrakło", "zabraknie", "brak", "potrzeba", "ubyło", "przybyło",
}
# "nie ma 5 lamp" -> nie ma pięciu lamp (negation takes the genitive)
_GEN_PHRASES = {
    "nie ma", "nie było", "nie będzie", "nie mam", "nie masz", "nie mamy", "nie macie", "nie mają",
    "nie widzę", "nie widać", "nie słychać",
}
# Case of a quantity (number + unit) after a preposition: "do 5 km" ->
# do pięciu kilometrów, "po 3 min" -> po trzech minutach, "przed 2 h" -> przed dwiema godzinami
_QTY_CASE = {
    **{p: "gen" for p in ("bez", "dla", "do", "od", "około", "koło", "u", "wśród", "powyżej", "poniżej", "blisko", "niedaleko", "brakuje", "zabrakło", "brak", "potrzeba")},
    "przed": "inst", "nad": "inst", "pod": "inst", "między": "inst", "przy": "loc", "po": "loc",
}


def _context(text: str, end: int) -> list[str]:
    """Up to two words before position `end` (lowercase)."""
    return [w.lower() for w in re.findall(r"[^\W\d_]+", text[max(0, end - 40):end])[-2:]]


def _genitive_context(before: list[str]) -> bool:
    return bool(before) and (before[-1] in _GEN_PREPS or " ".join(before[-2:]) in _GEN_PHRASES)
_CASE_ORDER = ("nom", "acc", "gen", "inst", "loc", "dat")
_DURATION_WORDS = {
    "pozostało", "zostało", "trwa", "trwało", "trwał", "czas", "za", "przez", "upłynęło",
    "minęło", "minutnik", "timer", "odliczanie", "pozostaje", "zostaje",
}
# (1, 2-4, 5+, accusative singular)
_HOURS = ("godzina", "godziny", "godzin", "godzinę")
_MINUTES = ("minuta", "minuty", "minut", "minutę")
_SECONDS = ("sekunda", "sekundy", "sekund", "sekundę")


def _numeral_for(n: int, following: list[str], before: list[str]) -> str | None:
    """Numeral agreeing with the noun after the number (the next word, or the
    one after it when Morfeusz says the next word is an adjective: "2 nowe wiadomości")."""
    readings, is_adj = morph.analyse(following[0]) if following else ((), False)
    if is_adj and len(following) > 1:
        # "2 nowe wiadomości": an adjective before a noun - take the noun
        next_readings, _ = morph.analyse(following[1])
        if next_readings:
            readings = next_readings
    if not readings:
        return None
    number = "sg" if n == 1 else "pl"
    readings = [r for r in readings if r[1] == number]
    if not readings:
        return None
    # Merge the readings per gender ("dzieci": nom and gen), then pick the case:
    # genitive after a genitive preposition, otherwise the first of nom, acc...
    by_gender: dict[str, set[str]] = {}
    for gender, _, cases in readings:
        by_gender.setdefault(gender, set()).update(cases)
    gen_prep = _genitive_context(before)
    if n >= 2 and plural_index(n) == 1 and not gen_prep:
        # After 2-4 (no genitive preposition) a genitive noun fits only m1 and
        # collectives ("dwóch księży", "dwoje dzieci"); drop other genders whose
        # form here is genitive-only ("księży" is also a rare feminine genitive)
        fitting = {
            g: c for g, c in by_gender.items()
            if g in ("m1", "col") or ({"nom", "acc", "inst", "loc", "dat"} & set(c))
        }
        by_gender = fitting or by_gender
    options: set[str] = set()
    for gender, cases in by_gender.items():
        if gen_prep and "gen" in cases:
            case = "gen"
        else:
            case = next((c for c in _CASE_ORDER if c in cases), "nom")
        if case == "gen" and not gen_prep and n >= 2:
            case = "nom"  # "5 osób", "2 mężczyzn": genitive noun, nominative numeral
        if gender == "m1" and case == "nom" and "nom" not in cases:
            case = "acc"  # "2 mężczyzn" -> dwóch (not "dwaj")
        options.add(declined(n, case, gender))
    return options.pop() if len(options) == 1 else None


MONTHS_GEN = [
    "", "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
]

# Unit -> (1, 2-4, 5+, fraction/genitive singular, feminine)
UNITS: dict[str, tuple[str, str, str, str, bool]] = {
    "°C": ("stopień Celsjusza", "stopnie Celsjusza", "stopni Celsjusza", "stopnia Celsjusza", False),
    "℃": ("stopień Celsjusza", "stopnie Celsjusza", "stopni Celsjusza", "stopnia Celsjusza", False),
    "°": ("stopień", "stopnie", "stopni", "stopnia", False),
    "%": ("procent", "procent", "procent", "procent", False),
    "kWh": ("kilowatogodzina", "kilowatogodziny", "kilowatogodzin", "kilowatogodziny", True),
    "Wh": ("watogodzina", "watogodziny", "watogodzin", "watogodziny", True),
    "kW": ("kilowat", "kilowaty", "kilowatów", "kilowata", False),
    "W": ("wat", "waty", "watów", "wata", False),
    "mV": ("miliwolt", "miliwolty", "miliwoltów", "miliwolta", False),
    "V": ("wolt", "wolty", "woltów", "wolta", False),
    "mA": ("miliamper", "miliampery", "miliamperów", "miliampera", False),
    "A": ("amper", "ampery", "amperów", "ampera", False),
    "VA": ("woltoamper", "woltoampery", "woltoamperów", "woltoampera", False),
    "GHz": ("gigaherc", "gigaherce", "gigaherców", "gigaherca", False),
    "MHz": ("megaherc", "megaherce", "megaherców", "megaherca", False),
    "Hz": ("herc", "herce", "herców", "herca", False),
    "Ω": ("om", "omy", "omów", "oma", False),
    "ohm": ("om", "omy", "omów", "oma", False),
    "kg": ("kilogram", "kilogramy", "kilogramów", "kilograma", False),
    "g": ("gram", "gramy", "gramów", "grama", False),
    "km/h": ("kilometr na godzinę", "kilometry na godzinę", "kilometrów na godzinę", "kilometra na godzinę", False),
    "m/s": ("metr na sekundę", "metry na sekundę", "metrów na sekundę", "metra na sekundę", False),
    "L/100 km": ("litr na sto kilometrów", "litry na sto kilometrów", "litrów na sto kilometrów", "litra na sto kilometrów", False),
    "l/100 km": ("litr na sto kilometrów", "litry na sto kilometrów", "litrów na sto kilometrów", "litra na sto kilometrów", False),
    "km": ("kilometr", "kilometry", "kilometrów", "kilometra", False),
    "cm": ("centymetr", "centymetry", "centymetrów", "centymetra", False),
    "mm": ("milimetr", "milimetry", "milimetrów", "milimetra", False),
    "m²": ("metr kwadratowy", "metry kwadratowe", "metrów kwadratowych", "metra kwadratowego", False),
    "m2": ("metr kwadratowy", "metry kwadratowe", "metrów kwadratowych", "metra kwadratowego", False),
    "m³": ("metr sześcienny", "metry sześcienne", "metrów sześciennych", "metra sześciennego", False),
    "m3": ("metr sześcienny", "metry sześcienne", "metrów sześciennych", "metra sześciennego", False),
    "m": ("metr", "metry", "metrów", "metra", False),
    "ml": ("mililitr", "mililitry", "mililitrów", "mililitra", False),
    "L": ("litr", "litry", "litrów", "litra", False),
    "l": ("litr", "litry", "litrów", "litra", False),
    "hPa": ("hektopaskal", "hektopaskale", "hektopaskali", "hektopaskala", False),
    "lx": ("luks", "luksy", "luksów", "luksa", False),
    "ppm": ("część na milion", "części na milion", "części na milion", "części na milion", True),
    "µg/m³": ("mikrogram na metr sześcienny", "mikrogramy na metr sześcienny", "mikrogramów na metr sześcienny", "mikrograma na metr sześcienny", False),
    "dBm": ("decybel na miliwat", "decybele na miliwat", "decybeli na miliwat", "decybela na miliwat", False),
    "dB": ("decybel", "decybele", "decybeli", "decybela", False),
    "kcal": ("kilokaloria", "kilokalorie", "kilokalorii", "kilokalorii", True),
    "ms": ("milisekunda", "milisekundy", "milisekund", "milisekundy", True),
    "sec": ("sekunda", "sekundy", "sekund", "sekundy", True),
    "s": ("sekunda", "sekundy", "sekund", "sekundy", True),
    "min": ("minuta", "minuty", "minut", "minuty", True),
    "h": ("godzina", "godziny", "godzin", "godziny", True),
    "zł": ("złoty", "złote", "złotych", "złotego", False),
    "PLN": ("złoty", "złote", "złotych", "złotego", False),
    "€": ("euro", "euro", "euro", "euro", False),
    "EUR": ("euro", "euro", "euro", "euro", False),
    "$": ("dolar", "dolary", "dolarów", "dolara", False),
    "TB": ("terabajt", "terabajty", "terabajtów", "terabajta", False),
    "GB": ("gigabajt", "gigabajty", "gigabajtów", "gigabajta", False),
    "GiB": ("gigabajt", "gigabajty", "gigabajtów", "gigabajta", False),
    "MB": ("megabajt", "megabajty", "megabajtów", "megabajta", False),
    "MiB": ("megabajt", "megabajty", "megabajtów", "megabajta", False),
    "kB": ("kilobajt", "kilobajty", "kilobajtów", "kilobajta", False),
    "kg/m²": ("kilogram na metr kwadratowy", "kilogramy na metr kwadratowy", "kilogramów na metr kwadratowy", "kilograma na metr kwadratowy", False),
    "kg/m2": ("kilogram na metr kwadratowy", "kilogramy na metr kwadratowy", "kilogramów na metr kwadratowy", "kilograma na metr kwadratowy", False),
    "dB/m": ("decybel na metr", "decybele na metr", "decybeli na metr", "decybela na metr", False),
    "m³/s": ("metr sześcienny na sekundę", "metry sześcienne na sekundę", "metrów sześciennych na sekundę", "metra sześciennego na sekundę", False),
    "UVI": ("w skali UV", "w skali UV", "w skali UV", "w skali UV", False),
    "% available": ("procent wolnego miejsca", "procent wolnego miejsca", "procent wolnego miejsca", "procent wolnego miejsca", False),
    "kvarh": ("kilowarogodzina", "kilowarogodziny", "kilowarogodzin", "kilowarogodziny", True),
    "var": ("war", "wary", "warów", "wara", False),
    "d": ("dzień", "dni", "dni", "dnia", False),
    "B": ("bajt", "bajty", "bajtów", "bajta", False),
    "kB/s": ("kilobajt na sekundę", "kilobajty na sekundę", "kilobajtów na sekundę", "kilobajta na sekundę", False),
    "KiB/s": ("kilobajt na sekundę", "kilobajty na sekundę", "kilobajtów na sekundę", "kilobajta na sekundę", False),
    "px": ("piksel", "piksele", "pikseli", "piksela", False),
    "steps": ("krok", "kroki", "kroków", "kroku", False),
    "floors": ("piętro", "piętra", "pięter", "piętra", False),
    "people": ("osoba", "osoby", "osób", "osoby", True),
    "Mbit/s": ("megabit na sekundę", "megabity na sekundę", "megabitów na sekundę", "megabita na sekundę", False),
    "MB/s": ("megabajt na sekundę", "megabajty na sekundę", "megabajtów na sekundę", "megabajta na sekundę", False),
}

# Abbreviations (regex -> words). Order matters (longer first).
ABBREVIATIONS: list[tuple[str, str]] = [
    (r"\bm\.in\.", "między innymi"),
    (r"\bitd\.(?=\s*[,;:)])", "i tak dalej"),
    (r"\bitd\.", "i tak dalej."),
    (r"\bitp\.(?=\s*[,;:)])", "i tym podobne"),
    (r"\bitp\.", "i tym podobne."),
    (r"\btzn\.", "to znaczy"),
    (r"\bnp\.", "na przykład"),
    (r"\bok\.(?=\s*\d)", "około"),
    (r"\bul\.", "ulica"),
    (r"\bal\.", "aleja"),
    (r"\bpl\.(?=\s+[A-ZĄĆĘŁŃÓŚŹŻ])", "plac"),
    (r"\bos\.(?=\s+[A-ZĄĆĘŁŃÓŚŹŻ])", "osiedle"),
    (r"\b(w|we)\s+godz\.", r"\1 godzinach"),
    (r"\b(o)\s+godz\.", r"\1 godzinie"),
    (r"\b(od|do|około)\s+godz\.", r"\1 godziny"),
    (r"\bgodz\.", "godzina"),
    (r"\btel\.", "telefon"),
    (r"\bnr\b\.?", "numer"),
    (r"\bdr\b\.?(?=\s+[A-ZĄĆĘŁŃÓŚŹŻ])", "doktor"),
    (r"\bprof\.", "profesor"),
    (r"\bmgr\b\.?(?=\s+[A-ZĄĆĘŁŃÓŚŹŻ])", "magister"),
    (r"\bśw\.", "święty"),
]

NUM = r"[-−]?\d+(?:[.,]\d+)?"
_TIME_PREP_FORM = {
    "godzinie": "f_gen", "godziny": "f_gen", "godzinę": "f_acc", "godzina": "f_nom",
    "o": "f_gen", "po": "f_gen", "w": "f_gen",  # locative = genitive form for feminine
    "od": "f_gen", "do": "f_gen", "około": "f_gen", "koło": "f_gen",
    "przed": "f_ins", "między": "f_ins", "za": "f_ins",
}


def _hour(h: int, form: str) -> str:
    return "zero" if h == 0 else ordinal(h, form)


def _time(h: int, m: int, form: str) -> str:
    words = _hour(h, form)
    if m:
        words += " " + (f"zero {cardinal(m)}" if m < 10 and form == "f_nom" else cardinal(m))
    return words


def _sub(pattern: str, repl: Callable[[re.Match[str]], str], text: str, flags: int = 0) -> str:
    return re.sub(pattern, repl, text, flags=flags)


def _valid_time(h: str, m: str) -> bool:
    return int(h) <= 24 and int(m) <= 59


def _valid_date(d: int, mo: int) -> bool:
    return 1 <= d <= 31 and 1 <= mo <= 12


def _date(d: int, mo: int, year: str | None) -> str:
    words = f"{ordinal(d, 'm_gen')} {MONTHS_GEN[mo]}"
    if year:
        words += f" {ordinal(int(year), 'm_gen')} roku"
    return words


def _round(number: str) -> str:
    """Spoken precision: 2 decimals below 10, 1 below 1000, none above
    (3027.18552 kWh -> 3027, 42.347 kWh -> 42.3, 0.571 A -> 0.57)."""
    plain = number.replace("−", "-").replace(",", ".")
    if "." not in plain or len(plain.split(".")[1]) <= 1:
        return number
    value = float(plain)
    digits = 2 if abs(value) < 10 else 1 if abs(value) < 1000 else 0
    rounded = f"{round(value, digits):.{digits}f}"
    return rounded.replace(".", ",") if "," in number else rounded


def _local(dt: "datetime") -> "datetime":
    """UTC -> Polish time (CET/CEST: last Sunday of March/October, 01:00 UTC)."""
    utc = dt.astimezone(timezone.utc).replace(tzinfo=None)

    def last_sunday(year: int, month: int) -> datetime:
        d = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year, 12, 31)
        return d - timedelta(days=(d.weekday() + 1) % 7)

    start = last_sunday(utc.year, 3).replace(hour=1)
    end = last_sunday(utc.year, 10).replace(hour=1)
    return utc + timedelta(hours=2 if start <= utc < end else 1)


# Currencies: whole units + hundredths, never rounded (49,99 zł)
_CURRENCY = {
    "zł": (("złoty", "złote", "złotych"), ("grosz", "grosze", "groszy")),
    "PLN": (("złoty", "złote", "złotych"), ("grosz", "grosze", "groszy")),
    "€": (("euro", "euro", "euro"), ("cent", "centy", "centów")),
    "EUR": (("euro", "euro", "euro"), ("cent", "centy", "centów")),
    "$": (("dolar", "dolary", "dolarów"), ("cent", "centy", "centów")),
}


def _money(number: str, unit: str) -> str:
    major, minor = _CURRENCY[unit]
    plain = number.replace("−", "-").replace(",", ".")
    negative = plain.startswith("-")
    whole, _, frac = plain.lstrip("-").partition(".")
    zl = int(whole or "0")
    gr = int((frac + "00")[:2]) if frac else 0
    words = f"{cardinal(zl)} {major[plural_index(zl) if zl else 2]}"
    if gr:
        words += f" {cardinal(gr)} {minor[plural_index(gr)]}"
    return ("minus " if negative else "") + words


def _decline_phrase(phrase: str, number: str, case: str) -> str | None:
    """Decline a unit phrase given in nominative singular: its head noun and
    agreeing adjectives ("metr kwadratowy" -> "metrach kwadratowych"); the rest
    ("na godzinę", "Celsjusza") stays."""
    words = phrase.split()
    gender = morph.noun_gender(words[0])
    head = morph.inflect(words[0], number, case)
    if head is None:
        return None
    out = [head]
    i = 1
    while i < len(words) and morph.is_adjective(words[i]) and words[i].endswith(("y", "i")):
        adj = morph.inflect(words[i], number, case, gender)
        if adj is None:
            break
        out.append(adj)
        i += 1
    return " ".join(out + words[i:])


def _quantity_oblique(n: int, unit: str, case: str) -> str | None:
    one, _, _, _, feminine = UNITS[unit]
    gender = "f" if feminine else (morph.noun_gender(one.split()[0]) or "m3")
    phrase = _decline_phrase(one, "sg" if n == 1 else "pl", case)
    if phrase is None:
        return None
    return f"{declined(abs(n), case, gender)} {phrase}"


def _quantity(number: str, unit: str, before: list[str] | None = None) -> str:
    if unit in _CURRENCY:
        return _money(number, unit)
    one, few, many, frac, feminine = UNITS[unit]
    plain = _round(number).replace("−", "-")
    case = _QTY_CASE.get(before[-1]) if before else None
    if case is None and before and " ".join(before[-2:]) in _GEN_PHRASES:
        case = "gen"
    if case and not re.search(r"[.,]\d*[1-9]", plain) and not plain.startswith("-"):
        oblique = _quantity_oblique(int(float(plain.replace(",", "."))), unit, case)
        if oblique:
            return oblique
    is_fraction = bool(re.search(r"[.,]\d*[1-9]", plain))
    if is_fraction:
        return f"{decimal_words(plain)} {frac}"
    n = int(float(plain.replace(",", ".")))
    forms = (one, few, many)
    words = cardinal(abs(n), feminine)
    if n < 0:
        words = "minus " + words
    return f"{words} {forms[plural_index(n) if n else 2]}"


_UNIT_RE = "|".join(re.escape(u) for u in sorted(UNITS, key=len, reverse=True))

_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
    "\U0000FE0F\U0000200D\U000E0020-\U000E007F]+"
)
# Words matched case-insensitively; all-caps abbreviations (OK, PR) only as
# written, so "ok." (około) or "pr" inside text are left alone
_PRONUNCIATION_KEY = {k.lower(): v for k, v in PRONUNCIATIONS.items()}
_PRONUNCIATION_RE = re.compile(
    "|".join(
        (rf"(?<![\w-]){re.escape(k)}(?![\w-])" if k.isupper() else rf"(?<![\w-])(?i:{re.escape(k)})(?![\w-])")
        for k in sorted(PRONUNCIATIONS, key=len, reverse=True)
    )
)
_ROMAN = re.compile(r"^M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$")
_ROMAN_VALUES = {"M": 1000, "D": 500, "C": 100, "L": 50, "X": 10, "V": 5, "I": 1}
_LOC_PREPS = {"w", "we", "na", "o", "przy", "po"}


def _dots(text: str) -> str:
    return " kropka ".join(p for p in text.split(".") if p)


def _phone(m: re.Match[str]) -> str:
    groups = [m.group(2), m.group(4), m.group(5)]
    out = ["plus czterdzieści osiem"] if m.group(1) else []
    out += [" ".join(cardinal(int(c)) for c in g) if g.startswith("0") else cardinal(int(g)) for g in groups]
    return ", ".join(out)


def _roman(text: str) -> int | None:
    if not text or not _ROMAN.match(text):
        return None
    total = 0
    for i, ch in enumerate(text):
        v = _ROMAN_VALUES[ch]
        total += -v if i + 1 < len(text) and _ROMAN_VALUES[text[i + 1]] > v else v
    return total or None


def _ordinal_for_noun(n: int, noun: str, before: list[str]) -> str | None:
    """Ordinal agreeing with the noun after it: "3. miejsce" -> trzecie,
    "w XXI wieku" -> dwudziestym pierwszym, "na 2. piętrze" -> drugim."""
    readings, _ = morph.analyse(noun)
    readings = [r for r in readings if r[1] == "sg"] or list(readings)
    if not readings:
        return None
    gender, number = readings[0][0], readings[0][1]
    # "wieku": separate readings for gen and loc - merge them
    cases = tuple(c for r in readings if r[0] == gender and r[1] == number for c in r[2])
    if before and before[-1] in _LOC_PREPS and "loc" in cases:
        case = "loc"
    elif _genitive_context(before) and "gen" in cases:
        case = "gen"
    else:
        case = next((c for c in _CASE_ORDER if c in cases), "nom")
    return ordinal(n, ordinal_form(gender, number, case))


def _score(a: int, b: int) -> str:
    second = "zera" if b == 0 else declined(b, "gen", "m3")
    return f"{cardinal(a)} do {second}"


def normalize(text: str) -> str:
    """Rewrite written forms into words. Idempotent: running it again on the
    result changes nothing (the result has no digits or unit symbols left)."""
    if not text:
        return text
    t = text.replace("\u00a0", " ").replace("\u202f", " ")

    # Emojis and pictographs are not read
    t = _EMOJI.sub("", t)

    # E-mail and web addresses: jan.kowalski@gmail.com -> jan kropka kowalski małpa gmail kropka com
    t = _sub(
        r"\b([\w.+-]+)@([\w-]+(?:\.[\w-]+)+)\b",
        lambda m: f"{_dots(m.group(1))} małpa {_dots(m.group(2))}",
        t,
    )
    t = _sub(
        r"\b(?:https?://)?(?:www\.)?((?:[\w-]+\.)+(?:pl|com|eu|org|net|io|dev|info|gov|edu)(?![\w.]))(?:/[^\s]*)?",
        lambda m: _dots(m.group(1)),
        t,
    )

    # Phone numbers: +48 123 456 789, 123-456-789, tel. 123 456 789
    t = _sub(
        r"(\+48[\s-]?)?\b(\d{3})([\s-])(\d{3})\3(\d{3})\b",
        lambda m: _phone(m) if (m.group(1) or m.group(3) == "-" or re.search(r"(?:tel|telefon\w*|numer\w*|zadzwoń\w*|komórk\w*)[\s.:]*$", m.string[: m.start()], re.IGNORECASE)) else m.group(0),
        t,
    )

    # Foreign words and names spelled the Polish way (pronunciations.py)
    t = _PRONUNCIATION_RE.sub(lambda m: _PRONUNCIATION_KEY[m.group(0).lower()], t)

    # 1 013 / 1 000 000 -> 1013 (thousands separated by spaces)
    t = _sub(r"\b(\d{1,3})(?: (\d{3}))+\b", lambda m: m.group(0).replace(" ", ""), t)

    for pattern, words in ABBREVIATIONS:
        t = re.sub(pattern, words, t, flags=re.IGNORECASE)

    # ISO date-time 2026-10-20T15:30(:00)
    def iso_dt(m: re.Match[str]) -> str:
        y, mo, d, h, mi = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
        if h is not None and m.group(6):
            try:
                stamp = datetime.fromisoformat(m.group(0).replace("Z", "+00:00"))
                local = _local(stamp)
                y, mo, d, h, mi = str(local.year), local.month, local.day, str(local.hour), f"{local.minute:02d}"
            except ValueError:
                pass
        out = _date(d, mo, y) if _valid_date(d, mo) else m.group(0)
        if h is not None and _valid_time(h, mi):
            out += ", " + _time(int(h), int(mi), "f_nom")
        return out

    t = _sub(r"\b(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{1,2}):(\d{2})(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?(?![\d:])", iso_dt, t)

    # Identifiers stay as written (espeak spells them): MAC, UUID, letter+digit
    # tokens (CR2450, PM10, e8). Protected now, restored at the end.
    protected: list[str] = []

    def protect(m: re.Match[str]) -> str:
        token = m.group(0)
        if token in UNITS or re.fullmatch(rf"{NUM}\s?(?:{_UNIT_RE})", token):  # m2, 15min - units
            return token
        protected.append(token)
        return chr(0xE000 + len(protected) - 1)  # private-use char: no digits for later rules

    t = _sub(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b", protect, t)
    t = _sub(r"\b[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\b", protect, t)
    t = _sub(r"\b(?=\w*\d)(?=\w*[A-Za-z])\w+\b", protect, t)

    # Raw HA states: no_wake_word -> no wake word; "0 · HOME" -> "0, HOME"; 2× AA
    t = re.sub(r"(?<=[^\W\d_])_(?=[^\W\d_])", " ", t)
    t = t.replace(" · ", ", ").replace("·", ", ")
    t = _sub(r"(\d)\s?[×x]\s?(?=[A-Za-z\d])", lambda m: f"{m.group(1)} razy ", t)

    # Versions and IPv4 addresses: 2026.10.1 / 192.168.1.10 -> "kropka"
    t = _sub(
        r"(?<![\d.,])(\d{4}\.\d{1,2}\.\d{1,2}|\d{1,3}(?:\.\d{1,3}){3})(?![\d.]*\d)",
        lambda m: " kropka ".join(cardinal(int(p)) for p in m.group(1).split(".")),
        t,
    )

    # Postal codes: 31-150 -> trzydzieści jeden, sto pięćdziesiąt
    t = _sub(r"\b(\d{2})-(\d{3})\b(?=\s+[A-ZĄĆĘŁŃÓŚŹŻ])", lambda m: f"{cardinal(int(m.group(1)))}, {cardinal(int(m.group(2)))}", t)

    # Small fractions: 2/3 -> dwie trzecie, 1/4 -> jedna czwarta, 5/8 -> pięć ósmych
    def fraction(m: re.Match[str]) -> str:
        a, b = int(m.group(1)), int(m.group(2))
        if a == 1 and b == 2:
            return "pół"
        form = "f_nom" if a == 1 else ("pl_nom" if plural_index(a) == 1 else "pl_gen")
        return f"{cardinal(a, feminine=True)} {ordinal(b, form)}"

    t = _sub(r"(?<![\d/])([1-9])/([2-9]|10)(?![\d/])", lambda m: fraction(m) if int(m.group(1)) < int(m.group(2)) else m.group(0), t)

    # House/flat numbers: 30/2 -> trzydzieści łamane przez dwa (1/2 -> pół)
    t = _sub(
        r"(?<![\d/])(\d{1,4})/(\d{1,4})(?![\d/])",
        lambda m: "pół" if m.group(0) == "1/2" else f"{cardinal(int(m.group(1)))} łamane przez {cardinal(int(m.group(2)))}",
        t,
    )

    # Times written with a dot after a time word: o 17.30 / godzina 9.05 / 17.30-18.00
    t = _sub(
        r"(?<![\d.,])(\d{1,2})\.(\d{2})\s*[-–]\s*(\d{1,2})\.(\d{2})(?![\d.,])",
        lambda m: f"{m.group(1)}:{m.group(2)}-{m.group(3)}:{m.group(4)}" if _valid_time(m.group(1), m.group(2)) and _valid_time(m.group(3), m.group(4)) else m.group(0),
        t,
    )

    t = _sub(
        r"\b(o|od|do|przed|po|około|godzina|godzinie|godziny|godzinę)\s+(\d{1,2})\.(\d{2})\b",
        lambda m: f"{m.group(1)} {m.group(2)}:{m.group(3)}" if _valid_time(m.group(2), m.group(3)) else m.group(0),
        t,
        flags=re.IGNORECASE,
    )
    # Scores: 2:1 -> dwa do jednego (one-digit "minutes" cannot be a time)
    t = _sub(r"(?<![\d:])(\d{1,2}):(\d)(?![\d:])", lambda m: _score(int(m.group(1)), int(m.group(2))), t)

    # Time ranges: 17:30-18:00 -> od siedemnastej trzydzieści do osiemnastej
    def time_range(m: re.Match[str]) -> str:
        h1, m1, h2, m2 = m.group(1), m.group(2), m.group(3), m.group(4)
        if not (_valid_time(h1, m1) and _valid_time(h2, m2)):
            return m.group(0)
        return f"od {_time(int(h1), int(m1), 'f_gen')} do {_time(int(h2), int(m2), 'f_gen')}"

    t = _sub(r"(?:\bod\s+)?\b(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})\b", time_range, t, flags=re.IGNORECASE)

    # Durations H:MM:SS (timer "0:05:00", "pozostało 1:23:45"):
    # jedna godzina dwadzieścia trzy minuty czterdzieści pięć sekund
    def duration(m: re.Match[str]) -> str:
        word, h, mi, sec = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if not (h == 0 or (word and word.lower() in _DURATION_WORDS)) or mi > 59 or sec > 59:
            return m.group(0)
        case = "acc" if word and word.lower() in ("za", "przez") else "nom"
        parts = []
        for value, forms in ((h, _HOURS), (mi, _MINUTES), (sec, _SECONDS)):
            if value:
                noun = forms[3] if (case == "acc" and value == 1) else forms[plural_index(value)]
                parts.append(f"{declined(value, case, 'f')} {noun}")
        spoken = " ".join(parts) or "zero sekund"
        return f"{word} {spoken}" if word else spoken

    t = _sub(r"(?:\b([^\W\d_]+)\s+)?\b(\d{1,3}):(\d{2}):(\d{2})\b", duration, t)

    # Times with a preposition: o 17:30 -> o siedemnastej trzydzieści
    def time_prep(m: re.Match[str]) -> str:
        prep, h, mi = m.group(1), m.group(2), m.group(3)
        if not _valid_time(h, mi):
            return m.group(0)
        return f"{prep} {_time(int(h), int(mi), _TIME_PREP_FORM[prep.lower()])}"

    preps = "|".join(sorted(_TIME_PREP_FORM, key=len, reverse=True))
    t = _sub(rf"\b({preps})\s+(\d{{1,2}}):(\d{{2}})\b", time_prep, t, flags=re.IGNORECASE)

    # Bare times: 14:30 -> czternasta trzydzieści
    t = _sub(
        r"(?<![\d:])(\d{1,2}):(\d{2})(?::\d{2})?(?![\d:])",
        lambda m: _time(int(m.group(1)), int(m.group(2)), "f_nom") if _valid_time(m.group(1), m.group(2)) else m.group(0),
        t,
    )

    # Dates: 20.10.2026 / 21.10 / 21 października 2026 r.
    def num_date(m: re.Match[str]) -> str:
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if not _valid_date(d, mo):
            return m.group(0)
        return _date(d, mo, y)

    t = _sub(r"(?<![\d,.])(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s*r(?:\.|oku\b))?(?![\d]|[.,]\d)", num_date, t)
    t = _sub(r"(?<![\d,.])(\d{1,2})\.(\d{2})(?![\d.,]|\s*(?:" + _UNIT_RE + r"))", lambda m: num_date(_FakeMatch(m.group(1), m.group(2), None)) , t)

    months = "|".join(MONTHS_GEN[1:])

    def word_date(m: re.Match[str]) -> str:
        d, month, y = int(m.group(1)), m.group(2), m.group(3)
        if not 1 <= d <= 31:
            return m.group(0)
        out = f"{ordinal(d, 'm_gen')} {month}"
        if y:
            out += f" {ordinal(int(y), 'm_gen')} roku"
        return out

    t = _sub(rf"\b(\d{{1,2}})\s+({months})(?:\s+(\d{{4}})(?:\s*r(?:\.|oku\b))?)?", word_date, t, flags=re.IGNORECASE)

    # Year with "r." / "roku": 2026 r. -> dwa tysiące dwudziestego szóstego roku
    t = _sub(r"\b([wW])\s+(\d{4})\s*r(?:\.|oku\b)", lambda m: f"{m.group(1)} {ordinal(int(m.group(2)), 'm_loc')} roku", t)
    t = _sub(r"\b(\d{4})\s*r(?:\.|oku\b)", lambda m: f"{ordinal(int(m.group(1)), 'm_gen')} roku", t)

    # Ordinals with a dot: 3. miejsce -> trzecie miejsce, na 2. piętrze -> na drugim piętrze
    def dotted_ordinal(m: re.Match[str]) -> str:
        word = _ordinal_for_noun(int(m.group(1)), m.group(2), _context(m.string, m.start(1)))
        return f"{word} {m.group(2)}" if word else m.group(0)

    t = _sub(r"(?<![\d.,])(\d{1,3})\.\s+([a-ząćęłńóśźż]+)", dotted_ordinal, t)

    # Roman numerals: XXI wiek / w XXI wieku / Jan Paweł II
    def roman(m: re.Match[str]) -> str:
        value = _roman(m.group(2))
        if value is None:
            return m.group(0)
        noun = m.group(3)
        if noun and noun[:1].islower():
            word = _ordinal_for_noun(value, noun, _context(m.string, m.start(2)))
            if word:
                return f"{m.group(1)}{word} {noun}"
        if m.group(1).strip() and len(m.group(2)) >= 2:
            # after a name: Jan Paweł II -> drugi
            return f"{m.group(1)}{ordinal(value, 'm_nom')}" + (f" {noun}" if noun else "")
        return m.group(0)

    t = _sub(r"((?:\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s)?)\b([IVXLCDM]{2,}|[VX])\b(?:\s+([^\W\d_]+))?", roman, t)

    # Ranges: 2-3 dni -> dwa, trzy dni; 2-3 osoby -> dwie, trzy osoby;
    # do 10-15 km -> do dziesięciu, piętnastu kilometrów (the way it is read aloud)
    def number_range(m: re.Match[str]) -> str:
        a, b, unit, noun = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
        if a >= b:
            return m.group(0)
        before = _context(m.string, m.start(1))
        if unit:
            unit = unit.strip()
            one, _, _, _, feminine = UNITS[unit]
            gender = "f" if feminine else (morph.noun_gender(one.split()[0]) or "m3")
            case = _QTY_CASE.get(before[-1], "nom") if before else "nom"
            return f"{declined(a, case, gender)}, {_quantity(m.group(2), unit, before)}"
        if noun:
            noun = noun.strip()
            second = _numeral_for(b, [noun], before) or cardinal(b)
            readings, _ = morph.analyse(noun)
            gender = readings[0][0] if readings else "m3"
            case = "gen" if _genitive_context(before) else "nom"
            first = declined(a, case, gender) if readings else cardinal(a)
            if gender == "m1" and case == "nom":
                first = declined(a, "acc", gender)
            return f"{first}, {second} {noun}"
        return f"{cardinal(a)}, {cardinal(b)}"

    t = _sub(
        rf"(?<![\d.,:/-])(\d{{1,4}})\s?[-–]\s?(\d{{1,4}})(?![\d.,:/])(\s?(?:{_UNIT_RE})(?![\wąćęłńóśźż]))?(\s+[a-ząćęłńóśźż]+)?",
        number_range,
        t,
    )

    # Quantities: -3,5°C, 50 km/h, 92%, 72 kg
    t = _sub(
        rf"(?<![\w.,])({NUM})\s?({_UNIT_RE})(?![\wąćęłńóśźż])",
        lambda m: _quantity(m.group(1), m.group(2), _context(m.string, m.start(1))),
        t,
    )

    # Negative numbers: -5 -> minus pięć (espeak drops the minus)
    t = _sub(r"(?<![\w.,])[-−](\d+(?:[.,]\d+)?)\b", lambda m: decimal_words("-" + m.group(1)), t)

    # Decimals: 3,5 -> trzy i pół
    t = _sub(r"(?<![\w.,])(\d+[.,]\d+)(?![\d.,]*\d)", lambda m: decimal_words(_round(m.group(1))), t)

    # Remaining integers (long digit strings are read digit by digit); the
    # numeral agrees with the following noun (jedna osoba, dwie lampy, dwoje dzieci)
    def integer(m: re.Match[str]) -> str:
        s = m.group(1)
        if len(s) > 9 or (len(s) > 1 and s.startswith("0")):
            return " ".join(cardinal(int(c)) for c in s) + m.group(2)
        n = int(s)
        word = _numeral_for(n, m.group(2).split(), _context(m.string, m.start(1)))
        return (word or cardinal(n)) + m.group(2)

    # Digits glued to letters (CO2, PM10, LO3842) stay: espeak spells such tokens
    t = _sub(r"(?<![^\W\d_])(\d+)(?![^\W\d_])((?:\s+[^\W\d_]+){0,2})", integer, t)

    for i, original in enumerate(protected):
        t = t.replace(chr(0xE000 + i), original)

    # Symbols left alone
    t = t.replace("&", " i ").replace("+", " plus ")
    return re.sub(r"[ \t]{2,}", " ", t).strip()


class _FakeMatch:
    """Lets the dd.mm rule reuse num_date with an optional year."""

    def __init__(self, d: str, mo: str, y: str | None) -> None:
        self._g = (None, d, mo, y)

    def group(self, i: int) -> str | None:
        return self._g[i]
