"""English -> Hausa transfer: stage 2 of the English -> Hausa system.

It reads the English analysis (stage 1) and decides what the Hausa sentence
contains: which construction, which PAC, which verb form, which words.
Generation (hausa_generate.py) then writes the words out.

There is one rule (one function) per construction:

    verbal_clause       Musa ya sayi mota.              C1-C5, C10, ditransitives (C3)
    equational_clause   Ada malama ce.                  C6
    adjective_clause    Wannan gida babba ne. / Miyar tana da zafi.   C7
    become_clause       Musa ya yi fushi.               C7
    locative_clause     Yaran suna cikin gida.          C8
    possession_clause   Ada tana da mota.               C9
    belong_clause       Littafin na Musa ne.            C6/C9
    existential_clause  Akwai matsala. / An yi hayaniya.
    weather_clause      Ana ruwa.
    passive_clause      An gyara motar jiya. / Ngozi ce ta shirya abincin.     S17

Rules that work across clauses:
    question words      Me Musa ya saya?                C12 (transfer_clause)
    focus               Ada ce ta dafa miyar.           S10 (transfer_clause)
    relative clauses    Mutumin da ya kira jiya ...     C15 (relative_clause_words)
    reported clauses    Na san cewa ta tafi.            C16 (transfer_clause)
    clause linkers      Lokacin da ..., Idan ..., Da ... da ...   C13, C14 (translate_analysis)

Every rule writes a short note saying what it did ("PAC 3sg.m + completive
-> ya"), so you can see why a translation came out the way it did.
A word missing from the lexicon appears in [brackets] and is listed.
"""
from dataclasses import dataclass, field, replace

import english_words as EW
import hausa_grammar as G
import hausa_lexicon as L
from english_analysis import NounPhrase, analyse
from hausa_generate import (HNoun, adjective_form, copula, linker, noun_phrase,
                            sentence, split_frame)


# ===========================================================================
# The result of translating one sentence
# ===========================================================================

@dataclass
class Translation:
    english: str
    hausa: str
    rules: list = field(default_factory=list)     # notes on the rules used
    missing: list = field(default_factory=list)   # English words not in the lexicon
    analysis: object = None


class Notes:
    """Collects the rule notes and missing words for one sentence."""

    def __init__(self):
        self.rules, self.missing = [], []
        # Settings for the clause being translated (saved and restored around inner clauses):
        self.relative_pac = False      # relative PAC (suka, yake): question words, focus, relative clauses
        self.force_column = None       # PAC column chosen by a linker: idan + completive ...
        self.gap_head = None           # the noun a relative clause describes (its missing subject)
        self.whose_head = None         # the owner in a "whose" relative clause

    def save(self):
        return (self.relative_pac, self.force_column, self.gap_head, self.whose_head)

    def restore(self, state):
        self.relative_pac, self.force_column, self.gap_head, self.whose_head = state

    def rule(self, text):
        if text not in self.rules:
            self.rules.append(text)

    def miss(self, kind, word):
        if (kind, word) not in self.missing:
            self.missing.append((kind, word))
        return f"[{word}]"


# The missing subject of a relative clause or a subject focus: "the man who [ ] called"
GAP = NounPhrase(text="", head="", kind="gap")


# ===========================================================================
# Person and PAC
# ===========================================================================

def person_key(person, number, sex):
    """English person/number/sex -> the PAC row name: 1sg, 2sg.m, 3sg.f, 3pl ..."""
    sex = sex or G.DEFAULT_SEX
    if person == "1":
        return "1sg" if number == "sg" else "1pl"
    if person == "2":
        return f"2sg.{sex}" if number == "sg" else "2pl"
    return f"3sg.{sex}" if number == "sg" else "3pl"


def pac_column(vg, notes):
    """Which PAC column the English tense and aspect need (hausa_grammar.PAC_COLUMN).

    A clause linker can decide instead (idan + completive, yayin da + continuous).
    State verbs (know, believe) use the completive in the simple present;
    feelings (admire) use the continuous in the simple past.
    """
    if notes.force_column:
        notes.rule(f"PAC column set by the clause linker: {notes.force_column}")
        return notes.force_column
    column = G.PAC_COLUMN.get((vg.tense, vg.aspect), "completive")
    lemma = vg.lemma.split()[0] if vg.lemma else ""
    if (vg.tense, vg.aspect) == ("present", "simple") and lemma in G.STATIVE_VERBS:
        column = "completive"
        notes.rule(f"State verb: {lemma} uses the completive (Na san ...)")
    elif (vg.tense, vg.aspect) == ("past", "simple") and lemma in G.FEELING_VERBS:
        column = "continuous"
        notes.rule(f"Feeling verb: {lemma} uses the continuous")
    else:
        notes.rule(f"Tense: {vg.tense} {vg.aspect} -> {column} PAC")
    return column


def pac_words(person, column, negative, notes):
    """Return (words before the verb, words at the end of the clause).

    Negative completive:  ba ta ... ba    (Ada ba ta iya iyo ba)
    Negative continuous:  ba ya ...       (Ba ya cin nama)
    Negative future:      ba zan ... ba   (Ba zan tafi ba)

    After a question word (C12) the PAC takes its relative form:
    completive -> relative completive (suka), continuous -> relative continuous (yake).
    """
    if notes.relative_pac and not negative:
        column = G.RELATIVE_COLUMN.get(column, column)
    if not negative:
        form = L.pac(person, column)
        notes.rule(f"PAC: {person} + {column} -> {form}")
        return [form], []
    if column == "future":
        form = L.pac(person, "future")
        notes.rule(f"PAC: {person} + negative future -> ba {form} ... ba")
        return ["ba", form], ["ba"]
    neg_column = G.NEGATIVE_COLUMN.get(column, "negative " + column)
    form = L.pac(person, neg_column)
    notes.rule(f"PAC: {person} + {neg_column} -> {form}")
    before, after = split_frame(form)
    return [before], [after] if after else []


# ===========================================================================
# Noun phrases: English NounPhrase -> Hausa HNoun
# ===========================================================================

