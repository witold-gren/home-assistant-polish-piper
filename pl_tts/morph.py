"""Live morphological analysis with Morfeusz 2 (IPI PAN, SGJP dictionary).

Morfeusz is built into the image (see Dockerfile); every word after a number is
analysed on the fly, so any Polish noun gets the right numeral - no word list.
Results are cached (the same words repeat in HA announcements).
"""

from __future__ import annotations

import functools
import logging

_LOGGER = logging.getLogger("pl_tts")

try:
    import morfeusz2

    _MORFEUSZ = morfeusz2.Morfeusz(expand_tags=False)
except Exception as err:  # noqa: BLE001 - without Morfeusz numerals stay nominative
    _MORFEUSZ = None
    _LOGGER.warning("Morfeusz 2 unavailable (%s) - numerals will not agree with nouns", err)

AVAILABLE = _MORFEUSZ is not None

# Parts of speech that make a form "not a noun" for numeral agreement
# (adjectives are handled separately: "księży" is a noun and an adjective)
_NOT_NOUN = {"fin", "adv", "num", "ppron12", "ppron3", "praet", "inf", "impt", "prep", "conj", "comp", "qub", "bedzie"}
_ADJECTIVE = {"adj", "ppas", "pact", "adja"}

Reading = tuple[str, str, tuple[str, ...]]  # (gender, number, cases)


@functools.lru_cache(maxsize=8192)
def analyse(word: str) -> tuple[tuple[Reading, ...], bool]:
    """(noun readings, is_adjective) for a word form.

    gender: m1 (personal), m2 (animate), m3 (inanimate), f, n, col (collective
    "dzieci" or plurale tantum "drzwi"). A form that can also be a verb gets no
    noun readings; one that can also be an adjective keeps them and is_adjective
    is True - the caller decides from the next word ("2 księży" vs "2 nowe okna").
    """
    if _MORFEUSZ is None:
        return (), False
    analyses = _MORFEUSZ.analyse(word.lower())
    tags = [a[2][2].split(":") for a in analyses]
    pos = {t[0] for t in tags}
    is_adj = bool(pos & _ADJECTIVE)
    if pos & _NOT_NOUN:
        return (), is_adj
    # Plurale tantum titles ("Wiadomości" - TV news) lose to the ordinary noun
    if any("pt" in t[4:] for t in tags) and any("pt" not in t[4:] and t[0] == "subst" and t[1] == "pl" for t in tags):
        tags = [t for t in tags if "pt" not in t[4:]]
    readings: set[Reading] = set()
    for t in tags:
        # ger = verbal noun ("spotkanie" from "spotkać") - declines like a neuter noun
        if t[0] not in ("subst", "depr", "ger") or len(t) < 4:
            continue
        for g in t[3].split("."):
            gender = "col" if ("col" in t[4:] or "pt" in t[4:]) else ("n" if g.startswith("n") else g)
            readings.add((gender, t[1], tuple(t[2].split("."))))
    return tuple(sorted(readings)), is_adj


@functools.lru_cache(maxsize=8192)
def inflect(word: str, number: str, case: str, gender: str | None = None) -> str | None:
    """Form of `word` (noun or adjective) in the given number and case, e.g.
    inflect("kilometr", "pl", "loc") -> "kilometrach",
    inflect("kwadratowy", "pl", "gen", "m3") -> "kwadratowych".
    None when Morfeusz does not know the word or the form."""
    if _MORFEUSZ is None:
        return None
    for a in _MORFEUSZ.analyse(word.lower()):
        tag = a[2][2].split(":")
        if tag[0] not in ("subst", "adj"):
            continue
        lemma = a[2][1].split(":")[0]
        for g in _MORFEUSZ.generate(lemma):
            gt = g[2].split(":")
            if gt[0] != tag[0] or len(gt) < 4 or gt[1] != number or case not in gt[2].split("."):
                continue
            if tag[0] == "adj":
                genders = gt[3].split(".")
                if gender and not any(x == gender or (gender == "n" and x.startswith("n")) for x in genders):
                    continue
                if len(gt) > 4 and gt[4] != "pos":
                    continue
            elif "col" in gt[4:] and "col" not in tag[4:]:
                continue
            form = g[0]
            return form if word[:1].islower() else form[:1].upper() + form[1:]
    return None


def noun_gender(word: str) -> str | None:
    """Gender of a noun's first reading (m1/m2/m3/f/n/col), or None."""
    readings, _ = analyse(word)
    return readings[0][0] if readings else None


def is_adjective(word: str) -> bool:
    return analyse(word)[1]
