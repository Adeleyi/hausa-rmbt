"""English analysis: stage 1 of the transfer system.

What it does, in order:
  1. clean_up      - expand contractions (didn't -> did not), split punctuation
  2. tag_words     - give every word a word class (noun, verb, ...) and base form
  3. split_clauses - cut the sentence into clauses (main, because-clause, ...)
  4. parse_clause  - inside each clause, find subject, verb group, object, etc.

The result is an Analysis object. The transfer rules (stage 2) read it.

Everything here is a hand-written rule. There is no statistics and no
machine learning: if the analysis is wrong, a rule or a word list is wrong,
and you can fix it.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

import english_words as W

ROOT = Path(__file__).resolve().parent.parent
LEXICON_FILE = ROOT / "data" / "lexicon" / "Hausa_RBMT_Lexicon_v2.xlsx"


# ===========================================================================
# Data structures: how an analysed sentence is stored
# ===========================================================================

@dataclass
class Token:
    text: str                 # the word as written
    lower: str                # lower-case form
    tag: str = ""             # word class, e.g. NOUN, VERB, DET
    lemma: str = ""           # base form, e.g. "go" for "went"
    form: str = ""            # verb form: base, past, participle, ing, 3sg; noun: sg/pl
    options: dict = field(default_factory=dict)   # possible tags before context decides


@dataclass
class NounPhrase:
    text: str                 # the words of the phrase
    head: str                 # base form of the main word, e.g. "girl"
    kind: str                 # noun, name, pronoun, indefinite, demonstrative, wh
    person: str = "3"
    number: str = "sg"        # sg or pl
    sex: str = ""             # m, f or "" (unknown) - for PAC agreement
    definite: str = ""        # definite, indefinite, near (this), far (that)
    possessor: object = None  # another NounPhrase, or a pronoun description
    adjectives: list = field(default_factory=list)
    modifiers: list = field(default_factory=list)   # nouns in front of the head: "house" in "house door"
    count: str = ""           # number word: "two"
    quantifier: str = ""      # many, every, some ...
    coordinated: list = field(default_factory=list)  # parts of "Musa and Aisha"
    relative_clause: object = None                   # a Clause
    negative: bool = False    # nobody, nothing


@dataclass
class VerbGroup:
    text: str
    lemma: str                # base form of the main verb ("be" for copula)
    tense: str = "present"    # past, present, future
    aspect: str = "simple"    # simple, progressive, perfect
    negative: bool = False
    never: bool = False
    modal: str = ""           # ability, possibility, obligation, conditional
    voice: str = "active"     # active or passive
    copula: bool = False      # True for "be" as the main verb
    possession: bool = False  # True for "have" as the main verb
    particle: str = ""        # "up" in "stand up"
    infinitive: str = ""      # "go" in "wanted to go"


@dataclass
class Clause:
    role: str = "main"        # main, coordinated, subordinate, relative, complement
    linker: str = ""          # and, but, because, if, that, who ...
    linker_type: str = ""     # reason, condition, time ...
    mood: str = "statement"   # statement, yes-no question, wh-question, command
    subject: object = None
    verb: object = None
    obj: object = None                 # direct object
    indirect_obj: object = None        # receiver: "Ada" in "gave Ada a book"
    complement: object = None          # after "be": a NounPhrase, an adjective or a place
    prep_phrases: list = field(default_factory=list)   # (preposition, NounPhrase)
    adverbs: list = field(default_factory=list)
    wh_word: str = ""
    wh_role: str = ""         # subject, object, place, time, reason, manner
    gap: str = ""             # in a relative clause: which role "who/that" fills
    focus: object = None      # "Ada" in "It was Ada who ..."
    existential: bool = False # "There is ..."
    agent: object = None      # "Ngozi" in "... was prepared by Ngozi"
    clauses: list = field(default_factory=list)  # clauses inside this one (complement)


@dataclass
class Analysis:
    sentence: str
    tokens: list
    clauses: list
    problems: list = field(default_factory=list)


# ===========================================================================
# Word classes from the lexicon workbook (loaded once)
# ===========================================================================

_WORDS = None


def word_classes():
    """Return sets of English nouns, verbs and adjectives, plus names.

    They come from the 'keys' column of the lexicon tabs, plus the extra
    lists in english_words.py.
    """
    global _WORDS
    if _WORDS is not None:
        return _WORDS
    nouns, verbs, adjs = set(W.EXTRA_NOUNS), set(W.EXTRA_VERBS), set(W.EXTRA_ADJECTIVES)
    names = dict(W.NAMES)
    try:
        import pandas as pd
        tabs = pd.read_excel(LEXICON_FILE, sheet_name=["Nouns", "Verbs", "Adjectives", "Names"], dtype=str)
        for tab, target in (("Nouns", nouns), ("Verbs", verbs), ("Adjectives", adjs)):
            for keys in tabs[tab]["keys"].dropna():
                for k in keys.split(";"):
                    k = k.strip().lower()
                    if k and " " not in k and k.isalpha():
                        target.add(k)
        for _, row in tabs["Names"].iterrows():
            if isinstance(row["name"], str) and row.get("gender") in ("m", "f"):
                names.setdefault(row["name"].lower(), row["gender"])
    except Exception as err:  # the analysis still works with the built-in lists
        print(f"Warning: could not read the lexicon ({err}). Using built-in word lists only.")
    # grammar words must never be treated as nouns or verbs
    grammar = (set(W.PRONOUNS) | set(W.POSSESSIVES) | set(W.ARTICLES) | set(W.DEMONSTRATIVES)
               | set(W.WH_WORDS) | set(W.BE_FORMS) | set(W.HAVE_FORMS) | set(W.DO_FORMS)
               | set(W.MODALS) | W.NEGATIVES | set(W.NUMBERS) | W.QUANTIFIERS | set(W.INDEFINITES)
               | {"and", "or", "but", "if", "because", "although", "unless", "while"})
    for s in (nouns, verbs, adjs):
        s -= grammar
    _WORDS = {"nouns": nouns, "verbs": verbs, "adjs": adjs, "names": names}
    return _WORDS


# ===========================================================================
# Step 1: clean-up and splitting into words
# ===========================================================================

CONTRACTIONS = [
    (r"\bcan't\b", "can not"), (r"\bcannot\b", "can not"), (r"\bwon't\b", "will not"),
    (r"\bshan't\b", "shall not"), (r"n't\b", " not"), (r"'m\b", " am"), (r"'re\b", " are"),
    (r"'ve\b", " have"), (r"'ll\b", " will"), (r"'d\b", " would"),
    (r"\b(it|he|she|that|what|who|there|where)'s\b", r"\1 is"),
]


def clean_up(sentence):
    """Straighten quotes and expand contractions."""
    s = sentence.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    for pattern, replacement in CONTRACTIONS:
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)
    return s


def split_words(sentence):
    """Split a sentence into words and punctuation. "Musa's" -> "Musa", "'s"."""
    raw = re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)*|'s|[0-9]+|[.,!?;:]", sentence)
    tokens = [Token(text=w, lower=w.lower()) for w in raw]
    return merge_multiword(tokens)


def merge_multiword(tokens):
    """Join fixed expressions such as "every day" into one token."""
    out, i = [], 0
    while i < len(tokens):
        if i + 1 < len(tokens):
            pair = tokens[i].lower + " " + tokens[i + 1].lower
            if pair in W.MULTIWORD or pair in W.INDEFINITES:
                out.append(Token(text=tokens[i].text + " " + tokens[i + 1].text, lower=pair))
                i += 2
                continue
        out.append(tokens[i])
        i += 1
    return out


# ===========================================================================
# Step 2: word classes and base forms
# ===========================================================================

def undouble(stem):
    """stopp -> stop, runn -> run"""
    if len(stem) > 2 and stem[-1] == stem[-2] and stem[-1] not in "aeiouls":
        return stem[:-1]
    return stem


def verb_base(word):
    """Return (base form, verb form) if the word is a known verb, else None."""
    verbs = word_classes()["verbs"]
    for base, (past, part) in W.IRREGULAR_VERBS.items():
        if word == past and word == part:
            return base, "past/participle"
        if word == past:
            return base, "past"
        if word == part:
            return base, "participle"
    candidates = []
    if word.endswith("ing"):
        stem = word[:-3]
        candidates += [(stem, "ing"), (stem + "e", "ing"), (undouble(stem), "ing")]
    if word.endswith("ied"):
        candidates.append((word[:-3] + "y", "past/participle"))
    if word.endswith("ed"):
        stem = word[:-2]
        candidates += [(stem, "past/participle"), (word[:-1], "past/participle"), (undouble(stem), "past/participle")]
    if word.endswith("ies"):
        candidates.append((word[:-3] + "y", "3sg"))
    if word.endswith("es"):
        candidates.append((word[:-2], "3sg"))
    if word.endswith("s") and not word.endswith("ss"):
        candidates.append((word[:-1], "3sg"))
    candidates.append((word, "base"))
    for base, form in candidates:
        if base in verbs or base in W.IRREGULAR_VERBS:
            return base, form
    return None


def noun_base(word):
    """Return (singular form, 'sg' or 'pl') if the word is a known noun, else None."""
    nouns = word_classes()["nouns"]
    if word in W.IRREGULAR_PLURALS:
        return W.IRREGULAR_PLURALS[word], "pl"
    candidates = []
    if word.endswith("ies"):
        candidates.append((word[:-3] + "y", "pl"))
    if word.endswith("es"):
        candidates.append((word[:-2], "pl"))
    if word.endswith("s") and not word.endswith("ss"):
        candidates.append((word[:-1], "pl"))
    candidates.append((word, "sg"))          # plural readings are tried first: parents -> parent
    for base, number in candidates:
        if base in nouns:
            if base in W.UNCOUNTABLE:
                number = "sg"
            return base, number
    return None


def possible_tags(tok, position, tokens):
    """List every word class this word could have, before looking at context."""
    w = tok.lower
    opts = {}
    if w in ".,!?;:":
        return {"PUNCT": w}
    if w == "'s":
        return {"POSS_S": "'s"}
    if w in W.MULTIWORD:
        return {W.MULTIWORD[w]: w}
    if w in W.INDEFINITES:
        return {"INDEF": w}
    if w in W.ARTICLES:
        opts["DET"] = w
    if w in W.DEMONSTRATIVES:
        opts["DEM"] = w
    if w in W.POSSESSIVES:
        opts["POSS"] = w
    if w in W.PRONOUNS:
        opts["PRON"] = w
    if w in W.NUMBERS:
        opts["NUM"] = w
    if w in W.QUANTIFIERS:
        opts["QUANT"] = w
    if w in W.BE_FORMS:
        opts["BE"] = "be"
    if w in W.HAVE_FORMS:
        opts["HAVE"] = "have"
    if w in W.DO_FORMS:
        opts["DO"] = "do"
    if w in W.MODALS:
        opts["MODAL"] = w
    if w in W.NEGATIVES:
        opts["NEG"] = w
    if w == "to":
        opts["TO"] = "to"
    if w == "there":
        opts["THERE"] = "there"
    if w in W.WH_WORDS:
        opts["WH"] = w
    if w in W.COORDINATORS:
        opts["COORD"] = w
    if w in W.SUBORDINATORS:
        opts["SUB"] = w
    if w in W.PREPOSITIONS:
        opts["PREP"] = w
    if w in W.PARTICLES:
        opts["PART"] = w
    if w in W.ADVERBS or (w.endswith("ly") and w not in word_classes()["adjs"] and len(w) > 4):
        opts["ADV"] = w
    words = word_classes()
    if w in words["names"] or w in W.PLACE_NAMES:
        opts["NAME"] = w
    elif tok.text[0].isupper() and position > 0 and not opts:
        opts["NAME"] = w            # unknown capitalised word in mid-sentence: a name
    if opts and not any(k in opts for k in ("ADV", "PART", "PREP")):
        return opts                 # grammar words are not also nouns/verbs
    v = verb_base(w)
    if v:
        opts["VERB"] = v
    n = noun_base(w)
    if n:
        opts["NOUN"] = n
    if w in words["adjs"]:
        opts["ADJ"] = w
    if not opts:                    # unknown word: guess from its ending
        if w.endswith("ing") or w.endswith("ed"):
            opts["VERB"] = (w, "past/participle" if w.endswith("ed") else "ing")
        else:
            opts["NOUN"] = (w[:-1], "pl") if w.endswith("s") else (w, "sg")
    return opts


VERB_GROUP_TAGS = {"VERB", "BE", "HAVE", "DO", "MODAL"}
NP_START_TAGS = {"DET", "DEM", "POSS", "NUM", "QUANT", "ADJ", "NOUN", "NAME", "PRON", "INDEF"}


def tag_words(tokens):
    """Choose one word class per word, using the words around it (left to right)."""
    for i, tok in enumerate(tokens):
        tok.options = possible_tags(tok, i, tokens)
    verb_seen = False                       # has this clause had a verb yet?
    rel_state = 0                           # 1 = inside a relative clause, 2 = its verb has been seen
    for i, tok in enumerate(tokens):
        opts = tok.options
        prev = tokens[i - 1] if i > 0 else None
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        p = prev.tag if prev else "START"
        nxt_opts = nxt.options if nxt else {}
        tag = None

        if len(opts) == 1 and not set(opts) & {"WH", "DEM", "TO", "THERE", "PREP", "PART", "SUB"}:
            tag = next(iter(opts))
        # --- "her": possessive before a noun, otherwise object pronoun
        elif tok.lower == "her":
            # "her mother" (possessive) or "carried her" (object pronoun)
            nxt_set = set(nxt_opts)
            if nxt and nxt_set & {"NOUN", "ADJ"} and not nxt_set & {"DET", "NAME", "PRON", "PUNCT", "PREP"}:
                tag = "POSS"
            else:
                tag = "PRON"
        # --- "that / this / these / those"
        elif "DEM" in opts:
            verb_follows = any("VERB" in t.options or set(t.options) & {"BE", "HAVE", "MODAL"}
                               for t in tokens[i + 1:])
            if tok.lower == "that" and p in ("NOUN", "NAME", "PRON", "INDEF", "ADV") and i > 1:
                tag = "REL"                      # "the book that I borrowed"
            elif tok.lower == "that" and p == "VERB" and verb_follows:
                tag = "COMP"                     # "I know that she left"
            elif nxt and set(nxt_opts) & {"NOUN", "ADJ"}:
                tag = "DEM"                      # "this house"
            else:
                tag = "DEM_PRON"                 # "Do not touch that."
        # --- who / which / when ...: question word, relative word or "when" clause
        elif "WH" in opts:
            if i == 0 and tok.lower == "when" and tokens[-1].lower != "?":
                tag = "SUB"
            elif i == 0:
                tag = "WH"
            elif tok.lower in W.RELATIVE_WORDS and p in ("NOUN", "NAME", "PRON", "ADV", "INDEF"):
                tag = "REL"
            elif "SUB" in opts:
                tag = "SUB"
            elif p in ("COMMA", "PUNCT"):
                tag = "SUB" if "SUB" in opts else "WH"
            else:
                tag = "WH"
        # --- "to": infinitive before a verb, preposition otherwise
        elif "TO" in opts or tok.lower == "to":
            tag = "TO_INF" if nxt and "VERB" in nxt_opts and not set(nxt_opts) & {"DET", "NAME", "PRON"} \
                and nxt_opts["VERB"][1] == "base" and "NOUN" not in nxt_opts else "PREP"
            if nxt and "VERB" in nxt_opts and "NOUN" in nxt_opts and p == "VERB":
                tag = "TO_INF"
        # --- "there is / there are"
        elif "THERE" in opts:
            tag = "THERE" if nxt and set(nxt_opts) & {"BE", "HAVE"} else "ADV"
        # --- inside / outside / before / after: preposition or adverb / subordinator
        elif "PREP" in opts and ("ADV" in opts or "SUB" in opts or "PART" in opts):
            if "PART" in opts and p == "VERB" and (prev.lemma + " " + tok.lower) in W.PHRASAL_VERBS:
                tag = "PART"
            elif "SUB" in opts and (i == 0 or p == "PUNCT"):
                tag = "SUB"
            elif nxt and set(nxt_opts) & {"DET", "POSS", "NOUN", "NAME", "NUM", "PRON", "DEM"}:
                tag = "PREP"
            else:
                tag = "ADV" if "ADV" in opts else "PART"
        elif "PART" in opts and p == "VERB" and (prev.lemma + " " + tok.lower) in W.PHRASAL_VERBS:
            tag = "PART"
        # --- SUB that is also a preposition handled above; plain SUB/COORD
        elif "SUB" in opts:
            tag = "SUB"
        elif "COORD" in opts:
            tag = "COORD"
        elif "ADV" in opts and not set(opts) & {"VERB", "NOUN"}:
            tag = "ADV"
        # --- content words: noun, verb or adjective?
        else:
            has_v, has_n, has_a = "VERB" in opts, "NOUN" in opts, "ADJ" in opts
            vform = opts["VERB"][1] if has_v else ""
            if has_a and p in ("BE", "ADV") and not (vform in ("ing", "past/participle", "participle")
                                                      and tok.lower not in word_classes()["adjs"]):
                tag = "ADJ"                       # "is happy", "is missing"
            elif has_a and nxt and "NOUN" in nxt_opts and "VERB" not in nxt_opts and p != "BE":
                tag = "ADJ"                       # "red bag", "good seats"
            elif has_a and not has_n and not has_v:
                tag = "ADJ"
            elif has_v and rel_state == 2 and p not in ("DET", "POSS", "DEM", "ADJ", "PREP", "NUM"):
                tag = "VERB"                      # main verb after a relative clause: "whom we visited lives"
            elif has_v and p in ("PRON", "MODAL", "TO_INF", "DO", "NEG", "INDEF", "HAVE", "REL", "FUTURE"):
                tag = "VERB"
            elif has_v and p == "BE" and vform in ("ing", "past/participle", "participle", "past"):
                tag = "VERB"                      # "is crying", "was stolen"
            elif has_n and p in ("DET", "POSS", "DEM", "NUM", "QUANT", "ADJ", "PREP", "POSS_S"):
                tag = "NOUN"
            elif has_v and p in ("NOUN", "NAME", "ADV") and not verb_seen:
                tag = "VERB"                      # "Birds fly", "The man ... lives"
            elif has_v and p in ("NOUN", "NAME") and vform in ("past/participle", "past", "3sg", "participle"):
                tag = "VERB"                      # "the man who called yesterday ... "
            elif has_v and p == "START":
                tag = "VERB"                      # command: "Sit down."
            elif has_v and p in ("COORD", "PUNCT") and not has_n:
                tag = "VERB"
            elif has_n:
                tag = "NOUN"
            elif has_v:
                tag = "VERB"
            elif has_a:
                tag = "ADJ"
            else:
                tag = next(iter(opts))

        # --- "have/do" as helper verbs or main verbs is decided in the verb group parser
        tok.tag = tag
        val = opts.get(tag)
        if tag == "VERB":
            tok.lemma, tok.form = val
        elif tag == "NOUN":
            tok.lemma, tok.form = val
        elif tag in ("REL", "COMP", "DEM_PRON"):
            tok.lemma = tok.lower
        else:
            tok.lemma = val if isinstance(val, str) else tok.lower
        if tag == "PUNCT" and tok.lower == ",":
            tok.tag = "COMMA"
        if tag in VERB_GROUP_TAGS:
            if rel_state == 1:
                rel_state = 2                     # the relative clause now has its verb
            elif rel_state == 2 and prev and prev.tag not in VERB_GROUP_TAGS:
                rel_state = 0                     # a new verb group: the main clause has resumed
            verb_seen = True
        if tag in ("COMMA", "COORD", "SUB", "REL", "COMP"):
            verb_seen = False
        if tag == "REL":
            rel_state = 1
    # "going to" + verb = future
    for i, tok in enumerate(tokens):
        if tok.lower == "going to":
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            if nxt and nxt.tag == "VERB":
                tok.tag = "FUTURE"
            else:                       # "going to the market"
                tok.tag, tok.lemma, tok.form = "VERB", "go", "ing"
    return tokens


# ===========================================================================
# Step 3: cutting the sentence into clauses
# ===========================================================================

def has_verb(tokens):
    return any(t.tag in VERB_GROUP_TAGS for t in tokens)


def split_clauses(tokens):
    """Return a list of (role, linker word, linker type, tokens) - one per clause."""
    body = [t for t in tokens if t.tag != "PUNCT"]
    # cut at commas first
    chunks, current = [], []
    for t in body:
        if t.tag == "COMMA":
            if current:
                chunks.append(current)
            current = []
        else:
            current.append(t)
    if current:
        chunks.append(current)
    # a chunk without a verb belongs to the chunk before it (e.g. a list of nouns)
    merged = []
    for c in chunks:
        if merged and not has_verb(c) and c[0].tag not in ("SUB", "COORD"):
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)

    clauses = []
    for chunk in merged:
        for piece in split_inside(chunk):
            clauses.append(piece)
    # a subordinate clause that comes first is attached to the next main clause;
    # we keep the order and mark roles so the transfer stage can rebuild it.
    return clauses


def split_inside(chunk):
    """Split one comma-free chunk at coordinators and subordinators."""
    role, linker, ltype = "main", "", ""
    if chunk and chunk[0].tag == "SUB":
        role, linker, ltype = "subordinate", chunk[0].lower, W.SUBORDINATORS[chunk[0].lower]
        chunk = chunk[1:]
    elif chunk and chunk[0].tag == "COORD":
        role, linker = "coordinated", chunk[0].lower
        chunk = chunk[1:]
    pieces = []
    start = 0
    for i, t in enumerate(chunk):
        if i <= start:
            continue
        left, right = chunk[start:i], chunk[i + 1:]
        if t.tag == "SUB" and has_verb(right) and has_verb(left):
            pieces.append((role, linker, ltype, left))
            role, linker, ltype = "subordinate", t.lower, W.SUBORDINATORS[t.lower]
            start = i + 1
        elif t.tag == "COORD" and has_verb(left) and starts_new_clause(right):
            pieces.append((role, linker, ltype, left))
            role, linker, ltype = "coordinated", t.lower, ""
            start = i + 1
    pieces.append((role, linker, ltype, chunk[start:]))
    return pieces


def starts_new_clause(tokens):
    """After 'and/but', does a new subject + verb follow (a new clause)?"""
    if not tokens:
        return False
    if tokens[0].tag in VERB_GROUP_TAGS:
        return False                     # "... and carried her inside": shared subject
    for t in tokens:
        if t.tag in VERB_GROUP_TAGS:
            return True
        if t.tag not in NP_START_TAGS and t.tag not in ("POSS_S", "ADV"):
            return False
    return False


# ===========================================================================
# Step 4: inside one clause
# ===========================================================================

def parse_np(tokens, i):
    """Read a noun phrase starting at position i. Returns (NounPhrase, next i) or (None, i)."""
    if i >= len(tokens):
        return None, i
    start = i
    t = tokens[i]

    # pronouns, names, indefinites, "this/that" used alone
    if t.tag == "PRON":
        person, number, sex, _ = W.PRONOUNS[t.lower]
        np = NounPhrase(text=t.text, head=t.lower, kind="pronoun", person=person, number=number, sex=sex)
        return attach_extras(np, tokens, i + 1, start)
    if t.tag == "INDEF":
        person, number, neg = W.INDEFINITES[t.lower]
        np = NounPhrase(text=t.text, head=t.lower, kind="indefinite", person=person, number=number, negative=neg)
        return attach_extras(np, tokens, i + 1, start)
    if t.tag == "DEM_PRON":
        dist, number = W.DEMONSTRATIVES[t.lower]
        np = NounPhrase(text=t.text, head=t.lower, kind="demonstrative", number=number, definite=dist)
        return np, i + 1
    if t.tag == "QUANT" and (i + 1 >= len(tokens) or tokens[i + 1].tag not in ("NOUN", "ADJ")):
        np = NounPhrase(text=t.text, head=t.lower, kind="quantity", quantifier=t.lower)
        return np, i + 1
    if t.tag == "NAME":
        words = word_classes()["names"]
        np = NounPhrase(text=t.text, head=t.text, kind="name", sex=words.get(t.lower, ""))
        return attach_extras(np, tokens, i + 1, start)

    np = NounPhrase(text="", head="", kind="noun")
    # determiner slot
    if t.tag == "DET":
        np.definite = W.ARTICLES[t.lower]
        i += 1
    elif t.tag == "DEM":
        np.definite, np.number = W.DEMONSTRATIVES[t.lower]
        i += 1
    elif t.tag == "POSS":
        person, number, sex = W.POSSESSIVES[t.lower]
        np.possessor = NounPhrase(text=t.text, head=t.lower, kind="pronoun", person=person, number=number, sex=sex)
        np.definite = "definite"
        i += 1
    while i < len(tokens) and tokens[i].tag in ("NUM", "QUANT"):
        if tokens[i].tag == "NUM":
            np.count = tokens[i].lower
        else:
            np.quantifier = tokens[i].lower
        i += 1
    while i < len(tokens) and tokens[i].tag == "ADJ":
        np.adjectives.append(tokens[i].lower)
        i += 1
    nouns = []
    while i < len(tokens) and tokens[i].tag == "NOUN":
        nouns.append(tokens[i])
        i += 1
    if not nouns:
        if np.adjectives and i > start:      # "the red" with no noun: treat adjective as head
            np.head = np.adjectives.pop()
        else:
            return None, start
    else:
        head = nouns[-1]
        np.head = head.lemma
        np.modifiers = [n.lemma for n in nouns[:-1]]
        if head.form == "pl":
            np.number = "pl"
    if np.count and np.count != "one":
        np.number = "pl"
    np.sex = "f" if np.head in W.FEMALE_NOUNS else "m" if np.head in W.MALE_NOUNS else ""
    return attach_extras(np, tokens, i, start)


def attach_extras(np, tokens, i, start):
    """After a noun phrase: possessive 's, 'and' + another noun phrase, relative clause."""
    # Musa's house: the phrase so far is the owner of the next noun
    if i < len(tokens) and tokens[i].tag == "POSS_S":
        owner = np
        owner.text = " ".join(t.text for t in tokens[start:i])
        owned, j = parse_np(tokens, i + 1)
        if owned:
            owned.possessor = owner
            owned.definite = "definite"
            return owned, j
    np.text = " ".join(t.text for t in tokens[start:i])
    # Musa and Aisha
    if i < len(tokens) and tokens[i].tag == "COORD" and tokens[i].lower in ("and", "or"):
        other, j = parse_np(tokens, i + 1)
        if other:
            both = NounPhrase(text=np.text + " " + tokens[i].text + " " + other.text, head=np.head,
                              kind="coordinated", person=min(np.person, other.person), number="pl",
                              coordinated=[np, other])
            return both, j
    # the man who called yesterday
    if i < len(tokens) and tokens[i].tag == "REL":
        rel, j = parse_relative(tokens, i)
        np.relative_clause = rel
        np.text = " ".join(t.text for t in tokens[start:j])
        return np, j
    return np, i