def to_np(np, role, notes, sex_hint="", negative=False):
    """Translate one English noun phrase.

    role: subject, object, receiver, after_prep, predicate, owner.
    negative: the clause is negative (anyone -> kowa, anything -> komai).
    It decides the pronoun set (ni / shi / masa), "the" -> -n/-r, and so on.
    """
    if np is None:
        return None
    if isinstance(np, str):
        return HNoun(word=notes.miss("phrase", np), english=np)

    if np.kind == "pronoun":
        key = "3sg.m" if np.head == "it" else person_key(np.person, np.number, np.sex)
        kind = {"object": "direct object", "receiver": "indirect object"}.get(role, "independent")
        word = L.pronoun(kind, key)
        return HNoun(word=word, english=np.head, kind="pronoun", person=key,
                     gender="f" if key.endswith(".f") else "m",
                     number="pl" if "pl" in key else "sg")

    if np.kind == "gap":                      # "the man who [ ] called": agrees with the head noun
        h = notes.gap_head
        return HNoun(word="", english="", kind="gap", gender=h.gender, number=h.number, person=h.person)

    if np.kind == "name":
        sex = np.sex or L.name_gender(np.head) or G.DEFAULT_SEX
        word = G.PLACE_NAMES.get(np.head.lower(), np.head)
        if word != np.head:
            notes.rule(f"Place name: {np.head} -> {word}")
        return HNoun(word=word, english=np.head, kind="name", gender=sex, person=f"3sg.{sex}")

    if np.kind == "indefinite":
        head = np.head.lower()
        if negative and head in G.NEGATIVE_INDEFINITES:
            word = G.NEGATIVE_INDEFINITES[head]
            notes.rule(f"In a negative sentence: {head} -> {word}")
        else:
            word = G.INDEFINITES.get(head) or notes.miss("indefinite", np.head)
        return HNoun(word=word, english=np.head, kind="indefinite", person="3sg.m")

    if np.kind == "demonstrative":            # "that" used alone
        return HNoun(word=L.demonstrative(np.head, "m", np.number), english=np.head, person="3sg.m")

    if np.kind == "coordinated":
        parts = [to_np(p, role, notes) for p in np.coordinated]
        persons = [p.person for p in parts]
        key = "1pl" if any(p.startswith("1") for p in persons) else \
              "2pl" if any(p.startswith("2") for p in persons) else "3pl"
        notes.rule(f"Coordination: X and Y -> X da Y, PAC {key}")
        return HNoun(word="", english=np.text, kind="coordinated", number="pl", person=key, parts=parts)

    if np.kind == "wh":                       # who -> wa, what -> me
        word = G.QUESTION_WORDS.get(np.head.lower()) or notes.miss("wh", np.head)
        return HNoun(word=word, english=np.head, kind="wh", person="3sg.m")

    if np.kind == "quantity":                 # "more" used alone -> ƙari
        word = G.QUANTITY_WORDS.get(np.head.lower()) or notes.miss("quantity", np.head)
        return HNoun(word=word, english=np.head, person="3sg.m")

    # --- an ordinary noun ---------------------------------------------------
    sex = np.sex or sex_hint
    entry = L.noun(np.head, sex)
    if entry is None:
        hn = HNoun(word=notes.miss("noun", np.head), english=np.head, number=np.number,
                   person="3pl" if np.number == "pl" else f"3sg.{G.DEFAULT_SEX}")
        return hn
    gender, number = entry["gender"], np.number
    always_plural = gender == "pl"
    if always_plural:                              # kuɗi (money), iyaye (parents) are plural in Hausa
        gender, number = "m", "pl"
        notes.rule(f"{entry['hausa']} is plural in Hausa")
    after_number = bool(np.count) and np.count != "one" and G.SINGULAR_AFTER_NUMBER
    if number == "pl" and not entry["plural"] and not after_number and not always_plural \
            and G.NO_PLURAL_MEANS_SINGULAR:
        number = "sg"                              # the lights -> wutar lantarki ta ...
        notes.rule(f"No plural for {np.head} in the lexicon: singular in Hausa ({entry['hausa']}, PAC 3sg)")
    use_plural = number == "pl" and not after_number
    if use_plural and entry["plural"]:
        word = entry["plural"]
    else:
        word = entry["hausa"]
    hn = HNoun(word=word, english=np.head, gender=gender, number=number,
               person="3pl" if number == "pl" else f"3sg.{gender}",
               linked=entry["linked"] if word == entry["hausa"] else "")
    if after_number:
        notes.rule(f"A17: singular noun after a number ({np.count} {np.head}s -> {word} ...)")

    # this / that / these / those (before the noun)
    if np.definite in ("near", "far"):
        eng = {("near", "sg"): "this", ("near", "pl"): "these",
               ("far", "sg"): "that", ("far", "pl"): "those"}[(np.definite, np.number)]
        hn.before.append(L.demonstrative(eng, gender, np.number))
        notes.rule(f"Demonstrative: {eng} -> {hn.before[-1]} before the noun")

    # which student -> wane ɗalibi (the clause rule adds ne/ce)
    if np.definite == "which":
        which = G.WHICH["pl" if number == "pl" else gender]
        hn.before.append(which)
        hn.kind = "which"
        notes.rule(f"which -> {which} (agrees with {word})")

    # quantifiers: many -> da yawa (after), some -> wasu (before)
    if np.quantifier in G.QUANTIFIERS:
        q, place, _ = G.QUANTIFIERS[np.quantifier]
        form_key = "pl" if number == "pl" else gender
        q = G.AGREEMENT.get(q, {}).get(form_key, q)          # kowace, isassun
        (hn.before if place == "before" else hn.after).append(q)
        notes.rule(f"Quantifier: {np.quantifier} -> {q} ({place} the noun)")
    elif np.quantifier:
        hn.after.append(notes.miss("quantifier", np.quantifier))

    # adjectives
    for a in np.adjectives:
        adj = L.adjective(a)
        if adj is None:
            hn.after.append(notes.miss("adjective", a))
        elif adj["type"] == "adjective":
            form = adjective_form(adj, gender, number)
            if G.ADJECTIVE_BEFORE_NOUN:
                form = linker(form, gender == "f" and number == "sg")
                hn.before.append(form)
                notes.rule(f"A7: adjective before the noun with a linker ({form} {word})")
            else:
                hn.after.append(form)
        elif adj["type"] == "noun after linker":   # waƙar gargajiya
            hn.possessor = HNoun(word=adj["masc"], english=a)
            notes.rule(f"Linked noun: {a} {np.head} -> {linker(word, hn.feminine)} {adj['masc']}")
        else:                                      # Hausa uses a noun: mai zafi / masu kyau
            mai = "masu" if number == "pl" else "mai"
            hn.after.append(f"{mai} {adj['masc']}")
            notes.rule(f"Quality noun: {a} {np.head} -> {word} {mai} {adj['masc']}")

    # number words come after the noun: fensir biyu
    if np.count and np.count != "one":
        hn.after.insert(0, L.number(np.count))
    elif np.count == "one":
        hn.after.insert(0, L.number("one"))

    # owner: my car -> motata; Musa's house -> gidan Musa
    if np.possessor is None and role == "subject" and notes.whose_head is not None:
        # "the girl whose father ..." -> yarinyar da mahaifinta ... (the owner is the head noun)
        hn.possessive_suffix = L.possessive_suffix(notes.whose_head.person, hn.feminine and word.endswith("a"))
        notes.rule(f"whose: the owned noun takes the owner's suffix (-{hn.possessive_suffix})")
    elif np.possessor is not None:
        if np.possessor.kind == "pronoun":
            key = person_key(np.possessor.person, np.possessor.number, np.possessor.sex)
            hn.possessive_suffix = L.possessive_suffix(key, hn.feminine and word.endswith("a"))
            notes.rule(f"Possessive suffix: {np.possessor.head} -> -{hn.possessive_suffix}")
        else:
            hn.possessor = to_np(np.possessor, "owner", notes)
            notes.rule("Possession: X's Y -> Y-n/-r X")
    elif np.modifiers:                            # "school bag" -> jakar makaranta
        mod = L.noun(np.modifiers[-1])
        hn.possessor = HNoun(word=mod["hausa"] if mod else notes.miss("noun", np.modifiers[-1]))
    elif np.definite == "definite" and hn.possessor is None:
        if role == "after_prep" and not G.DEFINITE_AFTER_PREPOSITION:
            notes.rule(f"A6: no -n/-r after a preposition ({word})")
        elif np.head in EW.UNIQUE_NOUNS:
            notes.rule(f"No -n/-r: there is only one {np.head} ({word})")
        else:
            hn.definite = True
            notes.rule(f"A6: the {np.head} -> {linker(word, hn.feminine, hn.linked, definite=True)}")

    if np.relative_clause is not None:            # C15: mutumin da ya kira jiya
        hn.relative = True
        hn.after.append(relative_clause_words(np.relative_clause, hn, notes))
    return hn


