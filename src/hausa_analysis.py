"""Hausa analysis: stage 1 of Hausa -> English.

  1. split_words   - split into words; join fixed expressions (lokacin da, da wuri)
  2. recognise     - find every possible reading of each word, using the lexicon backwards
  3. split_clauses - cut at commas, kuma/amma, idan/saboda ..., cewa
  4. parse_clause  - find the PAC first: before it is the subject, after it the verb and the rest

Tone is not written, so one form can have several readings (ta = she / her / of);
the words around it decide. Explained in docs/hausa_analysis_explained.md.
"""
import re
from dataclasses import dataclass, field

import english_words as EW
import hausa_lexicon as L
import hausa_words as HW


# ===== Data structures =====

@dataclass
class HToken:
    text: str
    lower: str
    parts: list = field(default_factory=list)
    options: dict = field(default_factory=dict)     # every possible reading: tag -> information
    tag: str = ""


@dataclass
class HNounPhrase:
    text: str
    hausa: str = ""
    english: str = ""
    kind: str = "noun"        # noun, name, pronoun, indefinite, demonstrative, wh, quantity, gap
    person: str = "3sg.m"     # PAC person this noun phrase agrees with
    number: str = "sg"
    gender: str = "m"
    definite: bool = False    # -n/-r or ɗin: "the"
    demonstrative: str = ""
    possessor: object = None  # a person key ("1sg" = my) or another HNounPhrase (gidan Musa)
    adjectives: list = field(default_factory=list)
    quantifier: str = ""      # many, some, every, enough
    count: str = ""
    negative: bool = False    # ba wanda (nobody), babu
    coordinated: list = field(default_factory=list)
    relative_clause: object = None
    which: bool = False       # wane ɗalibi
    english_negative: str = ""  # indefinites in a negative sentence: kowa -> anyone (not everyone)
    from_pac: bool = False    # no subject word: the PAC alone shows the person (Sun tafi)
    after: str = ""           # the Hausa preposition in front of it: a, cikin, kan ... (a gida = at home)


@dataclass
class HPAC:
    text: str
    person: str               # 1sg, 2sg.m, 3sg.f, 3pl, 4 (impersonal) ...
    column: str               # completive, continuous, future, subjunctive, relative completive ...
    negative: bool = False


@dataclass
class HVerb:
    text: str
    hausa: str = ""
    english: str = ""
    form: str = ""
    ability: bool = False     # iya: can
    ever: bool = False        # taɓa: ever / never
    infinitive: object = None # sun so [su fita]: (PAC, HVerb)
    yi_da: bool = False       # yi amfani da ...: the object comes after "da"


@dataclass
class HClause:
    role: str = "main"        # main, coordinated, subordinate, complement, relative
    linker: str = ""
    linker_english: str = ""
    construction: str = ""    # verbal, equational, adjective, possession, locative, existential,
                              # weather, belong, become, command, what-is
    mood: str = "statement"   # statement, yes-no question, wh-question, command
    pac: object = None
    verb: object = None
    subject: object = None
    obj: object = None
    receiver: object = None
    complement: object = None # (kind, value) for ne/ce, adjective and place clauses
    places: list = field(default_factory=list)
    adverbs: list = field(default_factory=list)
    negative: bool = False
    wh_word: str = ""
    wh_role: str = ""         # subject, object, place, time, reason, manner
    focus: object = None      # Ada ce ta dafa miyar: the focused noun phrase / adverb
    gap: str = ""
    please: bool = False
    clauses: list = field(default_factory=list)
    leftovers: list = field(default_factory=list)
    copula: str = ""
    modal: str = ""           # dole ne -> must


@dataclass
class HAnalysis:
    sentence: str
    tokens: list
    clauses: list
    problems: list = field(default_factory=list)


# ===== Step 2 (built once): the lexicon read backwards =====

_R = None


def first_key(row):
    keys = [k.strip() for k in str(row.get("keys", "")).split(";") if k.strip()]
    return keys[0] if keys else ""


def reader():
    """Build every index the analysis needs, once."""
    global _R
    if _R is not None:
        return _R
    tabs = L.tabs()
    R = {"nouns": {}, "verbs": {}, "yi_nouns": {}, "adjs": {}, "pac": {}, "pron": {},
         "suffixes": [], "multi": set(), "names": {}, "numbers": {}}

    def add(index, form, value):
        form = form.strip().lower()
        if not form or form == "nan":
            return
        index.setdefault(form, []).append(value)
        if " " in form and form.split()[0] != HW.DO_VERB:
            R["multi"].add(tuple(form.split()))

    for order, (_, row) in enumerate(tabs["Nouns"].iterrows()):
        eng = first_key(row)
        if not eng or row["status"] == "Wrong":
            continue
        g = row["gender"] or "m"
        number = "pl" if g == "pl" else "sg"
        g = "m" if g == "pl" else g
        base = dict(english=eng, hausa=row["hausa"], gender=g, order=order)
        add(R["nouns"], row["hausa"], dict(base, number=number, linked=False))
        for pl in str(row["plural"]).split(","):
            if pl.strip():
                add(R["nouns"], pl, dict(base, number="pl", linked=False))
        if row["linked_form"]:
            add(R["nouns"], row["linked_form"], dict(base, number=number, linked=True))

    for _, row in tabs["Verbs"].iterrows():
        eng = first_key(row)
        if not eng or row["status"] == "Wrong":
            continue
        yi = str(row["yi_verb"]).startswith("Y")
        if yi:
            add(R["yi_nouns"], row["hausa"], dict(english=eng, hausa=row["hausa"], da="da" in row["yi_verb"]))
            continue
        for col in ("hausa", "before_noun", "before_pronoun", "verbal_noun", "vn_with_object"):
            if row[col]:
                add(R["verbs"], row[col], dict(english=eng, hausa=row["hausa"], form=col,
                                                after_object=row.get("after_object", "")))

    for _, row in tabs["Adjectives"].iterrows():
        eng = first_key(row)
        if not eng or row["status"] == "Wrong":
            continue
        kind = row["type"] or "adjective"
        for col, (g, n) in (("masc", ("m", "sg")), ("fem", ("f", "sg")), ("plural", ("m", "pl"))):
            form = str(row[col]).split(",")[0].strip()
            if not form:
                continue
            info = dict(english=eng, type=kind, gender=g, number=n, linked=False)
            add(R["adjs"], form, info)
            if kind == "adjective" and " " not in form:     # babban, sabuwar, jar (linked, before a noun)
                linked = form + "r" if g == "f" and form.endswith("a") else form + "n"
                add(R["adjs"], linked, dict(info, linked=True))

    fw = tabs["Function words"]
    for _, row in fw[fw["category"] == "PAC"].iterrows():
        person, column = [x.strip() for x in row["features"].split(";")]
        form = row["hausa"].replace("…", " ").replace("...", " ")
        words = tuple(form.split())
        frame = "…" in row["hausa"]
        if frame:                                   # ba ta … ba: the final ba is found later
            words = words[:-1]
        R["pac"].setdefault(words, []).append((person, column))
        if column == "future":                      # negative future: ba + future PAC
            R["pac"].setdefault(("ba",) + words, []).append((person, "negative future"))
    for kind in ("independent", "direct object", "indirect object"):
        for _, row in fw[fw["category"] == f"Pronoun: {kind}"].iterrows():
            R["pron"].setdefault(row["hausa"], []).append((kind, row["features"].strip()))
    for _, row in fw[fw["category"] == "Possessive suffix"].iterrows():
        person = row["features"].split(";")[0].strip()
        R["suffixes"].append((row["hausa"].lstrip("-"), person))
    for _, row in fw[fw["category"] == "Number"].iterrows():
        R["numbers"][row["hausa"]] = row["english"]
    R["suffixes"].sort(key=lambda s: -len(s[0]))     # longest first: nsa before na

    for _, row in tabs["Names"].iterrows():
        if isinstance(row["name"], str) and row["name"]:
            R["names"][row["name"].lower()] = row["gender"] if row["gender"] in ("m", "f") else ""
    for name, sex in EW.NAMES.items():
        R["names"].setdefault(name, sex)

    for table in (HW.COORDINATORS, HW.SUBORDINATORS, HW.QUESTION_WORDS, HW.WHAT_IS, HW.PREPOSITIONS,
                  HW.ADVERBS, HW.QUANTIFIERS, HW.INDEFINITES):
        for k in table:
            if " " in k:
                R["multi"].add(tuple(k.split()))
    for k in [HW.PLEASE] + list(HW.NEGATIVE_SUBJECTS) + list(HW.MODALS):
        if " " in k:
            R["multi"].add(tuple(k.split()))
    _R = R
    return R


