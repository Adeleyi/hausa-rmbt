"""Hausa -> English transfer: stage 2 of the Hausa -> English system.

It reads the Hausa analysis (stage 1, hausa_analysis.py) and decides what the
English sentence contains: tense, the English verb, a/the, word order.
English generation (english_generate.py) writes the words out.

One rule (one function) per Hausa construction, mirroring transfer_en_ha.py:

    verbal         Musa ya sayi mota.         -> Musa bought a car.
    equational     Ada malama ce.             -> Ada is a teacher.
    adjective      Miyar tana da zafi.        -> The soup is hot.
    become         Musa ya yi fushi.          -> Musa became angry.
    possession     Ada tana da mota.          -> Ada has a car.
    locative       Yaran suna cikin gida.     -> The children are in the house.
    belong         Littafin na Musa ne.       -> The book belongs to Musa.
    existential    Akwai matsala.             -> There is a problem.
    weather        Ana ruwa.                  -> It is raining.
    command        Zauna.                     -> Sit down.
plus questions, focus (Ada ce ta ... -> It was Ada who ...), relative clauses,
reported clauses (cewa), passives (an + verb) and clause linkers.

Every rule writes a note, so you can see why the English came out as it did.
"""
import copy
from dataclasses import dataclass, field

import english_generate as EG
import english_grammar as G
import english_words as EW
import hausa_analysis as H
from hausa_analysis import HNounPhrase

MASS = G.MASS_NOUNS | EW.UNCOUNTABLE


@dataclass
class Translation:
    hausa: str
    english: str
    rules: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    analysis: object = None


class Notes:
    """Collects the rule notes and missing words for one sentence."""

    def __init__(self):
        self.rules, self.missing = [], []
        self.main_past = False         # is the main clause in the past? (relative clauses follow it)

    def rule(self, text):
        if text not in self.rules:
            self.rules.append(text)


# ===========================================================================
# Persons and noun phrases
# ===========================================================================

def person_number(key):
    """'3sg.f' -> ('3', 'sg'); '4' (impersonal) -> ('3', 'pl')."""
    if not key or key == "4":
        return "3", "pl"
    return key[0], ("pl" if "pl" in key else "sg")


def is_person(np):
    if np is None or not isinstance(np, HNounPhrase):
        return False
    return np.kind in ("name", "pronoun") or (np.english or "").split(" ")[-1] in G.PERSON_NOUNS


def np_words(np, role, notes, negative=False, question=False, owner_hidden=False):
    """English words for a Hausa noun phrase.

    role: subject, object, receiver, place, predicate, owner
    """
    if np is None:
        return []
    if isinstance(np, str):
        return [np]
    if isinstance(np, tuple):                         # (preposition, noun phrase)
        return [np[0]] + np_words(np[1], "place", notes)
    k = np.kind
    if k == "gap":
        return []
    if k == "wh":
        return [np.english]
    if k == "pronoun":
        table = G.SUBJECT_PRONOUNS if role == "subject" else G.OBJECT_PRONOUNS
        word = table.get(np.person, "it")
        if np.from_pac:
            notes.rule(f"Subject shown only by the PAC ({np.person}) -> {word}")
        return [word]
    if k == "name":
        return [np.english or np.hausa]
    if k == "indefinite":
        if np.english == "nobody":
            return ["nobody"]
        alt = np.english_negative or np.english
        if (negative or question) and alt != np.english:
            notes.rule(f"In a negative sentence or question: {np.hausa} -> {alt}")
            return [alt]
        return [np.english]
    if k == "demonstrative":
        return [np.english]
    if k == "coordinated":
        parts = [" ".join(np_words(p, role, notes)) for p in np.coordinated]
        return [" and ".join(parts)]

    # --- an ordinary noun
    noun = np.english or np.hausa
    if np.number == "pl":
        noun = EG.plural(noun, MASS)
    det = []
    if isinstance(np.possessor, str) and not owner_hidden:
        det = [G.POSSESSIVE_WORDS.get(np.possessor, "the")]          # motata -> my car
        notes.rule(f"Possessive suffix ({np.possessor}) -> {det[0]} {noun}")
    elif isinstance(np.possessor, HNounPhrase):
        owner = np_words(np.possessor, "owner", notes)
        det = [" ".join(owner) + "'s"] if owner else []              # gidan Musa -> Musa's house
    elif np.demonstrative:
        dem = np.demonstrative
        if np.number == "pl":
            dem = {"this": "these", "that": "those"}.get(dem, dem)
        det = [dem]
    elif np.which:
        det = ["which"]
    elif np.quantifier:
        det = [np.quantifier]
    elif np.definite:
        det = ["the"]
        notes.rule(f"-n/-r (or ɗin) -> the {noun}")
    elif np.count or owner_hidden:
        det = []
    elif role == "place" and G.THE_AFTER_PREPOSITION and np.number == "sg":
        det = ["the"]
        notes.rule(f"After a preposition: the {noun} (Hausa has no -n/-r here)")
    elif (np.english or "") in EW.UNIQUE_NOUNS:
        det = ["the"]
    elif np.number == "pl" or (np.english or "") in MASS or np.adjectives and np.adjectives[-1] in MASS:
        det = []
    elif role in ("subject", "object", "predicate", "receiver"):
        first = np.adjectives[0] if np.adjectives else noun
        det = [EG.a_or_an(first)]
    words = det + ([np.count] if np.count else []) + list(np.adjectives) + [noun]
    if np.relative_clause is not None:
        words += relative_words(np.relative_clause, np, notes)
    return words


