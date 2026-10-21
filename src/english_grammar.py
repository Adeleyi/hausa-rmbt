"""English grammar choices used by Hausa -> English. DATA: linguists can edit it.

Hausa often leaves out what English must show (a/the, simple or -ing, past or perfect).
Each value below is the default the system uses.
"""

# ===== 1. Tense: which English tense each PAC column becomes =====
# PAC column -> (English tense, aspect)
TENSE = {
    "completive": ("past", "simple"),            # ya iso -> arrived
    "relative completive": ("past", "simple"),
    "negative completive": ("past", "simple"),   # bai zo ba -> did not come
    "continuous": ("present", "progressive"),    # tana dafa -> is cooking
    "relative continuous": ("present", "progressive"),
    "negative continuous": ("present", "simple"),   # ba ya cin nama -> does not eat meat
    "future": ("future", "simple"),              # zai sayi -> will buy
    "negative future": ("future", "simple"),
    "subjunctive": ("present", "simple"),
}

# Verbs that describe a state: never -ing in English, and the completive is present.
#   Na san -> I know (not "I knew");  yana son -> likes (not "is liking")
STATE_VERBS = {"know", "believe", "understand", "like", "love", "want", "hate", "enjoy", "live",
               "lead", "belong", "own", "admire", "respect", "mean", "need", "prefer"}
# Of those, the ones whose COMPLETIVE also means present (Na san = I know)
PRESENT_COMPLETIVE = {"know", "believe", "understand", "lead", "mean", "prefer"}

# A continuous clause becomes the English simple present ("habit") when:
HABIT_ADVERBS = {"every day", "always", "regularly", "every week", "every morning"}
# ... or when the subject is a bare plural noun (Tsuntsaye suna tashi -> Birds fly).

# Subordinate clauses take the tense of a past main clause:
#   Saboda abincin yana da daɗi, kowa ya nemi ƙari -> Because the food WAS delicious ...
FOLLOW_MAIN_TENSE = {"because", "although", "since", "while", "when"}
# Conditional linkers: the English verb is present (Idan ka gama -> If you finish)
CONDITIONAL_LINKERS = {"if", "unless"}
# before / until: past after a past main clause (We left before the rain started),
# present otherwise (I will wait until you come)
TIME_LINKERS = {"before", "until"}

# ===== 2. Choosing the English verb from the context (word senses) =====
# One Hausa verb can mean several English verbs. Each rule:
#   hausa: the Hausa verb   english: the English verb to use
#   object: the rule applies when the object's English word is in this set
#   no_object / receiver / place / continuous / command / infinitive / subject: other conditions
# The first matching rule wins. If none match, the lexicon's English word is used.
SENSE_RULES = [
    dict(hausa="ci", object={"exam", "test", "examination"}, english="pass"),
    dict(hausa="ci", object={"gift", "prize", "race", "match", "election"}, english="win",
         object_english={"gift": "prize"}),
    dict(hausa="tashi", subject={"bird", "plane", "aeroplane"}, english="fly"),
    dict(hausa="zauna", continuous=True, english="live"),
    dict(hausa="zauna", command=True, english="sit down"),
    dict(hausa="zauna", place="in", english="stay"),
    dict(hausa="so", object_noun=True, continuous=True, english="like"),
    dict(hausa="so", infinitive=True, english="want"),
    dict(hausa="koya", receiver=True, english="teach"),
    dict(hausa="faɗa", receiver=True, english="tell"),
    dict(hausa="ɗauka", no_object=True, english="go out"),
    dict(hausa="ba", object={"story", "news", "advice"}, english="tell"),
    dict(hausa="nema", object={"more"}, english="ask for"),
    dict(hausa="tara", object={"money"}, english="save"),
    dict(hausa="tafi", no_object=True, no_place=True, statement=True, english="leave"),
    dict(hausa="ci gaba", object_is_quality=True, english="remain"),
]

# ===== 3. Nouns, articles and pronouns =====
# Nouns written with no "a/an" and no plural in English (besides UNCOUNTABLE in english_words.py)
MASS_NOUNS = {"dinner", "lunch", "breakfast", "anger", "traffic", "soup", "electricity", "light"}
# Nouns that take "the" even when Hausa has no -n/-r: UNIQUE_NOUNS in english_words.py
# After a preposition a singular noun takes "the": a kasuwa -> in the market
THE_AFTER_PREPOSITION = True

SUBJECT_PRONOUNS = {"1sg": "I", "2sg.m": "you", "2sg.f": "you", "3sg.m": "he", "3sg.f": "she",
                    "1pl": "we", "2pl": "you", "3pl": "they", "4": "they"}
OBJECT_PRONOUNS = {"1sg": "me", "2sg.m": "you", "2sg.f": "you", "3sg.m": "him", "3sg.f": "her",
                   "1pl": "us", "2pl": "you", "3pl": "them", "4": "them"}
POSSESSIVE_WORDS = {"1sg": "my", "2sg.m": "your", "2sg.f": "your", "3sg.m": "his", "3sg.f": "her",
                    "1pl": "our", "2pl": "your", "3pl": "their"}

# Relative words: who for people, that for things; whom when the person is the object
PERSON_NOUNS = {"man", "woman", "boy", "girl", "child", "children", "teacher", "student", "mother", "father",
                "person", "people", "doctor", "farmer", "player", "fan", "cook", "baby", "uncle", "wife",
                "husband", "friend", "lecturer", "sister", "brother", "parent"}

# ===== 4. Verbs with two objects: gave Ada a book (not "gave a book for Ada") =====
# Verbs that need a preposition before their object in English: ta kai ƙauyen -> leads TO the village
VERBS_WITH_PREPOSITION = {"lead": "to", "listen": "to", "look": "at", "wait": "for"}
DOUBLE_OBJECT_VERBS = {"give", "send", "tell", "show", "buy", "cook", "bring", "teach", "lend", "sell", "pay"}
# Other verbs put the receiver after "for": fetched water for the children

# ===== 5. Small word choices =====
# "sosai" (a lot) before an adjective is "very": An yi iska sosai -> It was very windy
A_LOT_BEFORE_ADJECTIVE = "very"
# Weather words that are verbs in English (It is raining); the rest are adjectives (It is cold)
WEATHER_VERBS = {"rain": "rain", "snow": "snow"}