def noun_readings(form):
    """Every way to read a written noun: (entry, definite?, owner person or None)."""
    R = reader()
    out = [(e, e["linked"], None, form) for e in R["nouns"].get(form, [])]
    # possessive suffixes: gidana, motata, mahaifiyarta, iyayenka
    for suf, person in R["suffixes"]:
        if form.endswith(suf) and len(form) > len(suf) + 1:
            stem = form[: -len(suf)]
            for s in (stem, stem[:-1] if stem.endswith("i") else None, stem + "i"):
                for e in R["nouns"].get(s or "", []) if s else []:
                    out.append((e, False, person, s))
    # -n / -r / -in for "the" or "of": yaron, miyar, ɗaliban, mutumin
    # A feminine singular noun in -a takes -r; everything else takes -n (so ɗaliban is ɗalibai, not ɗaliba).
    if form.endswith(("n", "r")) and len(form) > 2:
        for s in (form[:-1], form[:-1] + "i", form[:-2] if form.endswith("in") else None):
            for e in R["nouns"].get(s or "", []) if s else []:
                fem_a = e["gender"] == "f" and e["number"] == "sg" and s.endswith("a")
                if (form.endswith("r") and not fem_a) or (form.endswith("n") and fem_a):
                    continue
                out.append((e, True, None, s))
    # Best first: the row that comes first in the tab (core words first), then a reading
    # built on the base word (kawu + na "my uncle") before a plural form (kawuna "uncles").
    out.sort(key=lambda r: (0 if r[3] == r[0]["hausa"] else 1, r[0].get("order", 0)))
    return out


def adjective_readings(form):
    return reader()["adjs"].get(form, [])


# ===== Step 1: words and fixed expressions =====

def split_words(sentence):
    s = sentence.replace("’", "'").replace("‘", "'")
    raw = re.findall(r"[\w'-]+|[.,?!;:]", s)
    tokens = [HToken(text=w, lower=w.lower(), parts=[w.lower()]) for w in raw]
    return join_expressions(tokens)


def join_expressions(tokens):
    """Join fixed expressions into one unit, longest first: abincin dare, lokacin da, da wuri."""
    multi = reader()["multi"]
    out, i = [], 0
    while i < len(tokens):
        for n in (4, 3, 2):
            if i + n > len(tokens):
                continue
            words = [t.lower for t in tokens[i:i + n]]
            candidates = [tuple(words)]
            last = words[-1]
            if last.endswith(("n", "r")):
                candidates.append(tuple(words[:-1] + [last[:-1]]))
            hit = next((c for c in candidates if c in multi), None)
            if hit:
                text = " ".join(t.text for t in tokens[i:i + n])
                tok = HToken(text=text, lower=" ".join(words), parts=words)
                if hit != tuple(words):
                    tok.options["SUFFIX_DEF"] = " ".join(hit)      # aikin gidan = aikin gida + the
                out.append(tok)
                i += n
                break
        else:
            out.append(tokens[i])
            i += 1
    return out


# ===== Step 2: every possible reading of each word =====

def recognise(tokens):
    R = reader()
    for pos, t in enumerate(tokens):
        w = t.lower
        base = t.options.pop("SUFFIX_DEF", None)
        o = t.options
        if w in ".?!;:":
            o["PUNCT"] = w
            continue
        if w == ",":
            o["COMMA"] = w
            continue
        for table, tag in ((HW.COORDINATORS, "COORD"), (HW.SUBORDINATORS, "SUB"), (HW.QUESTION_WORDS, "WH"),
                           (HW.WHAT_IS, "WHATIS"), (HW.PREPOSITIONS, "PREP"), (HW.ADVERBS, "ADV"),
                           (HW.QUANTIFIERS, "QUANT"), (HW.INDEFINITES, "INDEF"), (HW.DEMONSTRATIVES, "DEM"),
                           (HW.WHICH, "WHICH"), (HW.OF_WORDS, "OF"), (HW.MAI_WORDS, "MAI"),
                           (HW.EXISTENTIAL, "EXIST")):
            if w in table:
                o[tag] = table[w]
        if w in HW.COPULA:
            o["COP"] = "f" if w == "ce" else "m"
        if w == HW.NEGATIVE:
            o["NEG"] = w
        if w == HW.NEGATIVE_COMMAND:
            o["KADA"] = w
        if w == HW.PLEASE:
            o["PLEASE"] = w
        if w in HW.NEGATIVE_SUBJECTS:
            o["NOBODY"] = HW.NEGATIVE_SUBJECTS[w]
        if w in HW.MODALS:
            o["MODAL"] = HW.MODALS[w]
        if w == HW.COMPLEMENTISER:
            o["CEWA"] = w
        if w == HW.RECEIVER_MARKER:
            o["WA"] = w
        if w == "da":
            o["DA"] = w
        if w == HW.DEFINITE_WORD:
            o["DIN"] = w
        if w in HW.WEATHER:
            o["WEATHER"] = HW.WEATHER[w]
        if w in R["pron"]:
            o["PRON"] = R["pron"][w]
        if (w,) in R["pac"]:
            o["PAC1"] = R["pac"][(w,)]
        if any(len(k) > 1 and k[0] == w for k in R["pac"]):
            o["PACPART"] = w                              # za (za ka), ba (ba ta)
        if w in HW.EXTRA_VERB_FORMS:
            hausa, english, form = HW.EXTRA_VERB_FORMS[w]
            o.setdefault("VERB", []).append(dict(english=english, hausa=hausa, form=form, after_object=""))
        if w in R["numbers"]:
            o["NUM"] = R["numbers"][w]
        if w in R["verbs"]:
            o["VERB"] = R["verbs"][w]
        if w in R["yi_nouns"]:
            o["YINOUN"] = R["yi_nouns"][w]
        adj = adjective_readings(w)
        if adj:
            kind = adj[0]["type"]
            o["ADJ" if kind == "adjective" else "QNOUN"] = adj
        nouns = [(e, True, None, base) for e in R["nouns"].get(base, [])] if base else noun_readings(w)
        if nouns:
            o["NOUN"] = nouns
        name = w in R["names"] or w in HW.PLACE_NAMES or w in EW.PLACE_NAMES
        if name or (t.text[0].isupper() and pos > 0 and not (set(o) - {"WEATHER"})):
            o["NAME"] = HW.PLACE_NAMES.get(w, t.text)
        if not o:
            o["UNKNOWN"] = w
    return tokens