def subject_words(subj, notes):
    """The subject is written out, except a pronoun, which the PAC already shows."""
    if subj is None or subj.kind == "gap":
        return []
    if subj.kind == "pronoun" and G.DROP_SUBJECT_PRONOUNS:
        notes.rule(f"Subject pronoun left out: the PAC shows the person ({subj.person})")
        return []
    return [noun_phrase(subj)]


def relative_clause_words(rel, head, notes):
    """C15: noun + -n/-r + da + clause with the relative PAC.

    subject gap:   Mutumin da ya kira jiya          (the PAC agrees with the head noun)
    object gap:    Matar da muka ziyarta            (the verb has no object after it)
    whose:         Yarinyar da mahaifinta likita ne / Yaron da aka sace masa keke
    """
    state = notes.save()
    notes.relative_pac, notes.force_column, notes.gap_head, notes.whose_head = True, None, None, None
    if rel.gap == "subject":
        rel = replace(rel, subject=GAP)
        notes.gap_head = head
    elif rel.gap == "possessor":
        notes.whose_head = head
    notes.rule(f"C15: relative clause ({rel.gap} gap) -> {linker(head.word, head.feminine, head.linked)} "
               f"{G.RELATIVE_MARKER} ... + relative PAC")
    words = choose_rule(rel, notes)
    notes.restore(state)
    return " ".join(w for w in [G.RELATIVE_MARKER] + words if w)


# ===========================================================================
# Verbs
# ===========================================================================

def verb_entry(lemma, notes):
    v = L.verb(lemma)
    if v is None:
        word = notes.miss("verb", lemma)
        return {"hausa": word, "before_noun": word, "before_pronoun": word, "verbal_noun": word,
                "vn_with_object": word, "after_object": "", "yi_verb": False, "yi_da": False, "grade": ""}
    return v


def finite_verb(v, obj, with_wa, notes, has_clause=False):
    """Verb form after a completive, future or subjunctive PAC, and in commands.

    yi-verb:              yi dariya
    before 'wa':          saya wa ...
    before a pronoun:     saye (ya saye shi)
    before a noun:        sayi (ya sayi mota)
    nothing after it:     saya (also when the object is a question word: Me Musa ya saya?)
    """
    if v["yi_verb"]:
        notes.rule(f"yi-verb: yi {v['hausa']}")
        return ["yi", v["hausa"]]
    if with_wa:
        form, why = v["hausa"], "before the receiver: wa / masa"
    elif obj is not None and obj.kind == "pronoun":
        form, why = v["before_pronoun"], "before a pronoun object"
    elif obj is not None:
        form, why = v["before_noun"], "before a noun object"
    elif has_clause:
        form, why = v["before_noun"], "before a reported clause"
    else:
        form, why = v["hausa"], "no object after the verb"
    notes.rule(f"Verb form: {form} ({why})")
    return [form]


def verbal_noun(v, has_object, notes):
    """Verb form after a continuous PAC: the verbal noun (cin shinkafa, wasa)."""
    if v["yi_verb"]:
        form = v["hausa"]
    else:
        form = v["vn_with_object"] if has_object else v["verbal_noun"]
    notes.rule(f"Verbal noun after continuous PAC: {form}")
    return [form]


# ===========================================================================
# Places and adverbs
# ===========================================================================

