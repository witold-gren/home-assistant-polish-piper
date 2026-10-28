"""Polish number words: cardinals, ordinals (hours, days, years) and plural forms."""

from __future__ import annotations

UNITS = ["zero", "jeden", "dwa", "trzy", "cztery", "pięć", "sześć", "siedem", "osiem", "dziewięć"]
TEENS = [
    "dziesięć", "jedenaście", "dwanaście", "trzynaście", "czternaście",
    "piętnaście", "szesnaście", "siedemnaście", "osiemnaście", "dziewiętnaście",
]
TENS = [
    "", "", "dwadzieścia", "trzydzieści", "czterdzieści", "pięćdziesiąt",
    "sześćdziesiąt", "siedemdziesiąt", "osiemdziesiąt", "dziewięćdziesiąt",
]
HUNDREDS = [
    "", "sto", "dwieście", "trzysta", "czterysta", "pięćset",
    "sześćset", "siedemset", "osiemset", "dziewięćset",
]
SCALES = [
    ("tysiąc", "tysiące", "tysięcy"),
    ("milion", "miliony", "milionów"),
    ("miliard", "miliardy", "miliardów"),
]


def plural_index(n: int) -> int:
    """0 = one (1), 1 = few (2-4, 22-24...), 2 = many (0, 5-21, 25-31...)."""
    n = abs(n)
    if n == 1:
        return 0
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return 1
    return 2


def _below_thousand(n: int) -> list[str]:
    words: list[str] = []
    h, rest = divmod(n, 100)
    if h:
        words.append(HUNDREDS[h])
    if 10 <= rest < 20:
        words.append(TEENS[rest - 10])
    else:
        t, u = divmod(rest, 10)
        if t:
            words.append(TENS[t])
        if u:
            words.append(UNITS[u])
    return words


def cardinal(n: int, feminine: bool = False) -> str:
    """Cardinal number in words, e.g. 1013 -> "tysiąc trzynaście".

    feminine: "jedna" for 1 and "dwie" for a final 2 (2, 22, 102...).
    """
    if n < 0:
        return "minus " + cardinal(-n, feminine)
    if n == 0:
        return "zero"
    if feminine and n == 1:
        return "jedna"
    words: list[str] = []
    groups: list[int] = []
    while n:
        n, g = divmod(n, 1000)
        groups.append(g)
    for scale, g in reversed(list(enumerate(groups))):
        if not g:
            continue
        if scale == 0:
            words += _below_thousand(g)
        else:
            forms = SCALES[scale - 1]
            if g == 1:
                words.append(forms[0])
            else:
                words += _below_thousand(g)
                words.append(forms[plural_index(g)])
    if feminine and words[-1] == "dwa":
        words[-1] = "dwie"
    return " ".join(words)


# --- ordinals ---------------------------------------------------------------

# Stem + type: "hard" stems take -y/-ego/-ym/-a/-ej/-ą, "soft" (drug-, trzec-)
# take -i/-iego/-im/-a|-ia/-iej/-ą|-ią.
_UNIT_STEMS = ["", "pierwsz", "drug", "trzec", "czwart", "piąt", "szóst", "siódm", "ósm", "dziewiąt"]
_TEEN_STEMS = [
    "dziesiąt", "jedenast", "dwunast", "trzynast", "czternast",
    "piętnast", "szesnast", "siedemnast", "osiemnast", "dziewiętnast",
]
_TEN_STEMS = [
    "", "", "dwudziest", "trzydziest", "czterdziest", "pięćdziesiąt",
    "sześćdziesiąt", "siedemdziesiąt", "osiemdziesiąt", "dziewięćdziesiąt",
]
_HUNDRED_STEMS = [
    "", "setn", "dwusetn", "trzechsetn", "czterechsetn", "pięćsetn",
    "sześćsetn", "siedemsetn", "osiemsetn", "dziewięćsetn",
]
_THOUSAND_STEMS = {1: "tysięczn", 2: "dwutysięczn"}