def relative_words(rel, head, notes):
    """C15: who / whom / that / whose + clause."""
    person = is_person(head)
    ctx = {"relative": True, "follow_past": notes.main_past}
    if rel.gap == "subject":
        word = "who" if person else "that"
        rest = clause_words(rel, notes, ctx)
        notes.rule(f"Relative clause (the {head.english} did it) -> {word} ...")
        return [word] + rest
    if rel.gap == "possessor":
        notes.rule("Relative clause with an owner (mahaifinta, masa) -> whose ...")
        return ["whose"] + clause_words(rel, notes, {**ctx, "whose": True})
    word = "whom" if person else "that"
    notes.rule(f"Relative clause (the {head.english} is the object) -> {word} ...")
    return [word] + clause_words(rel, notes, ctx)


# ===========================================================================
# Tense and the English verb
# ===========================================================================

def english_verb(cl, notes):
    """Choose the English verb, using the word-sense rules in english_grammar.py."""
    v = cl.verb
    obj_eng = (cl.obj.english if isinstance(cl.obj, HNounPhrase) else "") or ""
    subj_eng = (cl.subject.english if isinstance(cl.subject, HNounPhrase) else "") or ""
    continuous = cl.pac is not None and "continuous" in cl.pac.column
    for r in G.SENSE_RULES:
        if r["hausa"] != v.hausa or (v.form == "yi") != bool(r.get("yi")):
            continue
        if "object" in r and obj_eng not in r["object"]:
            continue
        if "subject" in r and subj_eng not in r["subject"]:
            continue
        if r.get("continuous") and not continuous:
            continue
        if r.get("command") and cl.mood != "command":
            continue
        if "place" in r and not any(p == r["place"] for p, _ in cl.places):
            continue
        if r.get("object_noun") and (cl.obj is None or v.infinitive):
            continue
        if r.get("infinitive") and not v.infinitive:
            continue
        if r.get("receiver") and cl.receiver is None:
            continue
        if r.get("no_object") and (cl.obj is not None or cl.receiver is not None or cl.leftovers):
            continue
        if r.get("no_place") and cl.places:
            continue
        if r.get("statement") and (cl.mood != "statement" or cl.negative):
            continue
        if r.get("object_is_quality") and not (isinstance(cl.obj, HNounPhrase) and quality_word(cl.obj)):
            continue
        if "object_english" in r and isinstance(cl.obj, HNounPhrase) and obj_eng in r["object_english"]:
            cl.obj.english = r["object_english"][obj_eng]
        notes.rule(f"Word sense: {v.hausa} here means '{r['english']}'")
        return r["english"]
    notes.rule(f"Verb: {v.text} = {v.hausa} -> {v.english}")
    return v.english