def place_words(prep_phrases, verb_lemma, notes, locative=False):
    """in the house -> cikin gida; to the market (after go) -> kasuwa."""
    out = []
    for prep, np in prep_phrases:
        hn = to_np(np, "after_prep", notes)
        if prep == "to" and verb_lemma in G.MOTION_VERBS:
            notes.rule(f"No preposition after a motion verb ({verb_lemma} to ...)")
            out.append(noun_phrase(hn))
            continue
        word = G.PREPOSITIONS.get(prep) or notes.miss("preposition", prep)
        if prep == "in" and np is not None and getattr(np, "head", "") in G.INSIDE_NOUNS:
            word = "cikin"
        if locative and word == "a" and G.DROP_A_IN_LOCATIVE:
            notes.rule("Locative: a is left out after the continuous PAC")
            out.append(noun_phrase(hn))
            continue
        notes.rule(f"Preposition: {prep} -> {word}")
        out.append(f"{word} {noun_phrase(hn)}")
    return out


def adverb_words(adverbs, notes, motion=False):
    out = []
    for a in adverbs:
        key = a.lower()
        if key in ("never", "not"):
            continue
        if motion and key in G.MOTION_ADVERBS:
            word = G.MOTION_ADVERBS[key]
            notes.rule(f"After a motion verb: {key} -> {word}")
        else:
            word = G.ADVERBS.get(key) or L.adverb(key) or notes.miss("adverb", a)
        out.append(word)
    return out


# ===========================================================================
# One rule per construction
# ===========================================================================

def question_word(np, notes):
    """The fronted question phrase: wa, me, or wane ɗalibi ne (which + noun + ne/ce)."""
    hn = to_np(np, "subject", notes)
    if hn.kind == "which":
        cop = copula(hn)
        notes.rule(f"which + noun + {cop} goes first: {noun_phrase(hn)} {cop}")
        return [noun_phrase(hn), cop], hn
    notes.rule(f"Question word first: {np.head.lower()} -> {hn.word}")
    return [hn.word], hn


def verbal_clause(cl, notes):
    """Subject + PAC + verb + receiver + object + places + adverbs (+ ba).

    Also handles, inside the same pattern:
      question word as subject or object (C12):  Wa ya buɗe ƙofar?  Me Musa ya saya?
      commands:                                  Zauna.  Don Allah ka rufe ƙofar.  Kada ka taɓa wancan.
      can / never / must / would
    """
    vg = cl.verb
    notes.rule("Construction: verbal sentence")
    negative = vg.negative or vg.never
    command = cl.mood == "command"
    adverbs = list(cl.adverbs)
    front = []

    # --- the subject (or a question word standing for it)
    if cl.mood == "wh-question" and cl.wh_role == "subject":
        front, subj = question_word(cl.subject, notes)
        person, show_subject = subj.person, False
    else:
        subj = to_np(cl.subject, "subject", notes, negative=negative) if cl.subject is not None else None
        person, show_subject = (subj.person if subj else f"2sg.{G.DEFAULT_SEX}"), not command

    v = verb_entry(vg.lemma, notes)
    has_clause = bool(cl.clauses)                     # "I know that ..." (C16)
    if has_clause and vg.lemma in G.REPORT_VERBS:     # said that -> ya ce
        word = G.REPORT_VERBS[vg.lemma]
        v = dict(v, hausa=word, before_noun=word, before_pronoun=word, yi_verb=False)
        notes.rule(f"C16: {vg.lemma} + clause -> {word} (no {G.COMPLEMENTISER})")
    places = list(cl.prep_phrases)
    obj_np = cl.obj
    if has_clause and vg.lemma in G.TELL_VERBS and obj_np is not None and cl.indirect_obj is None:
        cl = replace(cl, indirect_obj=obj_np, obj=None)   # told me that ... -> faɗa mini cewa ...
        obj_np = None
        notes.rule(f"{vg.lemma} X that ...: X is the receiver")
    if vg.lemma in G.TO_AS_OBJECT and obj_np is None and places and places[0][0] == "to":
        obj_np = places.pop(0)[1]                     # leads to the village -> ta kai ƙauyen
        notes.rule(f"{vg.lemma} to X -> X is the object")
    if vg.lemma in G.MOTION_VERBS and obj_np is not None and obj_np.kind in ("noun", "name"):
        # "going to the market": the analysis reads "the market" as an object; it is a destination
        places.insert(0, ("to", obj_np))
        obj_np = None
    if cl.mood == "wh-question" and cl.wh_role == "object" and obj_np is not None:
        front, _ = question_word(obj_np, notes)       # Me Musa ya saya? (the verb has no object after it)
        obj_np = None
    obj = to_np(obj_np, "object", notes, negative=negative) if obj_np is not None else None
    if obj is not None and vg.lemma == "do" and obj_np.kind == "demonstrative":
        obj.word = G.DO_THAT                          # do that -> yi haka
        notes.rule(f"do that -> yi {G.DO_THAT}")

    # --- the receiver: ba Ada / aika wa Chika / aika masa
    receiver, with_wa = [], False
    if cl.indirect_obj is not None:
        if v["hausa"] in G.VERBS_WITHOUT_WA:
            rec = to_np(cl.indirect_obj, "object", notes)
            receiver = [noun_phrase(rec)]
            notes.rule(f"Receiver straight after {v['hausa']} (no wa)")
        else:
            rec = to_np(cl.indirect_obj, "receiver", notes)
            with_wa = True
            if rec.kind == "pronoun":
                receiver = [rec.word]
                notes.rule(f"Receiver pronoun: {rec.word}")
            else:
                receiver = ["wa", noun_phrase(rec)]
                notes.rule("Receiver: verb + wa + receiver + object")

    # --- "already" in a question: Har za ka tafi?
    if cl.mood in ("yes-no question", "wh-question") and "already" in [a.lower() for a in adverbs]:
        adverbs = [a for a in adverbs if a.lower() != "already"]
        front = [G.ALREADY_IN_QUESTION] + front
        notes.rule(f"already in a question -> {G.ALREADY_IN_QUESTION} at the start")

    # --- PAC and verb form (commands do not use the tense)
    column = "subjunctive" if command else pac_column(vg, notes)
    if command:
        please = "please" in [a.lower() for a in adverbs]
        adverbs = [a for a in adverbs if a.lower() != "please"]
        start = [G.PLEASE] if please else []
        if negative:
            notes.rule(f"Negative command: {G.NEGATIVE_COMMAND} + subjunctive PAC")
            before = start + [G.NEGATIVE_COMMAND, L.pac(person, "subjunctive")]
        elif please:
            notes.rule(f"Command with please: {G.PLEASE} + subjunctive PAC")
            before = start + [L.pac(person, "subjunctive")]
        else:
            notes.rule("Command: the bare verb, no PAC")
            before = []
        after = []
        verb = finite_verb(v, obj, with_wa, notes)
    elif vg.never:
        notes.rule(f"never -> negative completive + {G.NEVER_VERB} + verbal noun")
        before, after = pac_words(person, "completive", True, notes)
        verb = [G.NEVER_VERB] + verbal_noun(v, obj is not None, notes)
    elif vg.modal in ("ability", "possibility"):
        # can -> ta iya iyo; Can you ...? / may -> za ka iya ...
        future = cl.mood == "yes-no question" or vg.modal == "possibility"
        column = G.ABILITY_QUESTION_COLUMN if future else "completive"
        notes.rule(f"{'may' if vg.modal == 'possibility' else 'can'} -> {column} PAC + {G.ABILITY_VERB} + verb")
        before, after = pac_words(person, column, negative, notes)
        if obj is None and not with_wa:                   # iya iyo, iya tafiya (verbal noun)
            verb = [G.ABILITY_VERB] + verbal_noun(v, False, notes)
        else:                                             # iya taimake ni
            verb = [G.ABILITY_VERB] + finite_verb(v, obj, with_wa, notes)
    elif vg.modal in G.MODAL_BEFORE_SUBJUNCTIVE:
        word = G.MODAL_BEFORE_SUBJUNCTIVE[vg.modal]
        notes.rule(f"{vg.modal} -> {word} + subjunctive PAC")
        before, after = [word, L.pac(person, "subjunctive")], []
        verb = finite_verb(v, obj, with_wa, notes)
    else:
        if vg.modal == "conditional" and not notes.force_column:
            column = G.CONDITIONAL_COLUMN
            notes.rule(f"would -> {column} PAC")
        elif vg.modal and vg.modal != "conditional":
            notes.rule(f"Modal '{vg.modal}' has no rule yet; translated without it")
        before, after = pac_words(person, column, negative, notes)
        main_obj = None if vg.infinitive else obj         # "wanted to buy a car": the object belongs to buy
        if column == "continuous":
            verb = verbal_noun(v, main_obj is not None or with_wa or has_clause or bool(vg.infinitive), notes)
        else:
            verb = finite_verb(v, main_obj, with_wa, notes, has_clause)
        if vg.infinitive:                                 # sun so su tafi
            inf = verb_entry(vg.infinitive, notes)
            pac = L.pac(person, "subjunctive")
            verb += [pac] + finite_verb(inf, obj, with_wa, notes)
            notes.rule(f"to + verb -> subjunctive PAC ({pac}) + {inf['hausa']}")

    # "Nobody came" -> Ba wanda ya zo (relative PAC, no final ba)
    if cl.subject is not None and cl.subject.kind == "indefinite" and cl.subject.negative:
        rel = "relative continuous" if column == "continuous" else \
              "future" if column == "future" else "relative completive"
        form = L.pac("3sg.m", rel)
        notes.rule(f"nobody -> {G.NOBODY_SUBJECT} + {rel} PAC ({form})")
        before, after = [G.NOBODY_SUBJECT, form], []
        show_subject = False

    # --- the object, with "da" for yi + da verbs and a word after it for ba ... mamaki
    obj_words = [noun_phrase(obj)] if obj else []
    if obj_words and v["yi_da"]:
        obj_words = ["da"] + obj_words
        notes.rule(f"yi {v['hausa']} da + object")
    if v["after_object"]:
        obj_words += [v["after_object"]]
        notes.rule(f"{v['after_object']} comes after the object ({v['hausa']})")

    words = front + (subject_words(subj, notes) if show_subject else []) + before + verb + receiver + obj_words
    motion = vg.lemma in G.MOTION_VERBS or vg.infinitive in G.MOTION_VERBS
    words += place_words(places, vg.lemma, notes) + adverb_words(adverbs, notes, motion)
    return words + after