# Form codes: m_nom, m_gen, m_dat, m_loc (= m/n instrumental), f_nom, f_gen
# (= f dat/loc), f_acc, f_ins, n_nom (= n acc), pl_nom (non-personal), pl_gen
# (= pl loc), pl_dat, pl_inst
_HARD = {
    "m_nom": "y", "m_gen": "ego", "m_dat": "emu", "m_loc": "ym", "f_nom": "a", "f_gen": "ej",
    "f_acc": "ą", "f_ins": "ą", "n_nom": "e", "pl_nom": "e", "pl_gen": "ych", "pl_dat": "ym", "pl_inst": "ymi",
}
_SOFT = {
    "m_nom": "i", "m_gen": "iego", "m_dat": "iemu", "m_loc": "im", "f_nom": "a", "f_gen": "iej",
    "f_acc": "ą", "f_ins": "ą", "n_nom": "ie", "pl_nom": "ie", "pl_gen": "ich", "pl_dat": "im", "pl_inst": "imi",
}


def _ord_word(stem: str, form: str) -> str:
    if stem == "drug":
        return "drug" + _SOFT[form]
    if stem == "trzec":
        ending = _SOFT[form]
        if form == "f_nom":
            ending = "ia"
        elif form in ("f_ins", "f_acc"):
            ending = "ią"
        return "trzec" + ending
    return stem + _HARD[form]


def ordinal(n: int, form: str = "m_nom") -> str:
    """Ordinal in words, 1..9999, e.g. ordinal(2026, "m_gen") ->
    "dwa tysiące dwudziestego szóstego"; ordinal(17, "f_gen") -> "siedemnastej".

    In compound ordinals only the last components are ordinal: thousands and
    hundreds stay cardinal unless they end the number (2000 -> "dwutysięcznego").
    """
    if not 1 <= n <= 9999:
        return cardinal(n)
    thousands, rest = divmod(n, 1000)
    hundreds, rest2 = divmod(rest, 100)
    words: list[str] = []
    if thousands:
        if rest == 0 and thousands in _THOUSAND_STEMS:
            return _ord_word(_THOUSAND_STEMS[thousands], form)
        words.append(cardinal(thousands * 1000))
    if hundreds:
        if rest2 == 0:
            words.append(_ord_word(_HUNDRED_STEMS[hundreds], form))
            return " ".join(words)
        words.append(HUNDREDS[hundreds])
    if 10 <= rest2 < 20:
        words.append(_ord_word(_TEEN_STEMS[rest2 - 10], form))
    else:
        t, u = divmod(rest2, 10)
        if t:
            words.append(_ord_word(_TEN_STEMS[t], form))
        if u:
            words.append(_ord_word(_UNIT_STEMS[u], form))
    return " ".join(words)


def decimal_words(text: str, feminine: bool = False) -> str:
    """ "3,5" -> "trzy i pół", "21.75" -> "dwadzieścia jeden przecinek siedemdziesiąt pięć",
    "-0,05" -> "minus zero przecinek zero pięć"."""
    text = text.strip()
    negative = text.startswith(("-", "−"))
    text = text.lstrip("-−")
    whole, _, frac = text.replace(".", ",").partition(",")
    whole_n = int(whole or "0")
    frac = frac.rstrip("0")
    prefix = "minus " if negative else ""
    if not frac:
        return prefix + cardinal(whole_n, feminine)
    if frac == "5":
        return prefix + (f"{cardinal(whole_n)} i pół" if whole_n else "pół")
    head = cardinal(whole_n)
    if frac.startswith("0"):
        tail = " ".join(UNITS[int(d)] for d in frac)
    else:
        tail = cardinal(int(frac))
    return f"{prefix}{head} przecinek {tail}"


# --- numerals agreeing with the noun -----------------------------------------