def verb_group_end(tokens, i):
    """Find where a verb group starting at i ends (helpers + one main verb)."""
    j = i
    while j < len(tokens) and tokens[j].tag in ("MODAL", "DO", "HAVE", "BE", "NEG", "FUTURE") \
            or (j < len(tokens) and tokens[j].tag == "ADV" and tokens[j].lower in ("already", "always", "never", "also", "often")):
        j += 1
    if j < len(tokens) and tokens[j].tag == "VERB":
        j += 1
        if j < len(tokens) and tokens[j].tag == "PART":
            j += 1
    return j


def parse_relative(tokens, i):
    """Read a relative clause starting with who/which/that/whose at position i."""
    rel_word = tokens[i].lower
    j = i + 1
    verb_done = False
    while j < len(tokens):
        t = tokens[j]
        if t.tag in VERB_GROUP_TAGS or t.tag in ("NEG", "FUTURE"):
            if verb_done:
                break                         # a second verb group: the main clause continues
            j = verb_group_end(tokens, j)
            verb_done = True
            continue
        if t.tag in ("COORD", "SUB", "COMMA"):
            break
        j += 1
    inner = tokens[i + 1:j]
    if rel_word == "whose":
        clause = parse_clause(inner, role="relative", linker="whose")
        clause.gap = "possessor"
    elif inner and inner[0].tag in VERB_GROUP_TAGS:
        clause = parse_clause(inner, role="relative", linker=rel_word, subject_gap=True)
        clause.gap = "subject"
    else:
        clause = parse_clause(inner, role="relative", linker=rel_word)
        clause.gap = "object"
    return clause, j