def passive_clause(cl, notes):
    """S17 passive.

    without "by":  An gyara motar jiya.          (impersonal PAC an / aka + verb + the thing)
    with "by":     Ngozi ce ta shirya abincin.   (the doer in focus: X ne/ce + relative PAC)
    """
    vg = cl.verb
    v = verb_entry(vg.lemma, notes)
    thing = to_np(cl.subject, "object", notes)
    column = pac_column(vg, notes)
    front = []
    if cl.agent is not None:
        doer = to_np(cl.agent, "subject", notes)
        cop = copula(doer)
        front, person = [noun_phrase(doer), cop], doer.person
        notes.relative_pac = True
        notes.rule(f"Passive with by: the doer goes first + {cop} + relative PAC")
    else:
        person = "4"
        notes.rule("Passive without by: impersonal PAC (an / aka)")
    before, after = pac_words(person, column, vg.negative, notes)
    receiver = []
    if notes.whose_head is not None:              # Yaron da aka sace masa keke
        receiver = [L.pronoun("indirect object", notes.whose_head.person)]
        notes.rule(f"whose + passive: the owner becomes {receiver[0]}")
    if column == "continuous":
        verb = verbal_noun(v, True, notes)
    else:
        verb = finite_verb(v, thing, bool(receiver), notes)
    return front + before + verb + receiver + [noun_phrase(thing)] + place_words(cl.prep_phrases, vg.lemma, notes) \
        + adverb_words(cl.adverbs, notes) + after