_M1_UNITS = ["", "jednego", "dwóch", "trzech", "czterech", "pięciu", "sześciu", "siedmiu", "ośmiu", "dziewięciu"]
_M1_TEENS = [
    "dziesięciu", "jedenastu", "dwunastu", "trzynastu", "czternastu",
    "piętnastu", "szesnastu", "siedemnastu", "osiemnastu", "dziewiętnastu",
]
_M1_TENS = [
    "", "", "dwudziestu", "trzydziestu", "czterdziestu", "pięćdziesięciu",
    "sześćdziesięciu", "siedemdziesięciu", "osiemdziesięciu", "dziewięćdziesięciu",
]
_M1_HUNDREDS = [
    "", "stu", "dwustu", "trzystu", "czterystu", "pięciuset",
    "sześciuset", "siedmiuset", "ośmiuset", "dziewięciuset",
]
_COLLECTIVE = {
    2: "dwoje", 3: "troje", 4: "czworo", 5: "pięcioro", 6: "sześcioro", 7: "siedmioro",
    8: "ośmioro", 9: "dziewięcioro", 10: "dziesięcioro", 11: "jedenaścioro",
    12: "dwanaścioro", 13: "trzynaścioro", 14: "czternaścioro", 15: "piętnaścioro",
    16: "szesnaścioro", 17: "siedemnaścioro", 18: "osiemnaścioro", 19: "dziewiętnaścioro",
    20: "dwadzieścioro",
}


def cardinal_m1(n: int) -> str:
    """Masculine-personal numeral (dwóch, pięciu, dwudziestu jeden): "2 mężczyzn"."""
    if not 2 <= n <= 999:
        return cardinal(n)
    h, rest = divmod(n, 100)
    words = [_M1_HUNDREDS[h]] if h else []
    if 10 <= rest < 20:
        words.append(_M1_TEENS[rest - 10])
    else:
        t, u = divmod(rest, 10)
        if t:
            words.append(_M1_TENS[t])
        if u:
            # "dwudziestu jeden mężczyzn" - a final 1 stays "jeden"
            words.append("jeden" if u == 1 and (t or h) else _M1_UNITS[u])
    return " ".join(words)


# --- numerals declined by case (gen, dat, acc, inst, loc) ---------------------

# Oblique forms of the components: (gen=loc, dat, inst)
_OBL_UNITS = {
    2: ("dwóch", "dwóm", "dwoma"), 3: ("trzech", "trzem", "trzema"), 4: ("czterech", "czterem", "czterema"),
    5: ("pięciu", "pięciu", "pięcioma"), 6: ("sześciu", "sześciu", "sześcioma"),
    7: ("siedmiu", "siedmiu", "siedmioma"), 8: ("ośmiu", "ośmiu", "ośmioma"),
    9: ("dziewięciu", "dziewięciu", "dziewięcioma"),
}
_OBL_TEENS = [
    "dziesięci", "jedenast", "dwunast", "trzynast", "czternast",
    "piętnast", "szesnast", "siedemnast", "osiemnast", "dziewiętnast",
]
_OBL_TENS = ["", "", "dwudziest", "trzydziest", "czterdziest", "pięćdziesięci",
             "sześćdziesięci", "siedemdziesięci", "osiemdziesięci", "dziewięćdziesięci"]
_OBL_HUNDREDS = ["", "st", "dwust", "trzyst", "czteryst", "pięciuset",
                 "sześciuset", "siedmiuset", "ośmiuset", "dziewięciuset"]

_ONE = {
    # case: (masculine, feminine, neuter)
    "nom": ("jeden", "jedna", "jedno"),
    "gen": ("jednego", "jednej", "jednego"),
    "dat": ("jednemu", "jednej", "jednemu"),
    "acc": ("jeden", "jedną", "jedno"),
    "inst": ("jednym", "jedną", "jednym"),
    "loc": ("jednym", "jednej", "jednym"),
}


def _obl_part(stem: str, case: str) -> str:
    """Teens/tens/hundreds stems: -u (gen/dat/loc), -oma (inst); -set stays."""
    if stem.endswith("set"):
        return stem
    if stem.endswith("i"):  # dziesięci-, pięćdziesięci-
        return stem + ("oma" if case == "inst" else "u")
    return stem + ("oma" if case == "inst" else "u")


# "tysiąc" in the oblique cases: (after 1, after 2+)
_OBL_THOUSAND = {
    "gen": ("tysiąca", "tysięcy"),
    "dat": ("tysiącowi", "tysiącom"),
    "inst": ("tysiącem", "tysiącami"),
    "loc": ("tysiącu", "tysiącach"),
}