def parse_verb_group(tokens, i):
    """Read helpers + main verb. Works out tense, aspect, negation, voice."""
    j = verb_group_end(tokens, i)
    words = tokens[i:j]
    vg = VerbGroup(text=" ".join(t.text for t in words), lemma="")
    main = None
    helpers = []
    for t in words:
        if t.tag == "VERB":
            main = t
        elif t.tag == "NEG":
            vg.negative = True
            vg.never = vg.never or t.lower == "never"
        elif t.tag == "ADV" and t.lower == "never":
            vg.negative = vg.never = True
        elif t.tag == "PART":
            vg.particle = t.lower
        elif t.tag in ("MODAL", "DO", "HAVE", "BE", "FUTURE"):
            helpers.append(t)

    first = helpers[0] if helpers else main
    # tense from the first word of the group
    if first is None:
        return None, i
    if any(h.tag == "MODAL" and W.MODALS[h.lower] == "future" for h in helpers) or \
            any(h.tag == "FUTURE" for h in helpers):
        vg.tense = "future"
    elif first.tag == "MODAL":
        vg.tense = "present"
    elif first.tag == "BE":
        vg.tense = "past" if W.BE_FORMS[first.lower][1] == "past" else "present"
    elif first.tag == "HAVE":
        vg.tense = "past" if first.lower == "had" else "present"
    elif first.tag == "DO":
        vg.tense = "past" if first.lower == "did" else "present"
    elif first.tag == "VERB":
        vg.tense = "past" if first.form in ("past", "past/participle") else "present"
    for h in helpers:
        if h.tag == "MODAL" and W.MODALS[h.lower] != "future":
            vg.modal = W.MODALS[h.lower]
        if h.tag == "MODAL" and h.lower == "would":
            vg.modal = "conditional"

    if main is None:
        # no main verb: the last helper is the main verb ("is", "has", "did")
        last = helpers[-1]
        if last.tag == "BE":
            vg.lemma, vg.copula = "be", True
            if any(h.tag == "HAVE" for h in helpers):
                vg.aspect = "perfect"         # "have been"
        elif last.tag == "HAVE":
            vg.lemma, vg.possession = "have", True
        elif last.tag == "DO":
            vg.lemma = "do"
        else:
            vg.lemma = "be"
            vg.copula = True          # "can be ..."
    else:
        vg.lemma = main.lemma + (" " + vg.particle if vg.particle else "")
        before = [h for h in helpers]
        if before and before[-1].tag == "BE" and main.form == "ing":
            vg.aspect = "progressive"
        elif before and before[-1].tag == "BE" and main.form in ("participle", "past/participle"):
            vg.voice = "passive"
        if any(h.tag == "HAVE" for h in before) and main.form in ("participle", "past/participle"):
            vg.aspect = "perfect"
            if before[-1].tag == "BE":
                vg.voice = "passive"
    if vg.lemma == "have" and not vg.copula and main is not None and main.lemma == "have":
        vg.possession = True
    # "wanted to go", "hopes to graduate"
    if j + 1 < len(tokens) and tokens[j].tag == "TO_INF" and tokens[j + 1].tag == "VERB":
        vg.infinitive = tokens[j + 1].lemma
        vg.text += " to " + tokens[j + 1].text
        j += 2
    return vg, j