def equational_clause(cl, notes):
    """X is a Y -> X Y ne/ce;  negative: X ba Y ba ne/ce  (C6)."""
    notes.rule("Construction: equational (X Y ne/ce)")
    subj = to_np(cl.subject, "subject", notes)
    # the sex of the subject person: Ada, she, my mother -> f
    sex = subj.gender if subj and subj.kind in ("name", "pronoun") else getattr(cl.subject, "sex", "")
    pred = to_np(cl.complement[1], "predicate", notes, sex_hint=sex)
    if sex and pred.gender == sex:
        notes.rule(f"Predicate noun chosen to match the subject's sex ({pred.word})")
    cop = copula(pred)
    notes.rule(f"Copula: {cop} (agrees with {pred.word})")
    subj_words = [noun_phrase(subj)] if subj else []       # pronouns stay: Ita malama ce
    if cl.verb.negative:
        notes.rule("Negative equational: ba ... ba before ne/ce")
        return subj_words + ["ba", noun_phrase(pred), "ba", cop]
    return subj_words + [noun_phrase(pred), cop]


def zama_or(adj, subj, noun_verb):
    """A real adjective: zama + adjective (ya zama babba).
    A quality noun: noun_verb + noun (ya yi fushi, za ta ci gaba da fushi)."""
    if adj["type"] == "adjective":
        return ["zama", adjective_form(adj, subj.gender, subj.number)]
    return [noun_verb, adj["masc"]]


def adjective_clause(cl, notes, adj_word):
    """X is ADJ.  Three Hausa patterns, chosen by the 'type' column (C7):

    adjective:         Wannan gida babba ne.
    noun with da:      Miyar tana da zafi.
    noun without da:   Yaran suna farin ciki.
    """
    subj = to_np(cl.subject, "subject", notes)
    adj = L.adjective(adj_word)
    if adj is None:
        return [noun_phrase(subj), notes.miss("adjective", adj_word)]
    negative = cl.verb.negative
    if cl.verb.tense == "future":                 # will be proud -> za su yi alfahari
        before, after = pac_words(subj.person, "future", negative, notes)
        verb = zama_or(adj, subj, "yi")
        notes.rule(f"will be + adjective -> future PAC + {' '.join(verb)}")
        return subject_words(subj, notes) + before + verb + adverb_words(cl.adverbs, notes) + after
    if adj["type"] == "mai + noun":               # Ada mai gaskiya ce
        cop = copula(subj)
        notes.rule(f"Construction: mai + noun + {cop}")
        mid = ["ba", "mai", adj["masc"], "ba"] if negative else ["mai", adj["masc"]]
        return [noun_phrase(subj)] + mid + [cop]
    if adj["type"] == "verb":                     # Littafin ya ɓata
        notes.rule("Construction: Hausa uses a verb (completive PAC + verb)")
        before, after = pac_words(subj.person, "completive", negative, notes)
        return subject_words(subj, notes) + before + [adj["masc"]] + adverb_words(cl.adverbs, notes) + after
    if adj["type"] == "adjective":
        notes.rule("Construction: adjective + ne/ce")
        form = adjective_form(adj, subj.gender, subj.number)
        cop = copula(subj)
        notes.rule(f"Adjective agrees with the subject: {form}; copula {cop}")
        if negative:
            return [noun_phrase(subj), "ba", form, "ba", cop]
        return [noun_phrase(subj), form, cop]
    notes.rule(f"Construction: quality noun ({adj['type']})")
    before, after = pac_words(subj.person, "continuous", negative, notes)
    da = ["da"] if adj["type"] == "noun with da" else []
    return subject_words(subj, notes) + before + da + [adj["masc"]] + after + adverb_words(cl.adverbs, notes)


def become_clause(cl, notes, adj_word):
    """became ADJ -> yi + noun (ya yi fushi) or zama + adjective (ya zama babba)."""
    notes.rule("Construction: become + adjective")
    subj = to_np(cl.subject, "subject", notes)
    adj = L.adjective(adj_word)
    column = pac_column(cl.verb, notes)
    if column == "continuous":
        column = "completive"
    before, after = pac_words(subj.person, column, cl.verb.negative, notes)
    if adj is None:
        verb = ["zama", notes.miss("adjective", adj_word)]
    else:
        verb = zama_or(adj, subj, "yi")
    notes.rule(f"become -> {verb[0]} + {verb[1]}")
    return subject_words(subj, notes) + before + verb + adverb_words(cl.adverbs, notes) + after


def remain_future_clause(cl, notes, adj_word):
    """will remain upset -> za ta ci gaba da fushi"""
    subj = to_np(cl.subject, "subject", notes)
    adj = L.adjective(adj_word)
    before, after = pac_words(subj.person, "future", cl.verb.negative, notes)
    if adj is None:
        rest = [notes.miss("adjective", adj_word)]
    else:
        rest = zama_or(adj, subj, "ci gaba da")
    notes.rule(f"will remain + adjective -> future PAC + {' '.join(rest)}")
    return subject_words(subj, notes) + before + rest + adverb_words(cl.adverbs, notes) + after


def place_adverb_clause(cl, notes):
    """X is here / outside -> X + continuous PAC + adverb: Muna nan."""
    notes.rule("Construction: locative (PAC + place adverb)")
    subj = to_np(cl.subject, "subject", notes)
    before, after = pac_words(subj.person, "continuous", cl.verb.negative, notes)
    return subject_words(subj, notes) + before + adverb_words(cl.adverbs, notes) + after


def locative_clause(cl, notes):
    """X is in/at/behind Y -> X + continuous PAC + (preposition) + Y   (C8)."""
    notes.rule("Construction: locative (PAC + place)")
    subj = to_np(cl.subject, "subject", notes)
    before, after = pac_words(subj.person, "continuous", cl.verb.negative, notes)
    place = place_words([cl.complement[1]], "be", notes, locative=True)
    return subject_words(subj, notes) + before + place + adverb_words(cl.adverbs, notes) + after


def possession_clause(cl, notes):
    """X has Y -> X + continuous PAC + da + Y;  negative: ba + pronoun + da (C9)."""
    notes.rule("Construction: possession (PAC + da)")
    subj = to_np(cl.subject, "subject", notes)
    obj = to_np(cl.obj, "object", notes) if cl.obj is not None else None
    if cl.verb.negative or getattr(cl.obj, "negative", False):     # "do not have" / "have no"
        pron = L.pronoun("direct object", subj.person)
        notes.rule(f"Negative possession: ba {pron} da")
        start = subject_words(subj, notes) + ["ba", pron, "da"]
    else:
        before, _ = pac_words(subj.person, "continuous", False, notes)
        start = subject_words(subj, notes) + before + ["da"]
    return start + ([noun_phrase(obj)] if obj else []) + place_words(cl.prep_phrases, "have", notes) \
        + adverb_words(cl.adverbs, notes)