def declined(n: int, case: str, gender: str) -> str:
    """Cardinal agreeing in case and gender with the noun:
    case: nom/gen/dat/acc/inst/loc; gender: m1, m2, m3, f, n, col.
    declined(1, "acc", "f") -> "jedną"; declined(2, "inst", "f") -> "dwiema";
    declined(5, "gen", "f") -> "pięciu"; declined(2, "nom", "col") -> "dwoje"."""
    if case == "voc":
        case = "nom"
    if n == 1:
        g = 1 if gender == "f" else 2 if gender in ("n", "col") else 0
        if case == "acc" and gender in ("m1", "m2"):
            return "jednego"
        return _ONE[case][g]
    if gender == "col" and n in _COLLECTIVE:
        base = _COLLECTIVE[n]  # dwoje, czworo, pięcioro
        stem = base[:-3] if base.endswith("oje") else base[:-3]
        tail = "oj" if base.endswith("oje") else "or"
        if case in ("nom", "acc"):
            return base
        return stem + tail + {"gen": "ga", "loc": "gu", "dat": "gu", "inst": "giem"}[case]
    if 1000 <= n <= 999_999 and case not in ("nom", "acc"):
        # "do 1500 km" -> do tysiąca pięciuset, "z 2000 osób" -> z dwóch tysięcy
        k, rest = divmod(n, 1000)
        thousand = _OBL_THOUSAND[case][0 if k == 1 else 1]
        words = [thousand] if k == 1 else [declined(k, case, "m3"), thousand]
        if rest:
            words.append("jeden" if rest == 1 else declined(rest, case, gender))
        return " ".join(words)
    if not 2 <= n <= 999:
        return cardinal(n, feminine=(gender == "f"))
    if case in ("nom", "acc"):
        if gender == "m1":
            if case == "nom" and n in (2, 3, 4):
                return {2: "dwaj", 3: "trzej", 4: "czterej"}[n]
            return cardinal_m1(n)  # dwóch / pięciu mężczyzn
        return cardinal(n, feminine=(gender == "f"))
    idx = {"gen": 0, "loc": 0, "dat": 1, "inst": 2}[case]
    h, rest = divmod(n, 100)
    words: list[str] = []
    if h:
        words.append(_obl_part(_OBL_HUNDREDS[h], case))
    if 10 <= rest < 20:
        words.append(_obl_part(_OBL_TEENS[rest - 10], case))
    else:
        t, u = divmod(rest, 10)
        if t:
            words.append(_obl_part(_OBL_TENS[t], case))
        if u == 1:
            words.append("jeden")  # "dwudziestu jeden osób" - a final 1 stays
        elif u:
            form = _OBL_UNITS[u][idx]
            if u == 2 and case == "inst" and gender == "f":
                form = "dwiema"
            words.append(form)
    return " ".join(words)


def ordinal_form(gender: str, number: str, case: str) -> str:
    """Form code for an ordinal agreeing with a noun (gender m1/m2/m3/f/n/col,
    number sg/pl, case nom/gen/dat/acc/inst/loc): "3. miejsce" -> n_nom."""
    if case == "voc":
        case = "nom"
    if number == "pl":
        return {"nom": "pl_nom", "acc": "pl_nom", "gen": "pl_gen", "loc": "pl_gen", "dat": "pl_dat", "inst": "pl_inst"}[case]
    if gender == "f":
        return {"nom": "f_nom", "gen": "f_gen", "dat": "f_gen", "loc": "f_gen", "acc": "f_acc", "inst": "f_ins"}[case]
    if gender in ("n", "col"):
        return {"nom": "n_nom", "acc": "n_nom", "gen": "m_gen", "dat": "m_dat", "inst": "m_loc", "loc": "m_loc"}[case]
    acc = "m_gen" if gender in ("m1", "m2") else "m_nom"
    return {"nom": "m_nom", "acc": acc, "gen": "m_gen", "dat": "m_dat", "inst": "m_loc", "loc": "m_loc"}[case]