def parse_clause(tokens, role="main", linker="", ltype="", subject_gap=False):
    """Find the parts of one clause: subject, verb group, objects and the rest."""
    cl = Clause(role=role, linker=linker, linker_type=ltype)
    toks = list(tokens)
    if not toks:
        return cl

    # --- "It was Ada who cooked the soup": focus
    if len(toks) > 3 and toks[0].lower == "it" and toks[1].tag == "BE":
        k = next((n for n in range(2, len(toks)) if toks[n].tag in ("REL", "COMP")
                  or (toks[n].lower == "that" and n > 2)), None)
        if k:
            focus_tokens = toks[2:k]
            focus, _ = parse_np(focus_tokens, 0)
            if focus is None and focus_tokens and focus_tokens[0].tag == "PREP":
                obj, _ = parse_np(focus_tokens, 1)
                focus = (focus_tokens[0].lower, obj)
            if focus is None:
                focus = " ".join(t.text for t in focus_tokens)
            rest = toks[k + 1:]
            gap_subject = bool(rest) and rest[0].tag in VERB_GROUP_TAGS
            inner = parse_clause(rest, role=role, linker=linker, ltype=ltype, subject_gap=gap_subject)
            inner.focus = focus
            inner.gap = "subject" if gap_subject else "object or adverb"
            if gap_subject and isinstance(focus, NounPhrase):
                inner.subject = focus
            return inner

    # --- commands: start with a verb, or "do not" + verb, or "please"
    i = 0
    while i < len(toks) and toks[i].tag == "ADV" and toks[i].lower == "please":
        cl.adverbs.append("please")
        i += 1
    if role == "main" and i < len(toks) and (toks[i].tag == "VERB" and toks[i].form == "base"
                                            or (toks[i].tag == "DO" and i + 2 < len(toks)
                                                and toks[i + 1].tag == "NEG" and toks[i + 2].tag == "VERB")):
        if not subject_gap:
            cl.mood = "command"
            cl.subject = NounPhrase(text="(you)", head="you", kind="pronoun", person="2")

    # --- question words at the start
    if i < len(toks) and toks[i].tag == "WH":
        cl.wh_word = toks[i].lower
        cl.mood = "wh-question"
        if toks[i].lower in ("which", "whose") and i + 1 < len(toks) and toks[i + 1].tag in ("NOUN", "ADJ"):
            wh_np, i2 = parse_np(toks, i + 1)
            wh_np.definite = "which" if toks[i].lower == "which" else "whose"
            wh_phrase = wh_np
            i = i2
        else:
            wh_phrase = NounPhrase(text=toks[i].text, head=toks[i].lower, kind="wh")
            i += 1
        if i < len(toks) and toks[i].tag in VERB_GROUP_TAGS and not (
                i + 1 < len(toks) and toks[i].tag in ("DO", "MODAL", "BE", "HAVE")
                and toks[i + 1].tag in NP_START_TAGS):
            # "Who opened the door?" - the question word is the subject
            cl.wh_role = "subject"
            cl.subject = wh_phrase
        else:
            # "What did Musa buy?" - helper verb comes before the subject: put it back
            toks = toks[:i] + invert(toks[i:])
            cl.wh_role = {"place": "place", "time": "time", "reason": "reason",
                          "manner": "manner"}.get(W.WH_WORDS[cl.wh_word], "object")
            cl.obj = wh_phrase if cl.wh_role == "object" else None
            if cl.wh_role != "object":
                cl.adverbs.append(wh_phrase.text)

    # --- yes/no questions: "Did you finish ...?", "Is Musa a teacher?"
    elif i < len(toks) and toks[i].tag in ("DO", "MODAL", "BE", "HAVE") and role == "main" and cl.mood != "command" \
            and i + 1 < len(toks) and toks[i + 1].tag in NP_START_TAGS:
        cl.mood = "yes-no question"
        toks = toks[:i] + invert(toks[i:])

    # --- "There is a problem"
    if i < len(toks) and toks[i].tag == "THERE":
        cl.existential = True
        vg, j = parse_verb_group(toks, i + 1)
        cl.verb = vg
        subj, j = parse_np(toks, j)
        cl.subject = subj
        return parse_rest(cl, toks, j)

    # --- subject
    if cl.subject is None and not subject_gap:
        while i < len(toks) and toks[i].tag in ("ADV",):
            cl.adverbs.append(toks[i].text)
            i += 1
        subj, i = parse_np(toks, i)
        cl.subject = subj
    while i < len(toks) and toks[i].tag == "ADV" and toks[i].lower not in ("never",):
        cl.adverbs.append(toks[i].text)
        i += 1
    # --- verb group
    if i < len(toks) and (toks[i].tag in VERB_GROUP_TAGS or toks[i].tag in ("NEG", "FUTURE")
                          or toks[i].lower == "never"):
        vg, i = parse_verb_group(toks, i)
        cl.verb = vg
    return parse_rest(cl, toks, i)