# ===== Step 3: cutting the sentence into clauses =====

def has(t, *tags):
    return t is not None and any(tag in t.options for tag in tags)


def pac_at(toks, i):
    """A PAC starting at position i? Returns (number of words, readings) or None."""
    R = reader()
    for n in (3, 2, 1):
        words = tuple(t.lower for t in toks[i:i + n])
        if len(words) == n and words in R["pac"]:
            if words == ("a",):                     # a alone is the preposition "in"
                continue
            nxt = toks[i + n] if i + n < len(toks) else None
            at_end = nxt is None or has(nxt, "PUNCT", "COMMA")
            if at_end and any(c == "relative continuous" for _, c in R["pac"][words]):
                return n, R["pac"][words]           # Ina Musa yake? - yake can end a question
            if at_end or (has(nxt, "COP") and not has(nxt, "VERB")):
                continue                            # "ya gan ta." - ta at the end is an object
            return n, R["pac"][words]
    return None


def clause_has_pac(toks):
    return any(pac_at(toks, i) for i in range(len(toks)))


def split_clauses(tokens):
    """Return a list of (role, Hausa linker, English linker, tokens)."""
    body = [t for t in tokens if not has(t, "PUNCT")]
    chunks, cur = [], []
    for t in body:
        if has(t, "COMMA"):
            if cur:
                chunks.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        chunks.append(cur)
    # split again at kuma / amma / don haka inside a chunk, when a clause follows
    pieces = []
    for ch in chunks:
        start = 0
        for k in range(1, len(ch)):
            if has(ch[k], "COORD", "SUB") and clause_has_pac(ch[k + 1:]) and clause_has_pac(ch[start:k]) \
                    and not inside_relative(ch, k):
                pieces.append(ch[start:k])
                start = k
        pieces.append(ch[start:])
    out = []
    counterfactual = sum(1 for p in pieces if p and p[0].lower == "da" and clause_has_pac(p[1:4])) >= 2
    for number, p in enumerate(pieces):
        role, link, eng = "main", "", ""
        first = p[0]
        if number > 0 and len(p) > 2 and p[1].lower == "kuma" and has(first, "PRON", "NOUN", "NAME"):
            role, link, eng, p = "coordinated", "kuma", "and", [first] + p[2:]   # ..., ni kuma na wanke ...
        elif has(first, "COORD"):
            role, link, eng, p = "coordinated", first.lower, first.options["COORD"], p[1:]
        elif first.lower == "da" and counterfactual:
            role, link, eng, p = "subordinate", "da", "counterfactual", p[1:]
        elif has(first, "SUB") and not (first.lower == "har" and pac_at(p, 1) and any(
                t.lower == "?" for t in tokens) and number == 0):
            role, link, eng, p = "subordinate", first.lower, first.options["SUB"], p[1:]
        elif first.lower == "bayan" and clause_has_pac(p[1:]):
            role, link, eng, p = "subordinate", "bayan", "after", p[1:]
        out.append((role, link, eng, p))
    # the clause after "Da ..." (counterfactual) is the main clause "da ..."
    if counterfactual:
        seen = 0
        for n, (role, link, eng, p) in enumerate(out):
            if link == "da":
                seen += 1
                if seen == 2:
                    out[n] = ("main", "da", "counterfactual", p)
    return out


# ===== Step 4: noun phrases =====

def person_of(np):
    if np.kind in ("pronoun", "gap"):
        return np.person
    return "3pl" if np.number == "pl" else f"3sg.{np.gender}"


def preferred(reading):
    """Choose the English word for a Hausa noun (hausa_words.PREFERRED_ENGLISH first)."""
    e, _, _, stem = reading
    for key in (stem, e["hausa"]):
        if key in HW.PREFERRED_ENGLISH:
            return HW.PREFERRED_ENGLISH[key]
    return e["english"]


def parse_np(toks, i, receiver=False, allow_relative=True):
    """Read a noun phrase starting at i. Returns (HNounPhrase, next i) or (None, i)."""
    if i >= len(toks):
        return None, i
    start = i
    t = toks[i]
    np = HNounPhrase(text="")
    if has(t, "NOBODY"):
        np = HNounPhrase(text=t.text, english=t.options["NOBODY"], kind="indefinite", negative=True)
        return np, i + 1
    if has(t, "INDEF") and not has(t, "NOUN"):
        pos, neg = t.options["INDEF"]
        np = HNounPhrase(text=t.text, hausa=t.lower, english=pos, kind="indefinite", english_negative=neg)
        return np, i + 1
    independent = has(t, "PRON") and any(k == "independent" for k, _ in t.options["PRON"])
    if has(t, "PRON") and (independent or not has(t, "NOUN", "NAME")):
        _, person = next(((k, p) for k, p in t.options["PRON"] if k == "independent"), t.options["PRON"][0])
        np = HNounPhrase(text=t.text, hausa=t.lower, kind="pronoun", person=person,
                         number="pl" if "pl" in person else "sg", gender="f" if person.endswith(".f") else "m")
        if independent and i + 2 < len(toks) and has(toks[i + 1], "DA") and has(toks[i + 2], "NAME", "NOUN") \
                and not receiver:             # Ni da Musa (Musa and I)
            other, j = parse_np(toks, i + 2, allow_relative=False)
            if other is not None:
                both = HNounPhrase(text=" ".join(x.text for x in toks[i:j]), kind="coordinated", number="pl",
                                   coordinated=[np, other])
                both.person = "1pl" if person.startswith("1") else "2pl" if person.startswith("2") else "3pl"
                return both, j
        return np, i + 1
    if has(t, "DEM") and not (i + 1 < len(toks) and has(toks[i + 1], "NOUN", "ADJ")):
        np = HNounPhrase(text=t.text, hausa=t.lower, english=t.options["DEM"], kind="demonstrative")
        return np, i + 1
    if has(t, "DEM"):
        np.demonstrative = t.options["DEM"]
        i += 1
    if i < len(toks) and has(toks[i], "WHICH"):
        np.which = True
        i += 1
    if i < len(toks) and has(toks[i], "QUANT") and toks[i].options["QUANT"][1] == "before":
        np.quantifier = toks[i].options["QUANT"][0]
        i += 1
    while i < len(toks) and has(toks[i], "ADJ") and toks[i].options["ADJ"][0]["linked"] \
            and i + 1 < len(toks) and has(toks[i + 1], "NOUN"):
        np.adjectives.append(toks[i].options["ADJ"][0]["english"])     # babban gida, jar jaka
        i += 1
    if i >= len(toks):
        return None, start
    t = toks[i]
    linked = False
    if has(t, "NAME") and not (has(t, "NOUN") and i == 0 and t.lower not in reader()["names"]):
        name = t.options["NAME"]
        np.kind, np.hausa, np.english = "name", t.text, name
        np.gender = reader()["names"].get(t.lower, "") or "m"
        i += 1
    elif has(t, "NOUN"):
        readings = t.options["NOUN"]
        entry, linked, owner, _ = readings[0]
        np.hausa, np.english = entry["hausa"], preferred(readings[0])
        np.gender, np.number = entry["gender"], entry["number"]
        if owner:
            np.possessor = owner
        i += 1
        if i < len(toks) and has(toks[i], "DIN"):         # fim ɗin
            linked = True
            i += 1
    elif has(t, "QNOUN", "YINOUN") and not receiver:
        info = (t.options.get("QNOUN") or t.options.get("YINOUN"))[0]
        np.hausa, np.english = t.lower, info["english"]
        i += 1
    else:
        return None, start
    np.definite = linked

    # owner after the linker: gidan Musa; adjective after the linker: waƙoƙin gargajiya
    if linked and i < len(toks):
        nxt = toks[i]
        if has(nxt, "QNOUN") and nxt.options["QNOUN"][0]["type"] == "noun after linker":
            np.adjectives.append(nxt.options["QNOUN"][0]["english"])
            np.definite = False
            i += 1
        elif not receiver and has(nxt, "NOUN", "NAME") and not has(nxt, "DA", "PREP", "VERB", "WEATHER") \
                and not pac_at(toks, i) and not has(nxt, "COP"):
            owner, j = parse_np(toks, i, receiver=True, allow_relative=False)
            if owner is not None:
                np.possessor = owner
                np.definite = False
                i = j

    # after the noun: number, mai X, adjectives, da yawa
    while i < len(toks):
        t = toks[i]
        if has(t, "NUM"):
            np.count = t.options["NUM"]
            np.number = "pl"
            i += 1
        elif has(t, "MAI") and i + 1 < len(toks) and has(toks[i + 1], "QNOUN"):
            np.adjectives.append(toks[i + 1].options["QNOUN"][0]["english"])
            i += 2
        elif has(t, "ADJ") and not t.options["ADJ"][0]["linked"] \
                and not has(toks[i + 1] if i + 1 < len(toks) else None, "COP") \
                and not (receiver and has(t, "NOUN")):
            np.adjectives.append(t.options["ADJ"][0]["english"])
            i += 1
        elif has(t, "QUANT") and t.options["QUANT"][1] == "after":
            np.quantifier = t.options["QUANT"][0]
            i += 1
        else:
            break

    np.text = " ".join(x.text for x in toks[start:i])
    np.person = person_of(np)

    if allow_relative and i < len(toks) and has(toks[i], "DA") and (linked or np.kind == "name") \
            and clause_has_pac(toks[i + 1:]) or (allow_relative and i < len(toks) and has(toks[i], "DA")
                                                 and linked and has_cop(toks[i + 1:])):
        end = relative_end(toks, i + 1)
        rel_toks = toks[i + 1:end]
        if rel_toks:
            np.relative_clause = parse_relative(rel_toks, np)
            np.definite = True
            np.text = " ".join(x.text for x in toks[start:end])
            return np, end

    if i + 1 < len(toks) and has(toks[i], "DA") and not linked and has(toks[i + 1], "NAME", "NOUN", "PRON") \
            and not receiver:
        other, j = parse_np(toks, i + 1, allow_relative=False)
        if other is not None:
            both = HNounPhrase(text=" ".join(x.text for x in toks[start:j]), kind="coordinated", number="pl",
                               coordinated=[np, other])
            both.person = "1pl" if any(p.person.startswith("1") for p in (np, other)) else "3pl"
            return both, j
    return np, i


