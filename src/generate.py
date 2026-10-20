"""Generation: stage 3 of the transfer system.

The transfer stage (transfer.py) decides WHAT the Hausa sentence contains:
which words, which PAC, which construction. This file decides HOW the words
are written:
  - the -n/-r suffix for "the" and for the linker (yaro -> yaron, miya -> miyar)
  - possessive suffixes (mota + -ta -> motata)
  - adjective agreement (sabo / sabuwa / sababbi)
  - ne / ce
  - putting the words of a noun phrase in order
  - the final sentence: spaces, capital letter, full stop
"""
from dataclasses import dataclass, field

import hausa_lexicon as L

VOWELS = "aeiouAEIOU"


# ---------------------------------------------------------------------------
# A Hausa noun phrase, as the transfer stage hands it over
# ---------------------------------------------------------------------------

@dataclass
class HNoun:
    word: str                    # Hausa noun, already singular or plural: yaro, yara
    english: str = ""            # the English head, for messages
    kind: str = "noun"           # noun, name, pronoun, indefinite, coordinated
    gender: str = "m"            # Hausa gender of the noun: m or f
    number: str = "sg"           # sg or pl
    person: str = "3sg.m"        # PAC person: 1sg, 2sg.m, 3sg.f, 3pl, 4 ...
    definite: bool = False       # English "the" -> -n/-r
    relative: bool = False       # a relative clause follows: mutumin da ... (always the linker)
    linked: str = ""             # the lexicon's -n/-r form, if it gives one
    before: list = field(default_factory=list)   # words before the noun: wannan, wasu, babban
    after: list = field(default_factory=list)    # words after the noun: biyu, da yawa, mai zafi
    possessive_suffix: str = ""  # nta, rta, na ... (my/her/his ...)
    possessor: object = None     # another HNoun: gidan Musa
    parts: list = field(default_factory=list)    # for "Musa da Ada"

    @property
    def feminine(self):
        """Feminine singular? (decides -r, ce, ta ...)"""
        return self.gender == "f" and self.number == "sg"


# ---------------------------------------------------------------------------
# Word-level rules
# ---------------------------------------------------------------------------

def add_suffix(word, suffix):
    """Attach a suffix to the last word.

    Plurals in -ai drop the -i:          ɗalibai -> ɗaliban, ɗalibansa
    A consonant-final word gets -i-:     tebur -> teburin
    """
    if not word:
        return word
    head, _, last = word.rpartition(" ")
    if last.endswith("ai"):
        last = last[:-1]
    elif last[-1] not in VOWELS:
        last += "i"
    return (head + " " if head else "") + last + suffix


def linker(word, feminine, linked_form="", definite=False):
    """The -n/-r form used for 'the' (A6) and for 'of' (gidan Musa).

    Feminine singular nouns ending in -a take -r (miya -> miyar);
    everything else takes -n (yaro -> yaron, yara -> yaran).
    For "the", a noun ending in a consonant takes a separate ɗin: fim -> fim ɗin.
    """
    if linked_form:
        return linked_form
    if definite and word[-1] not in VOWELS:
        return word + " ɗin"
    if feminine and word.endswith("a"):
        return word + "r"
    return add_suffix(word, "n")


def adjective_form(adj, gender, number):
    """Choose sabo / sabuwa / sababbi to agree with the noun."""
    if number == "pl":
        return adj["plural"]
    return adj["fem"] if gender == "f" else adj["masc"]


def copula(noun_phrase):
    """ne or ce, agreeing with the noun phrase (ce only for feminine singular)."""
    return L.copula(noun_phrase.feminine)


def split_frame(pac_form):
    """'ba ta … ba' -> ('ba ta', 'ba'); 'ya' -> ('ya', '')."""
    if "…" in pac_form:
        before, after = pac_form.split("…")
        return before.strip(), after.strip()
    return pac_form, ""


# ---------------------------------------------------------------------------
# Noun phrases
# ---------------------------------------------------------------------------

def noun_phrase(hn):
    """Write out a Hausa noun phrase in the right order.

    order:  [wannan / wasu / babban]  NOUN(-n/-r/suffix) [owner]  [biyu / da yawa / mai zafi]
    """
    if hn is None:
        return ""
    if hn.kind == "coordinated":
        return " da ".join(noun_phrase(p) for p in hn.parts)
    head = hn.word
    if hn.possessive_suffix:                       # mota + ta -> motata
        head = add_suffix(head, hn.possessive_suffix)
    elif hn.possessor is not None:                 # gidan Musa
        head = linker(head, hn.feminine, hn.linked) + " " + noun_phrase(hn.possessor)
    elif hn.relative:                              # mutumin da ya kira jiya (C15)
        head = linker(head, hn.feminine, hn.linked)
    elif hn.definite:                              # yaron, miyar, fim ɗin (A6)
        head = linker(head, hn.feminine, hn.linked, definite=True)
    return " ".join(w for w in hn.before + [head] + hn.after if w)


# ---------------------------------------------------------------------------
# The whole sentence
# ---------------------------------------------------------------------------

def sentence(words, end="."):
    """Join the words, tidy the spaces, add a capital letter and the final mark."""
    text = " ".join(w.strip() for w in words if w and w.strip())
    text = " ".join(text.split())
    if not text:
        return ""
    k = 1 if text[0] == "'" else 0              # 'yar'uwata -> 'Yar'uwata
    return text[:k] + text[k].upper() + text[k + 1:] + end