def invert(toks):
    """Move a fronted helper verb back after the subject: 'did Musa buy' -> 'Musa did buy'."""
    if not toks or toks[0].tag not in ("DO", "MODAL", "BE", "HAVE"):
        return toks
    helper = toks[0]
    neg = []
    rest = toks[1:]
    if rest and rest[0].tag == "NEG":
        neg, rest = [rest[0]], rest[1:]
    subj, k = parse_np(rest, 0)
    if subj is None:
        return toks
    return rest[:k] + [helper] + neg + rest[k:]


def parse_rest(cl, toks, i):
    """Everything after the verb: objects, complements, places, times."""
    nps = []
    while i < len(toks):
        t = toks[i]
        if t.tag == "PREP" or (t.tag == "TO_INF" and not (i + 1 < len(toks) and toks[i + 1].tag == "VERB")):
            obj, j = parse_np(toks, i + 1)
            if obj is not None:
                if t.lower == "by" and cl.verb and cl.verb.voice == "passive":
                    cl.agent = obj
                else:
                    cl.prep_phrases.append((t.lower, obj))
                i = j
                continue
            cl.adverbs.append(t.text)
            i += 1
            continue
        if t.tag == "ADJ" and not (i + 1 < len(toks) and toks[i + 1].tag == "NOUN"):
            if cl.verb and (cl.verb.copula or cl.verb.lemma in ("become", "remain", "seem", "appear", "look", "feel")):
                cl.complement = ("adjective", t.lower)
            else:
                cl.adverbs.append(t.text)
            i += 1
            continue
        if t.tag == "VERB" and t.form in ("participle", "past/participle") and cl.verb \
                and cl.verb.lemma in ("remain", "become", "seem", "look", "stay", "get"):
            cl.complement = ("adjective", t.text.lower())     # "remained flooded"
            i += 1
            continue
        if t.tag in ("ADV", "PART"):
            cl.adverbs.append(t.text)
            i += 1
            continue
        if t.tag == "COMP":
            inner = parse_clause(toks[i + 1:], role="complement", linker="that")
            cl.clauses.append(inner)
            break
        if t.tag in ("VERB",) and cl.verb and t.form == "base" and cl.verb.lemma in W.SAY_THINK_VERBS:
            inner = parse_clause(toks[i:], role="complement", linker="")
            cl.clauses.append(inner)
            break
        if t.tag in NP_START_TAGS or t.tag in ("DEM_PRON",):
            if cl.verb is None or (cl.verb.lemma in W.SAY_THINK_VERBS and has_verb(toks[i + 1:])
                                   and not cl.obj):
                # "The teacher said the exam was difficult": a clause without "that"
                if cl.verb is not None:
                    inner = parse_clause(toks[i:], role="complement", linker="")
                    cl.clauses.append(inner)
                    break
            np, j = parse_np(toks, i)
            if np is None:
                cl.adverbs.append(t.text)
                i += 1
                continue
            nps.append(np)
            i = j
            continue
        cl.adverbs.append(t.text)
        i += 1

    # roles for the noun phrases after the verb
    if cl.verb and cl.verb.copula and nps and cl.complement is None:
        cl.complement = ("noun", nps.pop(0))
    if cl.verb and cl.verb.copula and cl.complement is None and cl.prep_phrases:
        cl.complement = ("place", cl.prep_phrases.pop(0))
    if len(nps) >= 2 and cl.obj is None:
        cl.indirect_obj, cl.obj = nps[0], nps[1]
    elif nps and cl.obj is None:
        cl.obj = nps[0]
    elif nps and cl.obj is not None:          # "What did Musa give Ada?"
        cl.indirect_obj = nps[0]
    # "gave a book to Musa", "fetched water for the children": receiver / beneficiary
    if cl.indirect_obj is None:
        for prep, np in list(cl.prep_phrases):
            if (prep == "to" and cl.verb and cl.verb.lemma in ("give", "send", "tell", "show", "bring", "lend", "sell")) \
                    or (prep == "for" and cl.verb and cl.verb.lemma in ("buy", "cook", "fetch", "make", "write", "open", "do", "bake")):
                cl.indirect_obj = np
                cl.prep_phrases.remove((prep, np))
                break
    return cl