def has_cop(toks):
    return any(has(t, "COP") for t in toks)


def relative_end(toks, k):
    """Where does a relative clause that starts at k end?"""
    pacs = [p for p in range(k, len(toks)) if pac_at(toks, p)
            and not (p > k and has(toks[p], "PRON") and has(toks[p - 1], "VERB"))]
    cops = [p for p in range(k, len(toks)) if has(toks[p], "COP")]
    for c in cops:
        if c + 1 < len(toks) and pac_at(toks, c + 1):
            return c + 1
    if len(pacs) >= 2:
        return pacs[1]
    if cops and cops[-1] == len(toks) - 1:
        pred = cops[-1] - 1
        if pred - 1 >= k and has(toks[pred - 1], "MAI", "OF", "NEG"):
            pred -= 1
        return pred
    return len(toks)


def parse_relative(toks, head):
    """The clause after 'da'. Its subject or object is the head noun."""
    found = pac_at(toks, 0)
    agrees = found and any(p == head.person or (head.number == "pl" and p == "3pl") for p, _ in found[1])
    if found and agrees:                    # Mutumin da [ya kira jiya]: the subject is missing
        gap = HNounPhrase(text="", kind="gap", person=head.person, number=head.number, gender=head.gender,
                          english=head.english)
        cl = parse_clause(toks, role="relative", linker="da", gap_subject=gap)
        cl.gap = "subject"
    else:                                   # Matar da [muka ziyarta]: the object is missing
        cl = parse_clause(toks, role="relative", linker="da")
        owner_suffix = any(isinstance(np, HNounPhrase) and np.possessor == head.person
                           for np in (cl.subject, cl.obj))
        owner_receiver = cl.receiver is not None and cl.receiver.person == head.person
        # whose: mahaifinta (her father) / aka sace masa keke (his bicycle was stolen)
        cl.gap = "possessor" if owner_suffix or owner_receiver else "object"
    return cl


# ===== Step 4: clauses =====

# Set by analyse(): does the sentence end in "?"  (then ina / me are question words)
SENTENCE_IS_QUESTION = False


def choose_pac(readings, toks, start, end, context):
    """Pick one reading of an ambiguous PAC."""
    ends_with_ba = toks and toks[-1].lower == "ba" and end < len(toks)
    by_col = {c: p for p, c in readings}

    def pick(*cols):
        for c in cols:
            if c in by_col:
                return by_col[c], c
        return None

    if ends_with_ba and pick("negative completive"):
        return pick("negative completive")
    if context == "subjunctive" and pick("subjunctive"):
        return pick("subjunctive")
    if context == "relative":
        hit = pick("relative completive", "relative continuous")
        if hit:
            return hit
    return pick("completive", "continuous", "future", "negative continuous", "negative future",
                "relative completive", "relative continuous", "subjunctive", "negative completive") \
        or (readings[0][0], readings[0][1])


def make_pac(text, person, column):
    negative = column.startswith("negative")
    return HPAC(text=text, person=person, column=column, negative=negative)


