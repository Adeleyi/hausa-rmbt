"""Hausa word lists used to read Hausa (hausa_analysis.py, Hausa -> English stage 1).

This file is DATA, not program logic. Linguists can edit it freely.

Most Hausa words are read from the lexicon workbook (nouns, verbs, adjectives,
PAC forms, pronouns, possessive suffixes). This file holds the small closed
classes the reader needs to recognise, with the English it stands for.
Tables that are just hausa_grammar.py read backwards are built from it, so a
Hausa word is written in one place only.
"""
import hausa_grammar as HG

# ---------------------------------------------------------------------------
# 1. Words that join clauses
# ---------------------------------------------------------------------------
COORDINATORS = {"kuma": "and", "amma": "but", "don haka": "so", "ko": "or"}

# Hausa linker -> English linker. These start a subordinate clause.
SUBORDINATORS = {
    "lokacin da": "when", "yayin da": "while", "idan": "if", "in": "if",
    "saboda": "because", "ko da yake": "although", "tun da": "since",
    "sai dai idan": "unless", "kafin": "before", "bayan da": "after", "har": "until",
}
# "Da ... , da ..." at the start of two clauses: a counterfactual (If X had ..., Y would have ...)
COUNTERFACTUAL = HG.COUNTERFACTUAL

# "cewa" introduces a reported clause: Na san cewa ta tafi.
COMPLEMENTISER = HG.COMPLEMENTISER
# "ce" (say) is followed directly by the reported clause: Malamin ya ce ...
SAY_VERB = "ce"

# ---------------------------------------------------------------------------
# 2. Question words (C12)
# ---------------------------------------------------------------------------
QUESTION_WORDS = {
    "wa": "who", "me": "what", "mene": "what", "ina": "where", "yaushe": "when",
    "yaya": "how", "me ya sa": "why", "don me": "why", "saboda me": "why", "nawa": "how much",
}
# which + noun: wane (m) / wace (f) / waɗanne (pl)
WHICH = {hausa: gender for gender, hausa in HG.WHICH.items()}
# "Mene ne X?" / "Wane ne X?"
WHAT_IS = {"mene ne": "what", "wane ne": "who", "wace ce": "who"}

# ---------------------------------------------------------------------------
# 3. Prepositions, adverbs, time words
# ---------------------------------------------------------------------------
PREPOSITIONS = {
    "a": "in", "a cikin": "in", "cikin": "in", "a kan": "on", "kan": "on",
    "kusa da": "near", "bayan": "behind", "zuwa": "to", "daga": "from",
    "ƙarƙashin": "under", "tsakanin": "between", "gaban": "in front of",
    "wajen": "outside", "kamar": "like", "game da": "about", "ga": "to",
}
# Hausa adverb (one or more words) -> English
ADVERBS = {
    "jiya": "yesterday", "yau": "today", "gobe": "tomorrow", "yanzu": "now",
    "kullum": "every day", "da wuri": "early", "a makare": "late",
    "nan": "here", "can": "there", "a waje": "outside", "waje": "outside",
    "a ciki": "inside", "ciki": "inside", "zuwa kudu": "south", "zuwa arewa": "north",
    "zuwa gabas": "east", "zuwa yamma": "west", "da safiyar yau": "this morning",
    "da yammacin yau": "this evening", "bara": "last year",
    "shekarar da ta wuce": "last year", "shekaran da ta wuce": "last year",
    "sosai": "a lot", "da kyau": "well", "da ƙarfi": "loudly", "tuni": "already",
    "har yanzu": "still", "tare": "together", "a kan lokaci": "on time",
    "da sauri": "quickly", "a hankali": "slowly", "akai-akai": "regularly",
    "cike da alfahari": "proudly", "da gudu": "running", "ma": "too",
}
PLEASE = HG.PLEASE.lower()

# ---------------------------------------------------------------------------
# 4. Quantifiers, indefinites, demonstratives, numbers
# ---------------------------------------------------------------------------
# Hausa -> (English, "before" or "after" the noun in Hausa)
QUANTIFIERS = {
    "da yawa": ("many", "after"), "kaɗan": ("a few", "after"),
    "wasu": ("some", "before"), "duk": ("all", "before"),
    "kowane": ("every", "before"), "kowace": ("every", "before"),
    "isasshen": ("enough", "before"), "isasshiyar": ("enough", "before"), "isassun": ("enough", "before"),
}
# Hausa -> (English in a positive sentence, English in a negative sentence)
INDEFINITES = {
    "kowa": ("everyone", "anyone"), "komai": ("everything", "anything"),
    "wani": ("someone", "anyone"), "wata": ("someone", "anyone"),
    "wani abu": ("something", "anything"), "ƙari": ("more", "more"), "haka": ("that", "that"),
}
NOBODY = HG.NOBODY_SUBJECT
DEMONSTRATIVES = {"wannan": "this", "waɗannan": "these", "wancan": "that", "waccan": "that",
                  "waɗancan": "those"}

# ---------------------------------------------------------------------------
# 5. Small grammar words
# ---------------------------------------------------------------------------
COPULA = {"ne", "ce"}
NEGATIVE = "ba"
NEGATIVE_COMMAND = HG.NEGATIVE_COMMAND
EXISTENTIAL = {"akwai": False, "babu": True}       # word -> negative?
RECEIVER_MARKER = "wa"                             # ya aika wa Chika ...
OF_WORDS = {"na": "m", "ta": "f"}                  # Littafin na Musa ne
MAI_WORDS = {"mai": "sg", "masu": "pl"}            # hayaniya mai ƙarfi
ABILITY_VERB = "iya"                               # ta iya iyo
EVER_VERB = "taɓa"                                 # ban taɓa ganin ...
DO_VERB = "yi"                                     # ya yi dariya
DEFINITE_WORD = "ɗin"                              # fim ɗin
# English verbs after which a bare noun is a place, not an object: za mu tafi kasuwa
MOTION_VERBS = {"go", "come", "return", "travel", "go out", "run"}

# Verb forms that are not in the lexicon columns: written form -> (Hausa verb, English, form)
# zaune / tsaye are "stative" forms: suke zaune = they live (are settled)
EXTRA_VERB_FORMS = {"zaune": ("zauna", "live", "stative"), "tsaye": ("tsaya", "stand", "stative")}

# Place names spelled differently in Hausa
PLACE_NAMES = {hausa.lower(): english.title() for english, hausa in HG.PLACE_NAMES.items()}

# Weather nouns used with the impersonal PAC: Ana ruwa, An yi iska
WEATHER = {"ruwa": "rain", "sanyi": "cold", "zafi": "hot", "iska": "windy", "rana": "sunny",
           "gajimare": "cloudy"}

# ---------------------------------------------------------------------------
# 6. Which English word to use when a Hausa word has several meanings
# ---------------------------------------------------------------------------
# The lexicon is written English -> Hausa. Read the other way, one Hausa word
# can point to several English words. The first row in the tab is used,
# unless this table says otherwise.
PREFERRED_ENGLISH = {
    "malami": "teacher", "malama": "teacher", "zauna": "sit", "tashi": "stand up",
    "yaro": "boy", "yara": "children", "tafi": "go", "ci": "eat", "sani": "know",
    "fasa": "break", "gyara": "repair", "ɗauka": "carry", "jawo": "cause", "yarda": "believe",
    "matar": "woman", "mata": "woman", "mutum": "man", "gudu": "run", "jarrabawa": "exam", "gida": "house", "tsorata": "frighten",
}