def quality_word(np):
    """The English adjective for a Hausa quality noun (fushi -> upset), or ''."""
    for info in H.adjective_readings((np.hausa or "").lower()):
        if info["type"] != "adjective":
            return info["english"]
    return ""


def clause_tense(cl, lemma, ctx, notes):
    """Return (tense, aspect, modal) for an English clause."""
    col = cl.pac.column if cl.pac is not None else "continuous"
    tense, aspect = G.TENSE.get(col, ("present", "simple"))
    modal = ""
    if cl.pac is not None:
        notes.rule(f"PAC {cl.pac.text} ({cl.pac.person}, {col}) -> English {tense} {aspect}")
    if tense == "future":
        tense, modal = "present", "will"
    if lemma in G.STATE_VERBS:
        if aspect == "progressive":
            aspect = "simple"
            notes.rule(f"State verb: {lemma} is never -ing")
        if col.endswith("completive") and lemma in G.PRESENT_COMPLETIVE:
            tense = "present"
            notes.rule(f"State verb: completive {lemma} means the present (Na san = I know)")
    if aspect == "progressive" and (set(cl.adverbs) & G.HABIT_ADVERBS or bare_plural(cl.subject)):
        aspect = "simple"
        notes.rule("A habit (every day / bare plural subject): simple present, not -ing")
    if ctx.get("conditional") and not modal:
        tense, aspect = "present", "simple"
        notes.rule("After if / unless / before / until: simple present")
    if ctx.get("follow_past") and tense == "present" and not modal:
        tense = "past"
        notes.rule("The clause follows the past tense of the main clause")
    if ctx.get("counterfactual") == "if":
        tense, aspect, modal = "past", "perfect", ""
        notes.rule("Counterfactual: Da ... -> If ... had ...")
    elif ctx.get("counterfactual") == "main":
        tense, aspect, modal = "present", "perfect", "would"
        notes.rule("Counterfactual: da ... -> would have ...")
    if cl.verb is not None and cl.verb.ability:
        modal = "can"                                # ta iya iyo -> can swim (an ability now)
        tense = "present"
        if aspect == "perfect":
            aspect = "simple"
        notes.rule("iya -> can")
    return tense, aspect, modal


def bare_plural(np):
    return isinstance(np, HNounPhrase) and np.kind == "noun" and np.number == "pl" and not (
        np.definite or np.possessor or np.demonstrative or np.quantifier or np.count)


def subject_info(cl):
    if isinstance(cl.subject, HNounPhrase):
        return person_number(cl.subject.person)
    return "3", "sg"


def adverb_words(cl):
    return [a for a in cl.adverbs if a not in ("already", "still")]


def place_words(cl, notes):
    out = []
    for prep, np in cl.places:
        out += [prep] + np_words(np, "place", notes)
    return out


# ===========================================================================
# One rule per construction
# ===========================================================================

def clause_words(cl, notes, ctx):
    """English words for one Hausa clause (no final punctuation)."""
    question = cl.mood in ("yes-no question", "wh-question")
    negative = cl.negative
    subj = [] if (ctx.get("relative") and cl.gap == "subject") else \
        np_words(cl.subject, "subject", notes, negative, question, owner_hidden=ctx.get("whose", False))
    person, number = subject_info(cl)
    c = cl.construction

    if cl.focus is not None:
        return focus_words(cl, notes, ctx)
    if c == "what-is":
        notes.rule(f"{cl.wh_word} is X?")
        return [cl.wh_word, "is"] + np_words(cl.subject, "predicate", notes)
    if c == "existential":
        return existential_words(cl, notes, ctx)
    if c == "weather":
        return weather_words(cl, notes, ctx)
    if c in ("equational", "adjective", "become", "locative", "belong") or (c == "possession" and cl.verb is None):
        return copular_words(cl, notes, ctx, subj, person, number, question)
    if cl.verb is None:
        notes.rule("No verb found in the Hausa analysis")
        return subj + [f"[{w}]" for w in cl.leftovers]
    return verbal_words(cl, notes, ctx, subj, person, number, question)


def assemble(front, subj, verb, rest, question, wh_subject=False):
    """Put the parts in English order. In a question the first helper verb goes before the subject."""
    if question and not wh_subject and verb:
        return front + verb[:1] + subj + verb[1:] + rest
    return front + subj + verb + rest