def parse_clause(toks, role="main", linker="", gap_subject=None, context=""):
    """Find the parts of one Hausa clause."""
    cl = HClause(role=role, linker=linker)
    toks = [t for t in toks if not has(t, "PUNCT")]
    if not toks:
        return cl
    i = 0
    if role == "relative" or linker in ("lokacin da", "yayin da", "bayan da", "bayan"):
        context = "relative"

    # --- please / kada / har (already)
    if has(toks[i], "PLEASE"):
        cl.please, cl.mood = True, "command"
        i += 1
        context = "subjunctive"
    if i < len(toks) and has(toks[i], "KADA"):
        cl.mood, cl.negative = "command", True
        i += 1
        context = "subjunctive"
    if i < len(toks) and toks[i].lower == "har" and pac_at(toks, i + 1):
        cl.adverbs.append("already")
        i += 1
    if i < len(toks) and has(toks[i], "MODAL"):          # Dole ne ka tafi
        cl.modal = toks[i].options["MODAL"]
        i += 1
        context = "subjunctive"
    if i >= len(toks):
        cl.construction = cl.construction or "command"
        return cl

    # --- there is / there is no
    if has(toks[i], "EXIST"):
        cl.construction = "existential"
        cl.negative = toks[i].options["EXIST"]
        np, j = parse_np(toks, i + 1)
        cl.subject = np
        return parse_rest(cl, toks, j)

    # --- Mene ne X? / Wane ne X?
    if has(toks[i], "WHATIS"):
        cl.construction, cl.mood = "what-is", "wh-question"
        cl.wh_word = toks[i].options["WHATIS"]
        np, j = parse_np(toks, i + 1)
        cl.subject = np
        return parse_rest(cl, toks, j)

    # --- question word first (C12)
    is_question = SENTENCE_IS_QUESTION
    if has(toks[i], "WH", "WHICH") and (toks[i].lower not in ("ina", "me") or is_question or
                                        toks[i].lower == "me ya sa"):
        cl.mood = "wh-question"
        context = "relative"
        if has(toks[i], "WHICH"):                    # Wane ɗalibi ne ya ...
            np, j = parse_np(toks, i, allow_relative=False)
            if j < len(toks) and has(toks[j], "COP"):
                j += 1
            cl.wh_word, wh_np, i = "which", np, j
        else:
            cl.wh_word = toks[i].options["WH"]
            wh_np = HNounPhrase(text=toks[i].text, english=cl.wh_word, kind="wh")
            i += 1
        role_by_word = {"where": "place", "when": "time", "why": "reason", "how": "manner"}
        if cl.wh_word in role_by_word:
            cl.wh_role = role_by_word[cl.wh_word]
        elif pac_at(toks, i) and any(p.startswith("3") or p == "4" for p, _ in pac_at(toks, i)[1]) \
                and not (wh_np.kind == "wh" and all(p == "4" for p, _ in pac_at(toks, i)[1])):
            cl.wh_role, gap_subject = "subject", wh_np            # Wa ya buɗe ƙofar?
        elif pac_at(toks, i):                                     # Me kake dafawa? (kake = you)
            cl.wh_role = "object"
            cl.obj = wh_np
            wh_np.person = person_of(wh_np) if wh_np.kind != "wh" else "3sg.m"
        else:                                        # Wa Ada ta gayyata?
            cl.wh_role = "object"
            cl.obj = wh_np

    # --- focus (S10): X ne/ce + clause with a PAC
    if not cl.wh_word:
        for k in range(i + 1, len(toks) - 1):
            say_verb = has(toks[k], "VERB") and k > 0 and pac_at(toks, k - 1)   # ya ce = he said
            focus_ok = has(toks[k], "COP") and not say_verb and clause_has_pac(toks[k + 1:]) \
                and not any(has(x, "DA") for x in toks[i:k])
            if focus_ok:
                focus_toks = toks[i:k]
                focus = parse_focus(focus_toks)
                cl.focus = focus
                context = "relative"
                i = k + 1
                if pac_at(toks, i) and isinstance(focus, HNounPhrase):
                    gap_subject = focus                # Ada ce [ta dafa miyar]
                    cl.gap = "subject"
                else:
                    cl.gap = "object or adverb"
                break

    # --- nobody
    if gap_subject is None and i < len(toks) and has(toks[i], "NOBODY"):
        cl.subject = HNounPhrase(text=toks[i].text, english=toks[i].options["NOBODY"], kind="indefinite",
                                 negative=True)
        cl.negative = True
        i += 1
        found = pac_at(toks, i)
        if found:
            n, readings = found
            person, column = choose_pac(readings, toks, i, i + n, "relative")
            cl.pac = make_pac(" ".join(t.text for t in toks[i:i + n]), person, column)
            return parse_predicate(cl, toks, i + n)

    if i >= len(toks):
        cl.construction = "what-is"
        return cl

    # --- non-verbal clause ending in ne/ce: Ada malama ce
    belong_end = len(toks) >= 3 and has(toks[-3], "OF") and has(toks[-2], "NOUN", "NAME")
    if has(toks[-1], "COP") and not any(pac_at(toks, p) for p in range(i, len(toks) - 1)
                                        if not inside_relative(toks, p)
                                        and not (belong_end and p == len(toks) - 3)):
        return parse_copular(cl, toks, i)

    # --- negative possession: Ba ni da mota
    if toks[i].lower == "ba" and i + 2 < len(toks) and has(toks[i + 1], "PRON") and toks[i + 2].lower == "da":
        kind, person = next(((k, p) for k, p in toks[i + 1].options["PRON"] if k == "direct object"),
                            toks[i + 1].options["PRON"][0])
        cl.subject = HNounPhrase(text=toks[i + 1].text, kind="pronoun", person=person,
                                 number="pl" if "pl" in person else "sg")
        cl.pac = make_pac("ba", person, "negative continuous")
        cl.negative = True
        cl.construction = "possession"
        np, j = parse_np(toks, i + 3)
        cl.obj = np
        return parse_rest(cl, toks, j)

    # --- time and manner words before the subject: Kullum yana zuwa, Jiya na tafi kasuwa
    while gap_subject is None and i < len(toks) - 1 and toks[i].lower in HW.ADVERBS and not pac_at(toks, i) \
            and not has(toks[i], "NAME", "PRON", "PREP"):
        cl.adverbs.append(toks[i].options["ADV"])
        i += 1

    # --- subject, then the PAC
    if gap_subject is not None:
        cl.subject = gap_subject
        j = i
    elif pac_at(toks, i):
        j = i                                       # no subject word: Sun tsabtace ajin
    else:
        np, j = parse_np(toks, i)
        if np is not None and pac_at(toks, j):
            cl.subject = np
        else:
            j = next((p for p in range(i, len(toks)) if pac_at(toks, p)), None)
            if j is None:
                return parse_command(cl, toks, i)
            if j > i:
                cl.subject, _ = parse_np(toks[:j], i)
    n, readings = pac_at(toks, j)
    person, column = choose_pac(readings, toks, j, j + n, context)
    cl.pac = make_pac(" ".join(t.text for t in toks[j:j + n]), person, column)
    cl.negative = cl.negative or cl.pac.negative
    if cl.subject is None and j > i and "UNKNOWN" in toks[i].options:   # unknown subject: keep it, in [brackets]
        words = " ".join(t.text for t in toks[i:j])
        cl.subject = HNounPhrase(text=words, english=f"[{words}]", kind="name", person=person,
                                 number="pl" if "pl" in person else "sg")
    if cl.subject is None:
        cl.subject = HNounPhrase(text="", kind="pronoun", person=person, from_pac=True,
                                 number="pl" if "pl" in person else "sg",
                                 gender="f" if person.endswith(".f") else "m")
    if context == "subjunctive" or cl.mood == "command":
        cl.mood = "command" if role == "main" and cl.mood == "command" else cl.mood
    return parse_predicate(cl, toks, j + n)


def inside_relative(toks, p):
    """Is position p inside a relative clause (after noun-n/-r + da)?"""
    for q in range(p - 1, 0, -1):
        if has(toks[q], "DA") and has(toks[q - 1], "NOUN") and any(r[1] for r in toks[q - 1].options["NOUN"]):
            return True
    return False


def parse_focus(toks):
    """The focused part before ne/ce: a noun phrase, a place (A Legas) or a time word (Jiya)."""
    if not toks:
        return None
    if has(toks[0], "PREP"):
        np, _ = parse_np(toks, 1)
        return (toks[0].options["PREP"], np)
    if has(toks[0], "ADV") and len(toks) == 1:
        return toks[0].options["ADV"]
    np, _ = parse_np(toks, 0)
    return np


