"""Hausa generation: stage 3 of English -> Hausa. Writes out what transfer_en_ha.py decided:
-n/-r suffixes (yaron, miyar), possessive suffixes (motata), adjective agreement,
ne/ce, word order in the noun phrase, and the final sentence.
"""
from dataclasses import dataclass, field

VOWELS = "aeiouAEIOU"


# ===== A Hausa noun phrase, as the transfer stage hands it over =====

@dataclass
class HNoun:
    word: str                    # Hausa noun, already singular or plural: yaro, yara
    english: str = ""
    kind: str = "noun"           # noun, name, pronoun, indefinite, coordinated
    gender: str = "m"
    number: str = "sg"
    person: str = "3sg.m"        # PAC person: 1sg, 2sg.m, 3sg.f, 3pl, 4 ...
    definite: bool = False
    relative: bool = False       # a relative clause follows: mutumin da ... (always the linker)
    linked: str = ""
    before: list = field(default_factory=list)   # words before the noun: wannan, wasu, babban
    after: list = field(default_factory=list)    # words after the noun: biyu, da yawa, mai zafi
    possessive_suffix: str = ""
    possessor: object = None
    parts: list = field(default_factory=list)

    @property
    def feminine(self):
        """Feminine singular? (decides -r, ce, ta ...)"""
        return self.gender == "f" and self.number == "sg"


# ===== Word-level rules =====

def add_suffix(word, suffix):
    """Attach a suffix to the last word."""
    if not word:
        return word
    head, _, last = word.rpartition(" ")
    if last.endswith("ai"):
        last = last[:-1]
    elif last[-1] not in VOWELS:
        last += "i"
    return (head + " " if head else "") + last + suffix


def linker(word, feminine, linked_form="", definite=False):
    """The -n/-r form used for 'the' (A6) and for 'of' (gidan Musa)."""
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
    return "ce" if noun_phrase.feminine else "ne"


def split_frame(pac_form):
    """'ba ta … ba' -> ('ba ta', 'ba'); 'ya' -> ('ya', '')."""
    if "…" in pac_form:
        before, after = pac_form.split("…")
        return before.strip(), after.strip()
    return pac_form, ""


# ===== Noun phrases =====

def noun_phrase(hn):
    """Write out a Hausa noun phrase in the right order."""
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


# ===== The whole sentence =====

def sentence(words, end="."):
    """Join the words, tidy the spaces, add a capital letter and the final mark."""
    text = " ".join(w.strip() for w in words if w and w.strip())
    text = " ".join(text.split())
    if not text:
        return ""
    k = 1 if text[0] in "'[" else 0             # 'yar'uwata -> 'Yar'uwata; [bath] -> [Bath]
    return text[:k] + text[k].upper() + text[k + 1:] + end