def belong_clause(cl, notes):
    """X belongs to Y -> X na/ta Y ne/ce."""
    notes.rule("Construction: belonging (X na/ta Y ne/ce)")
    subj = to_np(cl.subject, "subject", notes)
    owner_np = next((np for prep, np in cl.prep_phrases if prep == "to"), None)
    owner = to_np(owner_np, "owner", notes)
    of = "ta" if subj.feminine else "na"
    cop = copula(subj)
    notes.rule(f"of -> {of}, copula {cop} (agree with {subj.word})")
    if cl.verb.negative:
        return [noun_phrase(subj), "ba", of, noun_phrase(owner), "ba", cop]
    return [noun_phrase(subj), of, noun_phrase(owner), cop]


def existential_clause(cl, notes):
    """There is X -> Akwai X;  there is no X -> Babu X;  there was X -> An yi X."""
    vg = cl.verb
    negative = vg.negative or getattr(cl.subject, "negative", False)    # "There is no water"
    thing = to_np(cl.subject, "subject", notes)
    places = list(cl.prep_phrases)
    if cl.complement and cl.complement[0] == "place":     # "in the market"
        places.insert(0, cl.complement[1])
    rest = [noun_phrase(thing)] + place_words(places, "be", notes) + adverb_words(cl.adverbs, notes)
    if vg.tense == "past" or vg.aspect == "perfect":
        notes.rule("Construction: existential in the past -> impersonal an yi")
        before, after = pac_words("4", "completive", negative, notes)
        return before + ["yi"] + rest + after
    word = L.existential(negative)
    notes.rule(f"Construction: existential -> {word}")
    return [word] + rest


def weather_word(cl):
    """'rain' in "It is raining", 'cold' in "The weather is cold", else ''."""
    if cl.subject is None or getattr(cl.subject, "head", "").lower() not in G.WEATHER_SUBJECTS:
        return ""
    if cl.verb.lemma in G.WEATHER:
        return cl.verb.lemma
    if cl.complement and cl.complement[0] == "adjective" and cl.complement[1] in G.WEATHER:
        return cl.complement[1]
    return ""


def weather_clause(cl, notes, word):
    """It is raining -> Ana ruwa;  It was windy -> An yi iska;  It became cloudy -> Sama ya yi gajimare."""
    noun, subject = G.WEATHER[word]
    vg = cl.verb
    person = "3sg.m" if subject else "4"
    notes.rule(f"Construction: weather ({'subject ' + subject if subject else 'impersonal PAC'}) + {noun}")
    ongoing = vg.lemma != "become" and (vg.aspect == "progressive" or (vg.tense == "present" and vg.aspect == "simple"))
    if notes.force_column in ("completive", "subjunctive"):      # Idan an yi ruwa, ...
        ongoing = False
    if ongoing and vg.tense != "future":                  # It is raining / It was raining -> ana ruwa
        before, after = pac_words(person, "continuous", vg.negative, notes)
        verb = [noun]
    else:                                                 # It was windy / It will rain -> an yi / za a yi
        column = "future" if vg.tense == "future" else (notes.force_column or "completive")
        before, after = pac_words(person, column, vg.negative, notes)
        verb = ["yi", noun]
    start = [subject] if subject else []
    return start + before + verb + adverb_words(cl.adverbs, notes) + after


def where_is_clause(cl, notes):
    """Where is X? -> Ina X yake?  (question word + subject + relative continuous PAC)"""
    notes.rule("Construction: where is X? -> ina + X + relative continuous PAC")
    subj = to_np(cl.subject, "subject", notes)
    before, after = pac_words(subj.person, "continuous", cl.verb.negative, notes)
    return subject_words(subj, notes) + before + after


def what_is_clause(cl, notes):
    """What is X? / Who is X? -> Mene ne X? / Wane ne X?"""
    other = cl.subject if getattr(cl.subject, "kind", "") != "wh" else \
        (cl.complement[1] if cl.complement and cl.complement[0] == "noun" else None)
    start = G.WHAT_IS if cl.wh_word == "what" else G.WHO_IS
    notes.rule(f"Construction: {cl.wh_word} is X? -> {start} X")
    return [start] + ([noun_phrase(to_np(other, "subject", notes))] if other is not None else [])


# ===========================================================================
# Choosing the rule for each clause, and the whole sentence
# ===========================================================================

def focus_words(cl, notes):
    """S10: the focused part goes first, then ne/ce: Ada ce ..., Jiya ne ..., A Legas ne ..."""
    f = cl.focus
    if isinstance(f, NounPhrase):
        hn = to_np(f, "object", notes)
        words, cop = [noun_phrase(hn)], copula(hn)
    elif isinstance(f, tuple):                    # It is in Lagos that ...
        hn, words, cop = None, place_words([f], "be", notes), "ne"
    else:                                         # It was yesterday that ...
        hn, words, cop = None, adverb_words([f], notes), "ne"
    notes.rule(f"S10 focus: {' '.join(words)} + {cop} first, then the relative PAC")
    return words + [cop], hn