def parse_copular(cl, toks, i):
    """X [ba] Y [ba] ne/ce:  equational, adjective, mai + noun, or na/ta X (belonging)."""
    cop = len(toks) - 1
    body = toks[i:cop]
    negative = len(body) > 2 and body[-1].lower == "ba" and any(t.lower == "ba" for t in body[:-1])
    if negative:
        first_ba = next(k for k, t in enumerate(body) if t.lower == "ba")
        x_toks, y_toks = body[:first_ba], body[first_ba + 1:-1]
        cl.negative = True
    else:
        y_len = 1
        if len(body) >= 3 and has(body[-2], "MAI", "OF"):
            y_len = 2
        if len(body) >= 2 and has(body[-1], "NOUN", "NAME") and has(body[-2], "OF"):
            y_len = 2
        x_toks, y_toks = body[:-y_len], body[-y_len:]
    if len(x_toks) == 1 and x_toks[0].lower in HW.TIME_SUBJECTS:      # Yau Juma'a ce
        cl.subject = HNounPhrase(text=x_toks[0].text, english=HW.TIME_SUBJECTS[x_toks[0].lower], kind="name")
    else:
        cl.subject, _ = parse_np(x_toks, 0) if x_toks else (None, 0)
        if cl.subject is None and x_toks and "UNKNOWN" in x_toks[0].options:
            words = " ".join(t.text for t in x_toks)
            cl.subject = HNounPhrase(text=words, english=f"[{words}]", kind="name")
    y = y_toks[0] if y_toks else None
    if y is None:
        cl.construction = "equational"
    elif len(y_toks) == 1 and y.lower in HW.POSSESSIVE_PRONOUNS:        # Motar tawa ce
        cl.construction = "equational"
        cl.complement = ("noun", HW.POSSESSIVE_PRONOUNS[y.lower])
    elif has(y, "OF") and len(y_toks) > 1:            # Littafin na Musa ne
        cl.construction = "belong"
        owner, _ = parse_np(y_toks, 1)
        cl.complement = ("owner", owner)
    elif has(y, "MAI") and len(y_toks) > 1:           # Ada mai gaskiya ce
        cl.construction = "adjective"
        info = (y_toks[1].options.get("QNOUN") or [{"english": y_toks[1].lower}])[0]
        cl.complement = ("adjective", info["english"])
    elif has(y, "ADJ") and len(y_toks) == 1:          # Wannan gida babba ne
        cl.construction = "adjective"
        cl.complement = ("adjective", y.options["ADJ"][0]["english"])
    else:                                             # Ada malama ce
        cl.construction = "equational"
        pred, _ = parse_np(y_toks, 0, allow_relative=False)
        cl.complement = ("noun", pred)
        if pred is None:                              # a word not in the lexicon: keep it, in [brackets]
            cl.leftovers = [t.text for t in y_toks]
    cl.copula = toks[cop].lower
    return cl


def parse_command(cl, toks, i):
    """No PAC: a command (Zauna. Kawo littattafan nan.) or something not understood."""
    if i < len(toks) and has(toks[i], "VERB", "YINOUN"):
        cl.mood = "command"
        cl.construction = "command"
        cl.subject = HNounPhrase(text="", kind="pronoun", person="2sg.m", from_pac=True)
        return parse_predicate(cl, toks, i, command=True)
    cl.leftovers = [t.text for t in toks[i:]]
    return cl


def verb_reading(t, prefer):
    """The verb readings of a token, best first. prefer: 'vn' after a continuous PAC, else 'finite'."""
    rs = t.options.get("VERB", [])
    order = ("verbal_noun", "vn_with_object", "hausa", "before_noun", "before_pronoun") if prefer == "vn" else \
            ("hausa", "before_noun", "before_pronoun", "verbal_noun", "vn_with_object")
    rs = sorted(rs, key=lambda r: order.index(r["form"]) if r["form"] in order else 9)
    if rs:
        r = rs[0]
        eng = HW.PREFERRED_ENGLISH.get(r["hausa"], r["english"])
        return HVerb(text=t.text, hausa=r["hausa"], english=eng, form=r["form"])
    return None


def parse_verb(toks, k, continuous):
    """The verb group at k. Returns (HVerb or None, next k, extra) where extra describes yi + noun."""
    if k >= len(toks):
        return None, k, None
    t = toks[k]
    if t.lower == HW.DO_VERB and k + 1 < len(toks):
        n = toks[k + 1]
        if has(n, "YINOUN"):                               # ya yi dariya -> laughed
            info = n.options["YINOUN"][0]
            v = HVerb(text=f"{t.text} {n.text}", hausa=info["hausa"], english=info["english"], form="yi",
                      yi_da=info["da"])
            return v, k + 2, None
        if has(n, "WEATHER"):                              # an yi iska -> it was windy
            q = n.options.get("QNOUN")
            return None, k + 2, ("weather", n.options["WEATHER"], q[0]["english"] if q else n.options["WEATHER"])
        if has(n, "QNOUN"):                                # ya yi fushi -> became angry
            return None, k + 2, ("become", n.options["QNOUN"][0]["english"])
        return HVerb(text=t.text, hausa="yi", english="do", form="hausa"), k + 1, None
    if t.lower == HW.ABILITY_VERB:                         # ta iya iyo
        v, k2, extra = parse_verb(toks, k + 1, True)
        if v is None and k + 1 < len(toks) and has(toks[k + 1], "YINOUN"):
            info = toks[k + 1].options["YINOUN"][0]
            v, k2 = HVerb(text=toks[k + 1].text, hausa=info["hausa"], english=info["english"], form="yi"), k + 2
        if v is not None:
            v.ability = True
            v.text = f"{t.text} {v.text}"
            return v, k2, extra
    if t.lower == HW.EVER_VERB and k + 1 < len(toks):     # ban taɓa ganin
        v, k2, extra = parse_verb(toks, k + 1, True)
        if v is not None:
            v.ever = True
            v.text = f"{t.text} {v.text}"
            return v, k2, extra
    if has(t, "VERB"):
        return verb_reading(t, "vn" if continuous else "finite"), k + 1, None
    if has(t, "YINOUN") and continuous:                    # suna wasa -> are playing
        info = t.options["YINOUN"][0]
        v = HVerb(text=t.text, hausa=info["hausa"], english=info["english"], form="yi", yi_da=info["da"])
        return v, k + 1, None
    return None, k, None


