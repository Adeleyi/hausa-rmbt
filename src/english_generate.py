"""English generation: the last stage of Hausa -> English.

The transfer stage decides WHAT the English sentence says (verb "buy", past,
negative, subject Ada, object "car", indefinite). This file writes it out:
  - verb forms: bought, buys, buying, did not buy, is buying, was bought
  - helper verbs in questions: Did Ada buy a car?
  - plurals: children, students
  - a / an / the
  - capital letter and final punctuation
"""
import english_words as EW

VOWELS = "aeiou"
_PAST = {base: forms[0] for base, forms in EW.IRREGULAR_VERBS.items()}
_PART = {base: forms[1] for base, forms in EW.IRREGULAR_VERBS.items()}
_PLURAL = {sg: pl for pl, sg in EW.IRREGULAR_PLURALS.items()}


# ---------------------------------------------------------------------------
# Words
# ---------------------------------------------------------------------------

# Two-syllable verbs stressed on the end also double: submit -> submitted
DOUBLE_LAST = {"submit", "admit", "permit", "commit", "prefer", "occur", "refer", "regret", "forget", "begin",
               "control", "travel"}


def _double_final(verb):
    """stop -> stopp(ed): one syllable (one vowel), ending consonant-vowel-consonant."""
    if verb in DOUBLE_LAST:
        return True
    return (len(verb) >= 3 and sum(c in VOWELS for c in verb) == 1 and verb[-1] not in VOWELS + "wxy"
            and verb[-2] in VOWELS and verb[-3] not in VOWELS)


def _split(verb):
    """'stand up' -> ('stand', ' up'): only the first word changes."""
    head, _, rest = verb.partition(" ")
    return head, (" " + rest if rest else "")


def past(verb):
    v, rest = _split(verb)
    if v in _PAST:
        return _PAST[v] + rest
    if v.endswith("e"):
        return v + "d" + rest
    if v.endswith("y") and v[-2] not in VOWELS:
        return v[:-1] + "ied" + rest
    if _double_final(v):
        return v + v[-1] + "ed" + rest
    return v + "ed" + rest


def participle(verb):
    v, rest = _split(verb)
    if v in _PART:
        return _PART[v] + rest
    return past(v) + rest


def third_person(verb):
    v, rest = _split(verb)
    if v == "have":
        return "has" + rest
    if v in ("be",):
        return "is" + rest
    if v.endswith(("s", "sh", "ch", "x", "z", "o")):
        return v + "es" + rest
    if v.endswith("y") and v[-2] not in VOWELS:
        return v[:-1] + "ies" + rest
    return v + "s" + rest


def ing(verb):
    v, rest = _split(verb)
    if v == "be":
        return "being" + rest
    if v.endswith("ie"):
        return v[:-2] + "ying" + rest
    if v.endswith("e") and not v.endswith("ee") and len(v) > 2:
        return v[:-1] + "ing" + rest
    if _double_final(v):
        return v + v[-1] + "ing" + rest
    return v + "ing" + rest


def plural(noun, mass_nouns=()):
    if noun in mass_nouns or noun in EW.UNCOUNTABLE:
        return noun
    head, _, tail = noun.rpartition(" ")
    word = tail
    if word in _PLURAL:
        out = _PLURAL[word]
    elif word in EW.IRREGULAR_PLURALS:        # already plural: children
        out = word
    elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        out = word                            # the lexicon already gives a plural: parents
    elif word.endswith(("s", "sh", "ch", "x", "z")):
        out = word + "es"
    elif word.endswith("y") and len(word) > 1 and word[-2] not in VOWELS:
        out = word[:-1] + "ies"
    elif word.endswith("fe"):
        out = word[:-2] + "ves"
    else:
        out = word + "s"
    return (head + " " if head else "") + out


def a_or_an(word):
    return "an" if word[:1].lower() in VOWELS and not word.lower().startswith(("uni", "use", "eu")) else "a"


# ---------------------------------------------------------------------------
# Verb groups
# ---------------------------------------------------------------------------

def be_form(tense, person, number):
    if tense == "past":
        return "was" if (number == "sg" and person in ("1", "3")) else "were"
    if person == "1" and number == "sg":
        return "am"
    return "is" if (number == "sg" and person == "3") else "are"


def verb_group(lemma, tense="present", aspect="simple", negative=False, modal="", person="3", number="sg",
               passive=False, question=False):
    """Return the verb words as a list. In a question, the first word is the helper
    verb that goes before the subject.

    verb_group("buy", "past", negative=True)        -> ["did", "not", "buy"]
    verb_group("cook", "present", "progressive")    -> ["is", "cooking"]
    verb_group("buy", "past", question=True)        -> ["did", "buy"]   (Did Ada buy ...?)
    """
    neg = ["not"] if negative else []
    third = number == "sg" and person == "3"
    if modal:                                   # will / can / would have ...
        words = [modal] + neg
        if aspect == "perfect":
            return words + ["have", participle(lemma)]
        if passive:
            return words + ["be", participle(lemma)]
        if aspect == "progressive":
            return words + ["be", ing(lemma)]
        return words + [lemma]
    if passive:
        return [be_form(tense, person, number)] + neg + [participle(lemma)]
    if lemma == "be":
        return [be_form(tense, person, number)] + neg
    if aspect == "progressive":
        return [be_form(tense, person, number)] + neg + [ing(lemma)]
    if aspect == "perfect":
        have = "had" if tense == "past" else ("has" if third else "have")
        return [have] + neg + [participle(lemma)]
    if tense == "past":
        if negative or question:
            return ["did"] + neg + [lemma]
        return [past(lemma)]
    # present simple
    if negative or question:
        return ["does" if third else "do"] + neg + [lemma]
    return [third_person(lemma) if third else lemma]


# ---------------------------------------------------------------------------
# The sentence
# ---------------------------------------------------------------------------

def sentence(words, end="."):
    text = " ".join(w.strip() for w in words if w and w.strip())
    text = " ".join(text.split()).replace(" ,", ",").replace("can not", "cannot")
    if not text:
        return ""
    return text[0].upper() + text[1:] + end