def verbal_words(cl, notes, ctx, subj, person, number, question):
    v = cl.verb
    if isinstance(cl.subject, HNounPhrase) and cl.subject.english == "nobody":
        cl.negative = False                         # Ba wanda ya zo -> Nobody came (not "did not come")
        notes.rule("nobody + positive verb")
    lemma = english_verb(cl, notes)
    if lemma == "remain":                           # za ta ci gaba da fushi -> she will remain upset
        adj = quality_word(cl.obj)
        tense, aspect, modal = clause_tense(cl, "be", ctx, notes)
        verb = EG.verb_group("remain", tense, aspect, cl.negative, modal, person, number, question=question)
        return assemble([], subj, verb, [adj] + adverb_words(cl), question)

    # --- impersonal PAC + verb + thing: a passive (An gyara motar -> The car was repaired)
    passive = cl.pac is not None and cl.pac.person == "4" and cl.obj is not None and cl.mood != "command"
    obj = cl.obj
    if passive:
        notes.rule("Impersonal an / aka + verb + thing -> English passive")
        owner_hidden = ctx.get("whose", False)
        subj = np_words(obj, "subject", notes, owner_hidden=owner_hidden)
        person, number = person_number(obj.person if obj.kind != "noun" else
                                       ("3pl" if obj.number == "pl" else "3sg"))
        obj = None

    if cl.pac is not None and cl.pac.person == "4" and lemma in G.WEATHER_VERBS.values():
        subj, person, number = ["it"], "3", "sg"     # an yi ruwa -> it rained
        notes.rule("Impersonal PAC + weather verb -> it")
    tense, aspect, modal = clause_tense(cl, lemma, ctx, notes)
    front = []
    if cl.mood == "command":
        notes.rule("Command: the bare verb")
        front = ["please"] if cl.please else []
        verb = (["do", "not"] if cl.negative else []) + [lemma]
        subj = []
        question = False
    elif v.ever and cl.negative:                    # Ban taɓa ganin komai ba -> I never saw anything
        notes.rule("taɓa + negative -> never")
        verb = ["never"] + EG.verb_group(lemma, tense, aspect, False, modal, person, number, passive)
    else:
        verb = EG.verb_group(lemma, tense, aspect, cl.negative, modal, person, number, passive, question)

    # question words
    wh_subject = cl.mood == "wh-question" and cl.wh_role == "subject"
    if cl.mood == "wh-question":
        if wh_subject:
            subj = np_words(cl.subject, "subject", notes)
            verb = EG.verb_group(lemma, tense, aspect, cl.negative, modal, person, number, passive)
        elif cl.wh_word == "which" and isinstance(cl.obj, HNounPhrase):
            front = np_words(cl.obj, "object", notes)              # Which book did Ada buy?
        else:
            front = [cl.wh_word]
        notes.rule(f"Question word first: {cl.wh_word}")
    # aka sace masa keke -> whose bicycle was stolen (masa is the owner, not a receiver)
    cl_receiver = None if passive and ctx.get("whose") else cl.receiver
    if v.infinitive:                                 # sun so su fita -> wanted to go out
        inf = v.infinitive[1].english
        if inf == "go out" and "outside" in cl.adverbs:
            inf = "go"
        verb += ["to", inf]
        notes.rule(f"so + subjunctive -> want to {inf}")

    # receiver and object
    rest = []
    neg_or_q = cl.negative or question
    obj_w = np_words(obj, "object", notes, neg_or_q, question) if obj is not None and not (
        cl.mood == "wh-question" and cl.wh_role == "object") else []
    rec_w = np_words(cl_receiver, "receiver", notes) if cl_receiver is not None else []
    if obj_w and lemma in G.VERBS_WITH_PREPOSITION:
        obj_w = [G.VERBS_WITH_PREPOSITION[lemma]] + obj_w      # leads to the village
    if rec_w and obj_w and lemma.split()[0] in G.DOUBLE_OBJECT_VERBS:
        rest += rec_w + obj_w
        notes.rule(f"{lemma} + receiver + thing (gave Ada a book)")
    elif rec_w and obj_w:
        rest += obj_w + ["for"] + rec_w
        notes.rule(f"{lemma} + thing + for + receiver")
    else:
        rest += rec_w + obj_w
    for inner in cl.clauses:                         # reported clause
        rest += ["that"] + clause_words(inner, notes, {"follow_past": tense == "past" and not modal})
        notes.rule("Reported clause: that + clause")
    rest += place_words(cl, notes) + adverb_words(cl)
    if "already" in cl.adverbs:
        rest += ["already"]
    rest += [f"[{w}]" for w in cl.leftovers]         # Hausa words the analysis could not place
    return assemble(front, subj, verb, rest, question and cl.mood != "command", wh_subject)