# ===========================================================================
# The whole pipeline
# ===========================================================================

def analyse(sentence):
    """Analyse one English sentence. Returns an Analysis."""
    tokens = tag_words(split_words(clean_up(sentence)))
    is_question = any(t.lower == "?" for t in tokens)
    pieces = split_clauses(tokens)
    clauses = []
    for role, linker, ltype, toks in pieces:
        cl = parse_clause(toks, role=role, linker=linker, ltype=ltype)
        if is_question and cl.mood == "statement" and role == "main":
            cl.mood = "yes-no question"
        clauses.append(cl)
    result = Analysis(sentence=sentence, tokens=tokens, clauses=clauses)
    result.problems = check(result)
    return result


def check(analysis):
    """List anything that looks incomplete, so it can go in the errors log."""
    problems = []
    for n, cl in enumerate(analysis.clauses, 1):
        if cl.verb is None:
            problems.append(f"clause {n}: no verb found")
        if cl.subject is None and cl.role not in ("relative",) and cl.mood != "command" and not cl.gap:
            problems.append(f"clause {n}: no subject found")
    unknown = [t.text for t in analysis.tokens if t.tag == "NOUN" and t.lemma not in word_classes()["nouns"]]
    if unknown:
        problems.append("word(s) not in the lexicon: " + ", ".join(unknown))
    return problems