def parse_predicate(cl, toks, k, command=False):
    """Everything after the PAC: verb (or da / place / quality noun), objects, places, times, final ba."""
    pac = cl.pac
    continuous = pac is not None and "continuous" in pac.column
    impersonal = pac is not None and pac.person == "4"
    t = toks[k] if k < len(toks) else None
    if t is None and continuous and cl.wh_role == "place":      # Ina Musa yake? (Where is Musa?)
        cl.construction = "locative"
        cl.complement = ("place adverb", "where")
        return cl

    # --- continuous PAC without a verb
    if continuous and t is not None:
        parts = t.parts if len(t.parts) > 1 and t.parts[0] == "da" else None
        if t.lower == "da" or parts:
            rest = toks[k + 1:] if not parts else split_off_da(t) + toks[k + 1:]
            nxt = rest[0] if rest else None
            if has(nxt, "QNOUN") and nxt.options["QNOUN"][0]["type"] in ("noun with da", "verb"):
                cl.construction = "adjective"               # Miyar tana da zafi
                cl.complement = ("adjective", nxt.options["QNOUN"][0]["english"])
                return parse_rest(cl, rest, 1)
            cl.construction = "possession"                  # Ada tana da mota
            np, j = parse_np(rest, 0)
            cl.obj = np
            return parse_rest(cl, rest, j)
        if has(t, "WEATHER") and impersonal:                 # Ana ruwa, Ana sanyi
            cl.construction = "weather"
            cl.complement = ("weather", t.options["WEATHER"])
            return parse_rest(cl, toks, k + 1)
        if has(t, "QNOUN") and not has(t, "VERB"):           # Yaran suna farin ciki
            cl.construction = "adjective"
            cl.complement = ("adjective", t.options["QNOUN"][0]["english"])
            return parse_rest(cl, toks, k + 1)
        if has(t, "PREP") and not has(t, "VERB"):            # Yaran suna cikin gida
            cl.construction = "locative"
            np, j = parse_np(toks, k + 1)
            if np is not None:
                np.after = t.lower
            cl.complement = ("place", (t.options["PREP"], np))
            return parse_rest(cl, toks, j)
        if has(t, "NOUN", "NAME") and not has(t, "VERB", "YINOUN"):   # Musa yana kasuwa
            np, j = parse_np(toks, k)
            cl.construction = "locative"
            cl.complement = ("place", ("at", np))
            return parse_rest(cl, toks, j)
        if has(t, "ADV") and not has(t, "VERB", "YINOUN"):   # muna nan
            cl.construction = "locative"
            cl.complement = ("place adverb", t.options["ADV"])
            return parse_rest(cl, toks, k + 1)

    # --- a quality word that Hausa expresses as a verb: Littafin ya ɓata
    if t is not None and has(t, "QNOUN") and t.options["QNOUN"][0]["type"] == "verb" and not has(t, "VERB"):
        cl.construction = "adjective"
        cl.complement = ("adjective", t.options["QNOUN"][0]["english"])
        return parse_rest(cl, toks, k + 1)

    # --- feelings: Ina jin yunwa (I am hungry), Zan ji ƙishin ruwa
    if t is not None and t.lower in ("jin", "ji") and k + 1 < len(toks):
        for n in (2, 1):
            words = " ".join(x.lower for x in toks[k + 1:k + 1 + n])
            if len(toks) > k + n and words in HW.FEELINGS:
                cl.construction = "adjective"
                cl.complement = ("adjective", HW.FEELINGS[words])
                return parse_rest(cl, toks, k + 1 + n)

    # --- verb group
    verb, k, extra = parse_verb(toks, k, continuous)
    if extra is not None:
        kind, word = extra[0], extra[1]
        sky = isinstance(cl.subject, HNounPhrase) and cl.subject.hausa == "sama"
        if kind == "weather" and not (impersonal or sky):  # Musa ya yi sanyi: Musa became cold
            kind, word = "become", extra[2]
        if kind == "become":
            cl.construction = "become"
            cl.complement = ("adjective", word)
        else:
            cl.construction = "weather"
            cl.complement = ("weather", word)
        return parse_rest(cl, toks, k)
    if verb is None:
        cl.construction = cl.construction or "verbal"
        cl.leftovers = [x.text for x in toks[k:] if not has(x, "NEG")]
        return cl
    if verb.hausa in HW.STATE_VERBS and not (k < len(toks) and has(toks[k], "NOUN", "NAME", "PRON")):
        cl.construction = "adjective"                 # Mun gaji -> We are tired
        cl.complement = ("adjective", HW.STATE_VERBS[verb.hausa])
        return parse_rest(cl, toks, k)
    cl.verb = verb
    cl.construction = "command" if command else "verbal"
    # an yi + noun (not a yi-verb): there was ...
    if impersonal and verb.english == "do" and k < len(toks) and not has(toks[k], "VERB"):
        cl.construction = "existential"
        np, j = parse_np(toks, k)
        cl.subject = np
        cl.verb = None
        return parse_rest(cl, toks, j)

    # "ya ce" + clause
    if (verb.hausa == HW.SAY_VERB or verb.english == "say") and clause_has_pac(toks[k:]):
        cl.clauses.append(parse_clause(toks[k:], role="complement", linker=""))
        return cl

    # infinitive: sun so [su fita waje]
    if k + 1 < len(toks) and has(toks[k], "PAC1") and has(toks[k + 1], "VERB", "YINOUN"):
        readings = toks[k].options["PAC1"]
        person = next((p for p, c in readings if c == "subjunctive"), readings[0][0])
        inf, k2, _ = parse_verb(toks, k + 1, False)
        if inf is not None:
            verb.infinitive = (person, inf)
            k = k2

    # receiver and object
    k = parse_objects(cl, toks, k)
    return parse_rest(cl, toks, k)


def split_off_da(t):
    """'da kyau' (one unit) after a continuous PAC is really da + kyau."""
    out = []
    for w in t.parts[1:]:
        tok = HToken(text=w, lower=w, parts=[w])
        recognise([tok])
        out.append(tok)
    return out


def parse_objects(cl, toks, k):
    """wa + receiver, receiver pronoun (masa), give + receiver + thing, the object."""
    R = reader()
    verb = cl.verb
    io = {f for f, rs in R["pron"].items() if any(kind == "indirect object" for kind, _ in rs)}
    # wa + receiver / receiver pronoun
    if k < len(toks) and has(toks[k], "WA") and k + 1 < len(toks):
        rec, j = parse_np(toks, k + 1, receiver=True)
        if rec is not None:
            cl.receiver, k = rec, j
    elif k < len(toks) and toks[k].lower in io:
        _, person = next((x for x in R["pron"][toks[k].lower] if x[0] == "indirect object"))
        cl.receiver = HNounPhrase(text=toks[k].text, kind="pronoun", person=person,
                                  number="pl" if "pl" in person else "sg")
        k += 1
    # ba (give) + pronoun + noun: the pronoun is the receiver
    if verb is not None and verb.hausa == "ba" and cl.receiver is None and k + 1 < len(toks) \
            and has(toks[k], "PRON") and has(toks[k + 1], "NOUN", "NAME"):
        _, person = next((x for x in toks[k].options["PRON"] if x[0] == "direct object"), toks[k].options["PRON"][0])
        cl.receiver = HNounPhrase(text=toks[k].text, kind="pronoun", person=person,
                                  number="pl" if "pl" in person else "sg")
        k += 1
    # direct object: a pronoun or a noun phrase
    if k < len(toks) and has(toks[k], "PRON") and not has(toks[k], "NOUN", "NAME") \
            and any(kind == "direct object" for kind, _ in toks[k].options["PRON"]) and not pac_at(toks, k):
        _, person = next(x for x in toks[k].options["PRON"] if x[0] == "direct object")
        cl.obj = HNounPhrase(text=toks[k].text, kind="pronoun", person=person,
                             number="pl" if "pl" in person else "sg")
        k += 1
    elif verb is not None and verb.yi_da and k < len(toks) and toks[k].lower == "da":
        np, j = parse_np(toks, k + 1)                 # yi amfani da kyandir
        cl.obj, k = np, j
    elif verb is not None and verb.english in HW.MOTION_VERBS:
        pass                                                 # za mu tafi kasuwa: a place, not an object
    elif k < len(toks) and has(toks[k], "NOUN", "NAME", "DEM", "INDEF", "QUANT", "ADJ") and not has(toks[k], "ADV", "PREP"):
        first, j = parse_np(toks, k, receiver=True)
        if first is not None:
            # give + receiver + thing: ya ba Ada littafi
            second, j2 = parse_np(toks, j, receiver=True) if j < len(toks) and \
                has(toks[j], "NOUN", "NAME") and not has(toks[j], "ADV") else (None, j)
            after = toks[j].lower if j < len(toks) else ""
            if verb is not None and verb.hausa == "ba" and after:
                # ba X mamaki -> surprise X (the after_object column of the Verbs tab)
                for r in R["verbs"].get("ba", []):
                    if r.get("after_object") == after and r["form"] == "before_noun":
                        verb.english, verb.hausa = r["english"], r["hausa"]
                        cl.obj = first
                        return j + 1
            if second is not None and cl.receiver is None and verb is not None and verb.hausa == "ba":
                cl.receiver, cl.obj, k = first, second, j2
            else:
                cl.obj, k = first, j
    return k