def transfer_clause(cl, notes, force_column=None, relative=False):
    """Pick the construction rule for one clause and run it.

    force_column / relative come from the clause linker (translate_analysis).
    """
    vg = cl.verb
    notes.relative_pac, notes.force_column = relative, force_column
    notes.gap_head = notes.whose_head = None
    if vg is None:
        notes.rule("No verb found in the English analysis")
        return [noun_phrase(to_np(cl.subject, "subject", notes))] if cl.subject else []

    front = []
    # --- focus (S10): It was Ada who cooked the soup -> Ada ce ta dafa miyar
    if cl.focus is not None:
        front, focus_hn = focus_words(cl, notes)
        notes.relative_pac = True
        if cl.gap == "subject" and focus_hn is not None:
            cl = replace(cl, subject=GAP)
            notes.gap_head = focus_hn

    # --- question words (C12): put the word first, use the relative PAC
    elif cl.mood == "wh-question":
        notes.relative_pac = True
        if cl.wh_role in ("place", "time", "reason", "manner"):
            word = G.QUESTION_WORDS.get(cl.wh_word) or notes.miss("wh", cl.wh_word)
            front = [word]
            notes.rule(f"Question word first: {cl.wh_word} -> {word}; relative PAC")
            cl = replace(cl, adverbs=[a for a in cl.adverbs if a.lower() != cl.wh_word])
            if vg.copula and cl.wh_role == "place" and not cl.complement:
                return front + where_is_clause(cl, notes)
        elif vg.copula:
            return what_is_clause(cl, notes)
        else:
            notes.rule("Question word replaces the subject or object; relative PAC")

    words = front + choose_rule(cl, notes)

    # --- reported clauses (C16): Na san cewa ta tafi; Malamin ya ce ...
    for inner in cl.clauses:
        if vg.lemma not in G.REPORT_VERBS:
            words.append(G.COMPLEMENTISER)
            notes.rule(f"C16: reported clause after {G.COMPLEMENTISER}")
        words += transfer_clause(inner, notes)
    return words


def choose_rule(cl, notes):
    """The construction rules, tried in this order."""
    vg = cl.verb
    if cl.existential:
        return existential_clause(cl, notes)
    w = weather_word(cl)
    if w:
        return weather_clause(cl, notes, w)
    comp = cl.complement
    if vg.lemma == "become" and comp and comp[0] == "adjective":
        return become_clause(cl, notes, comp[1])
    if vg.lemma in G.REMAIN_VERBS and comp and comp[0] == "adjective":
        if vg.tense == "future":
            return remain_future_clause(cl, notes, comp[1])
        notes.rule(f"{vg.lemma} + adjective = still be + adjective -> ... {G.ADVERBS['still']}")
        return adjective_clause(replace(cl, adverbs=cl.adverbs + ["still"]), notes, comp[1])
    if vg.voice == "passive":
        return passive_clause(cl, notes)
    if vg.copula and comp:
        if comp[0] == "noun":
            return equational_clause(cl, notes)
        if comp[0] == "adjective":
            return adjective_clause(cl, notes, comp[1])
        if comp[0] == "place":
            return locative_clause(cl, notes)
    if vg.copula and not comp and cl.adverbs:          # We are here -> Muna nan
        return place_adverb_clause(cl, notes)
    if vg.lemma == "belong":
        return belong_clause(cl, notes)
    if vg.possession or vg.lemma in G.POSSESSION_VERBS:
        return possession_clause(cl, notes)
    return verbal_clause(cl, notes)


def clause_linker(cl, counterfactual):
    """Decide the Hausa linker and its PAC for a subordinate clause (C14).

    Returns (Hausa linker, PAC column or None, relative PAC?, name of the rule).
    """
    vg = cl.verb
    simple = vg is not None and vg.aspect in ("simple", "perfect")
    key = cl.linker
    if key == "if" and counterfactual:
        return G.COUNTERFACTUAL, "completive", False, "counterfactual if -> da + completive"
    if key == "when":
        key = "when (past)" if vg is not None and vg.tense == "past" else "when"
    if key in G.SUBORDINATE_PAC:
        link, column, relative = G.SUBORDINATE_PAC[key]
        if key in ("while", "when (past)"):          # always relative; the column only for simple tenses
            return link, column if simple or key == "while" else None, relative, f"{key} -> {link}"
        if simple:
            return link, column, relative, f"{key} -> {link} + {column}"
        return link, None, relative, f"{key} -> {link}"
    link = G.CLAUSE_LINKERS.get(cl.linker, cl.linker)
    return link, None, False, f"{cl.linker} -> {link}"


def translate_analysis(analysis):
    """Turn a stage-1 Analysis into a Translation.

    Clauses keep the English order. The linker of each clause decides its PAC:
      Lokacin da ruwan sama ya fara, yaran suka ...   (past when: relative completive in both)
      Yayin da jaririn yake barci, ...                (while: relative continuous)
      Idan ka gama da wuri, za ka iya tafiya.         (if: completive)
      Da Ngozi ta iso da wuri, da ta haɗu da malamin. (counterfactual: da ... da ...)
    """
    notes = Notes()
    clauses = analysis.clauses
    counterfactual = any(c.role == "subordinate" and c.linker == "if" and c.verb is not None
                         and c.verb.tense == "past" and c.verb.aspect == "perfect" for c in clauses)
    words, after_past_when = [], False
    for n, cl in enumerate(clauses):
        force, relative, link = None, False, ""
        prev = clauses[n - 1] if n > 0 else None
        if cl.role == "subordinate":
            link, force, relative, name = clause_linker(cl, counterfactual)
            notes.rule(f"C14: {name}")
        elif cl.role == "coordinated":
            link = G.CLAUSE_LINKERS.get(cl.linker, cl.linker)
            if G.COMMA_BEFORE_COORDINATOR and words:
                words[-1] += ","
            notes.rule(f"C13: two clauses joined by {cl.linker} -> , {link}")
        else:
            if counterfactual and cl.verb is not None and cl.verb.modal == "conditional":
                link, force = G.COUNTERFACTUAL, "completive"
                notes.rule("C14: would have -> da + completive")
            if after_past_when and G.RELATIVE_AFTER_PAST_WHEN:
                relative = True
                notes.rule("C14: main clause after a past when-clause -> relative completive (suka)")
        # a subordinate clause that comes first is followed by a comma
        if prev is not None and prev.role == "subordinate" and cl.role == "main" and G.COMMA_AFTER_SUBORDINATE:
            words[-1] += ","
        after_past_when = cl.role == "subordinate" and cl.linker == "when" and \
            cl.verb is not None and cl.verb.tense == "past"
        words += ([link] if link else []) + transfer_clause(cl, notes, force, relative)
    marks = [t.lower for t in analysis.tokens if t.tag == "PUNCT"]
    end = "?" if "?" in marks else "!" if "!" in marks else "."
    return Translation(english=analysis.sentence, hausa=sentence(words, end), rules=notes.rules,
                       missing=notes.missing, analysis=analysis)


def translate(english):
    """English sentence -> Translation (analysis, transfer and generation)."""
    return translate_analysis(analyse(english))