def copular_words(cl, notes, ctx, subj, person, number, question):
    """be / become / have / belong sentences."""
    c = cl.construction
    kind, value = cl.complement if cl.complement else ("", None)
    tense, aspect, modal = clause_tense(cl, "be", ctx, notes) if cl.pac is not None else ("present", "simple", "")
    if cl.pac is None and ctx.get("follow_past") and not ctx.get("relative"):
        tense = "past"                               # (ne/ce in a relative clause keeps the present)
    if c == "adjective" and cl.pac is not None and "completive" in cl.pac.column and not ctx.get("follow_past"):
        tense = "present"                            # Littafin ya ɓata -> The book is missing (a state)
        notes.rule("Completive + state word -> present state (is missing, is tired)")
    if c == "become" and modal == "will":
        c = "adjective"                              # za su yi alfahari -> will be proud
    aspect = "simple"
    neg = cl.negative
    front = []
    if cl.mood == "wh-question" and cl.wh_role:
        front = [cl.wh_word]
    if c == "possession":
        notes.rule("PAC + da + noun -> have")
        verb = EG.verb_group("have", tense, aspect, neg, modal, person, number, question=question)
        rest = np_words(cl.obj, "object", notes, neg, question)
    elif c == "belong":
        notes.rule("X na/ta Y ne/ce -> X belongs to Y")
        verb = EG.verb_group("belong", tense, aspect, neg, modal, person, number, question=question)
        rest = ["to"] + np_words(value, "object", notes)
    elif c == "become":
        notes.rule("yi + quality noun -> became + adjective")
        verb = EG.verb_group("become", tense, aspect, neg, modal, person, number, question=question)
        rest = very(cl) + [value]
    elif c == "equational":
        notes.rule("X Y ne/ce -> X is a Y")
        verb = EG.verb_group("be", tense, aspect, neg, modal, person, number)
        rest = np_words(value, "predicate", notes)
    elif c == "adjective":
        notes.rule(f"-> be + adjective ({value})")
        verb = EG.verb_group("be", tense, aspect, neg, modal, person, number)
        if "still" in cl.adverbs:
            verb += ["still"]
        rest = very(cl) + [value]
    else:                                            # locative
        notes.rule("PAC + place -> be + place")
        verb = EG.verb_group("be", tense, aspect, neg, modal, person, number)
        if kind == "place":
            prep, np = value
            rest = [prep] + np_words(np, "place", notes)
        elif value == "where":
            rest = []
        else:
            rest = [value] if value else []
    rest += place_words(cl, notes) + [a for a in adverb_words(cl) if a != "a lot"]
    return assemble(front, subj, verb, rest, question)


def very(cl):
    return [G.A_LOT_BEFORE_ADJECTIVE] if "a lot" in cl.adverbs else []


def existential_words(cl, notes, ctx):
    """Akwai X -> There is X;  Babu X -> There is no X;  An yi X -> There was X."""
    np = cl.subject
    plural = isinstance(np, HNounPhrase) and np.number == "pl"
    past = cl.pac is not None or ctx.get("follow_past")
    be = ("were" if plural else "was") if past else ("are" if plural else "is")
    words = ["there", be]
    thing = np_words(np, "object", notes)
    if cl.negative:
        if thing and thing[0] in ("a", "an"):
            thing = thing[1:]
        words.append("no")
    notes.rule(f"Existential -> there {be}{' no' if cl.negative else ''}")
    return words + thing + place_words(cl, notes) + adverb_words(cl)