def parse_rest(cl, toks, k):
    """Places, times, manner, 'da' + noun, and the final ba."""
    while k < len(toks):
        t = toks[k]
        if t.lower == "ba" and k == len(toks) - 1:
            cl.negative = True
            k += 1
            continue
        if has(t, "ADV") and not (has(t, "PREP") and k + 1 < len(toks) and has(toks[k + 1], "NOUN", "NAME")):
            cl.adverbs.append(t.options["ADV"])
            k += 1
            continue
        if has(t, "PREP"):
            np, j = parse_np(toks, k + 1)
            if np is not None:
                np.after = t.lower
                cl.places.append((t.options["PREP"], np))
                k = j
                continue
        if t.lower == "da" and k + 1 < len(toks):
            np, j = parse_np(toks, k + 1)
            if np is not None:
                cl.places.append(("with", np))
                k = j
                continue
        if has(t, "NOUN", "NAME") and cl.verb is not None and cl.verb.english in HW.MOTION_VERBS \
                and not cl.places:
            np, j = parse_np(toks, k)
            if np is not None:
                cl.places.append(("to", np))
                k = j
                continue
        if has(t, "NOUN", "NAME") and cl.obj is None and cl.construction in ("verbal", "command"):
            np, j = parse_np(toks, k)
            if np is not None:
                cl.obj = np
                k = j
                continue
        cl.leftovers.append(t.text)
        k += 1
    return cl


# ===== The whole pipeline =====

def analyse(sentence):
    """Analyse one Hausa sentence. Returns an HAnalysis."""
    global SENTENCE_IS_QUESTION
    tokens = recognise(split_words(sentence))
    SENTENCE_IS_QUESTION = any(t.lower == "?" for t in tokens)
    clauses = []
    for role, link, eng, toks in split_clauses(tokens):
        cewa = next((k for k, t in enumerate(toks) if has(t, "CEWA")), None)
        inner_toks = None
        if cewa is not None:
            toks, inner_toks = toks[:cewa], toks[cewa + 1:]
        cl = parse_clause(toks, role=role, linker=link)
        cl.linker_english = eng
        if inner_toks:
            cl.clauses.append(parse_clause(inner_toks, role="complement", linker="cewa"))
        if SENTENCE_IS_QUESTION and cl.mood == "statement" and role == "main":
            cl.mood = "yes-no question"
        clauses.append(cl)
    result = HAnalysis(sentence=sentence, tokens=tokens, clauses=clauses)
    result.problems = check(result)
    return result


def check(analysis):
    problems = []
    unknown = [t.text for t in analysis.tokens if "UNKNOWN" in t.options]
    if unknown:
        problems.append("word(s) not recognised: " + ", ".join(unknown))

    def walk(cl, n):
        if cl.leftovers:
            problems.append(f"clause {n}: words not placed: {' '.join(cl.leftovers)}")
        if not cl.construction:
            problems.append(f"clause {n}: construction not found")
        for inner in cl.clauses:
            walk(inner, n)
        for np in (cl.subject, cl.obj):
            if isinstance(np, HNounPhrase) and np.relative_clause is not None:
                walk(np.relative_clause, n)
    for n, cl in enumerate(analysis.clauses, 1):
        walk(cl, n)
    return problems


# ===== Showing the result =====

def describe_np(np):
    if np is None:
        return "-"
    if isinstance(np, tuple):
        return f"{np[0]} + {describe_np(np[1])}"
    if isinstance(np, str):
        return np
    if np.kind == "coordinated":
        return " and ".join(describe_np(p) for p in np.coordinated)
    bits = [np.kind]
    if np.english:
        bits.append(f"English: {np.english}")
    if np.kind not in ("wh",):
        bits.append(np.person)
    if np.definite:
        bits.append("the")
    if np.demonstrative:
        bits.append(np.demonstrative)
    if np.which:
        bits.append("which")
    if isinstance(np.possessor, str):
        bits.append(f"owner: {np.possessor}")
    elif np.possessor is not None:
        bits.append(f"owner: {np.possessor.text}")
    if np.adjectives:
        bits.append("adjective: " + ", ".join(np.adjectives))
    if np.quantifier:
        bits.append(np.quantifier)
    if np.count:
        bits.append(f"number: {np.count}")
    if np.negative:
        bits.append("negative")
    if np.from_pac:
        bits.append("shown only by the PAC")
    out = f"{np.text or '(none)'}  [{' | '.join(bits)}]"
    if np.relative_clause is not None:
        out += "\n" + describe_clause(np.relative_clause, indent=8, title="relative clause")
    return out


def describe_clause(cl, indent=2, title=None):
    pad = " " * indent
    head = title or f"{cl.role} clause"
    if cl.linker:
        head += f" (linker: {cl.linker}{' = ' + cl.linker_english if cl.linker_english else ''})"
    lines = [f"{pad}{head} - {cl.mood} - {cl.construction or '?'}"]
    if cl.focus is not None:
        lines.append(f"{pad}  focus:        {describe_np(cl.focus)}")
    if cl.wh_word:
        lines.append(f"{pad}  question:     {cl.wh_word} (asks about the {cl.wh_role})")
    if cl.gap:
        lines.append(f"{pad}  gap:          {cl.gap}")
    lines.append(f"{pad}  subject:      {describe_np(cl.subject)}")
    if cl.pac is not None:
        lines.append(f"{pad}  PAC:          {cl.pac.text}  [{cl.pac.person} | {cl.pac.column}]")
    if cl.verb is not None:
        v = cl.verb
        bits = [f"Hausa: {v.hausa}", f"English: {v.english}", f"form: {v.form}"]
        if v.ability:
            bits.append("can (iya)")
        if v.ever:
            bits.append("ever (taɓa)")
        if v.infinitive:
            bits.append(f"+ to {v.infinitive[1].english}")
        lines.append(f"{pad}  verb:         {v.text}  [{' | '.join(bits)}]")
    if cl.receiver is not None:
        lines.append(f"{pad}  receiver:     {describe_np(cl.receiver)}")
    if cl.obj is not None:
        lines.append(f"{pad}  object:       {describe_np(cl.obj)}")
    if cl.complement is not None:
        kind, value = cl.complement
        lines.append(f"{pad}  complement:   ({kind}) {describe_np(value) if not isinstance(value, str) else value}")
    for prep, np in cl.places:
        lines.append(f"{pad}  {prep + ' + ...:':<14}{describe_np(np)}")
    if cl.adverbs:
        lines.append(f"{pad}  adverbs:      {', '.join(cl.adverbs)}")
    if cl.negative:
        lines.append(f"{pad}  negative:     yes")
    if cl.please:
        lines.append(f"{pad}  please:       yes")
    for inner in cl.clauses:
        lines.append(describe_clause(inner, indent + 4, title="reported clause"))
    return "\n".join(lines)


def describe(analysis):
    def tag_of(t):
        o = [k for k in t.options if k not in ("PUNCT", "COMMA")]
        return "/".join(o[:3]) if o else ""
    lines = [f"Sentence: {analysis.sentence}",
             "Words:    " + "  ".join(f"{t.text}<{tag_of(t)}>" for t in analysis.tokens if tag_of(t))]
    for n, cl in enumerate(analysis.clauses, 1):
        lines.append(describe_clause(cl, title=f"Clause {n}: {cl.role}"))
    if analysis.problems:
        lines.append("  PROBLEMS: " + "; ".join(analysis.problems))
    return "\n".join(lines)