# ===========================================================================
# Showing the result in a readable way
# ===========================================================================

def describe_np(np):
    if np is None:
        return "-"
    if isinstance(np, tuple):                    # (preposition, NounPhrase)
        return f"{np[0]} + {describe_np(np[1])}"
    if isinstance(np, str):
        return np
    bits = [np.kind, f"base: {np.head}"]
    if np.kind not in ("wh", "quantity"):
        bits.append(f"{np.person}rd" if np.person == "3" else f"{np.person}{'st' if np.person == '1' else 'nd'}")
        bits.append("plural" if np.number == "pl" else "singular")
    if np.sex:
        bits.append("female" if np.sex == "f" else "male")
    if np.definite:
        bits.append(np.definite)
    if np.possessor is not None:
        bits.append(f"owner: {np.possessor.text}")
    if np.adjectives:
        bits.append("adjective: " + ", ".join(np.adjectives))
    if np.modifiers:
        bits.append("noun modifier: " + ", ".join(np.modifiers))
    if np.count:
        bits.append(f"number: {np.count}")
    if np.quantifier:
        bits.append(f"quantifier: {np.quantifier}")
    if np.negative:
        bits.append("negative")
    out = f"{np.text}  [{' | '.join(bits)}]"
    if np.relative_clause is not None:
        out += "\n" + describe_clause(np.relative_clause, indent=6, title="relative clause")
    return out