def weather_words(cl, notes, ctx):
    """Ana ruwa -> It is raining;  An yi iska -> It was windy;  Sama ya yi gajimare -> It became cloudy."""
    word = cl.complement[1]
    col = cl.pac.column if cl.pac is not None else "continuous"
    sky = isinstance(cl.subject, HNounPhrase) and cl.subject.hausa == "sama"
    tense = "past" if "completive" in col else "present"
    modal = "will" if "future" in col else ""
    notes.rule(f"Weather -> it + {word}")
    if word in G.WEATHER_VERBS:
        aspect = "progressive" if "continuous" in col else "simple"
        verb = EG.verb_group(G.WEATHER_VERBS[word], tense, aspect, cl.negative, modal)
        return ["it"] + verb + adverb_words(cl)
    lemma = "become" if sky else "be"
    verb = EG.verb_group(lemma, tense, "simple", cl.negative, modal)
    rest = very(cl) + [word] + [a for a in adverb_words(cl) if a != "a lot"]
    return ["it"] + verb + rest


def focus_words(cl, notes, ctx):
    """Ada ce ta dafa miyar -> It was Ada who cooked the soup."""
    col = cl.pac.column if cl.pac is not None else ""
    be = "was" if "completive" in col else "is"
    f = cl.focus
    if isinstance(f, HNounPhrase):
        focus = np_words(f, "object", notes)
        word = "who" if is_person(f) and cl.gap == "subject" else "that"
    elif isinstance(f, tuple):
        focus = [f[0]] + np_words(f[1], "place", notes)
        word = "that"
    else:
        focus = [f]
        word = "that"
    notes.rule(f"Focus (X ne/ce ...) -> It {be} X {word} ...")
    inner = copy.copy(cl)
    inner.focus = None
    rest = clause_words(inner, notes, {**ctx, "relative": cl.gap == "subject"})
    return ["it", be] + focus + [word] + rest


# ===========================================================================
# The whole sentence
# ===========================================================================

def translate_analysis(analysis):
    notes = Notes()
    for t in analysis.tokens:
        if "UNKNOWN" in t.options:
            notes.missing.append(("word", t.text))
    clauses = analysis.clauses
    main = next((c for c in clauses if c.role == "main"), clauses[0] if clauses else None)
    main_past = main is not None and main.pac is not None and "completive" in main.pac.column \
        and not (main.verb is not None and main.verb.english in G.PRESENT_COMPLETIVE)
    notes.main_past = main_past
    words = []
    for n, cl in enumerate(clauses):
        ctx = {}
        link = []
        if cl.linker_english == "counterfactual":
            ctx["counterfactual"] = "if" if cl.role == "subordinate" else "main"
            link = ["if"] if cl.role == "subordinate" else []
        elif cl.role == "subordinate":
            link = [cl.linker_english]
            if cl.linker_english in G.CONDITIONAL_LINKERS:
                ctx["conditional"] = True
            elif cl.linker_english in G.TIME_LINKERS:
                ctx["follow_past" if main_past else "conditional"] = True
            elif cl.linker_english in G.FOLLOW_MAIN_TENSE and main_past:
                ctx["follow_past"] = True
            notes.rule(f"Clause linker: {cl.linker} -> {cl.linker_english}")
        elif cl.role == "coordinated":
            if words:
                words[-1] += ","
            link = [cl.linker_english]
            notes.rule(f"Clause linker: , {cl.linker} -> , {cl.linker_english}")
        prev = clauses[n - 1] if n > 0 else None
        if prev is not None and prev.role == "subordinate" and cl.role == "main" and words:
            words[-1] += ","
        words += link + clause_words(cl, notes, ctx)
    marks = [t.lower for t in analysis.tokens if "PUNCT" in t.options]
    end = "?" if "?" in marks else "!" if "!" in marks else "."
    return Translation(hausa=analysis.sentence, english=EG.sentence(words, end), rules=notes.rules,
                       missing=notes.missing, analysis=analysis)


def translate(hausa):
    """Hausa sentence -> Translation (analysis, transfer, generation)."""
    return translate_analysis(H.analyse(hausa))