def describe_vg(vg):
    if vg is None:
        return "-"
    bits = [f"base: {vg.lemma}", vg.tense, vg.aspect]
    if vg.negative:
        bits.append("negative" + (" (never)" if vg.never else ""))
    if vg.modal:
        bits.append(f"modal: {vg.modal}")
    if vg.voice == "passive":
        bits.append("passive")
    if vg.copula:
        bits.append("copula 'be'")
    if vg.possession:
        bits.append("possession 'have'")
    if vg.infinitive:
        bits.append(f"+ to {vg.infinitive}")
    return f"{vg.text}  [{' | '.join(bits)}]"


def describe_clause(cl, indent=2, title=None):
    pad = " " * indent
    head = title or f"{cl.role} clause"
    if cl.linker:
        head += f" (linker: {cl.linker}{', ' + cl.linker_type if cl.linker_type else ''})"
    lines = [f"{pad}{head} - {cl.mood}"]
    if cl.focus is not None:
        lines.append(f"{pad}  focus:        {describe_np(cl.focus)}")
    if cl.wh_word:
        lines.append(f"{pad}  question:     {cl.wh_word} (asks about the {cl.wh_role})")
    if cl.gap:
        lines.append(f"{pad}  gap:          the {cl.gap} is the noun this clause describes")
    if cl.existential:
        lines.append(f"{pad}  existential:  there is / there are")
    lines.append(f"{pad}  subject:      {describe_np(cl.subject)}")
    lines.append(f"{pad}  verb:         {describe_vg(cl.verb)}")
    if cl.indirect_obj is not None:
        lines.append(f"{pad}  receiver:     {describe_np(cl.indirect_obj)}")
    if cl.obj is not None:
        lines.append(f"{pad}  object:       {describe_np(cl.obj)}")
    if cl.complement is not None:
        kind, value = cl.complement
        lines.append(f"{pad}  complement:   ({kind}) {describe_np(value) if not isinstance(value, str) else value}")
    if cl.agent is not None:
        lines.append(f"{pad}  doer (by):    {describe_np(cl.agent)}")
    for prep, np in cl.prep_phrases:
        lines.append(f"{pad}  {prep + ' + ...:':<14}{describe_np(np)}")
    if cl.adverbs:
        lines.append(f"{pad}  adverbs:      {', '.join(cl.adverbs)}")
    for inner in cl.clauses:
        lines.append(describe_clause(inner, indent + 4, title="complement clause"))
    return "\n".join(lines)


def describe(analysis):
    lines = [f"Sentence: {analysis.sentence}",
             "Words:    " + "  ".join(f"{t.text}/{t.tag}" for t in analysis.tokens if t.tag != "PUNCT")]
    for n, cl in enumerate(analysis.clauses, 1):
        lines.append(describe_clause(cl, title=f"Clause {n}: {cl.role}"))
    if analysis.problems:
        lines.append("  PROBLEMS: " + "; ".join(analysis.problems))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) or "The girls did not eat the rice."
    print(describe(analyse(text)))
