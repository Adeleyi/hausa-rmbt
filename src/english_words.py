"""English word lists for reading and writing English. DATA: linguists can edit it.

Most words come from the lexicon (data/lexicon/*.csv). Here: grammar words, irregular forms,
names and the sex of people words, and words not yet in the lexicon.
"""

# ===== 1. Grammar words =====

# Personal pronouns: word -> (person, number, sex, case)
# sex is "m", "f" or "" (unknown); case is "subject" or "object"
PRONOUNS = {
    "i":    ("1", "sg", "",  "subject"),
    "me":   ("1", "sg", "",  "object"),
    "you":  ("2", "sg", "",  "subject"),   # could also be plural; see A2/B11 default
    "he":   ("3", "sg", "m", "subject"),
    "him":  ("3", "sg", "m", "object"),
    "she":  ("3", "sg", "f", "subject"),
    "her":  ("3", "sg", "f", "object"),    # "her" can also be possessive; decided by context
    "it":   ("3", "sg", "",  "subject"),
    "we":   ("1", "pl", "",  "subject"),
    "us":   ("1", "pl", "",  "object"),
    "they": ("3", "pl", "",  "subject"),
    "them": ("3", "pl", "",  "object"),
}

# Possessive words before a noun: word -> (person, number, sex)
POSSESSIVES = {
    "my": ("1", "sg", ""), "your": ("2", "sg", ""), "his": ("3", "sg", "m"),
    "her": ("3", "sg", "f"), "its": ("3", "sg", ""), "our": ("1", "pl", ""),
    "their": ("3", "pl", ""),
}

ARTICLES = {"a": "indefinite", "an": "indefinite", "the": "definite", "no": "negative"}

# this/that/these/those: word -> (distance, number)
DEMONSTRATIVES = {
    "this": ("near", "sg"), "these": ("near", "pl"),
    "that": ("far", "sg"), "those": ("far", "pl"),
}

QUANTIFIERS = {"many", "some", "all", "every", "each", "more", "enough", "few", "several", "any"}

NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twenty": 20,
    "hundred": 100, "thousand": 1000,
}

# Forms of "be", "have" and "do": word -> (lemma, tense, person/number it shows)
BE_FORMS = {
    "be": ("be", "base"), "am": ("be", "present"), "is": ("be", "present"),
    "are": ("be", "present"), "was": ("be", "past"), "were": ("be", "past"),
    "been": ("be", "participle"), "being": ("be", "ing"),
}
HAVE_FORMS = {"have": "present", "has": "present", "had": "past", "having": "ing"}
DO_FORMS = {"do": "present", "does": "present", "did": "past"}

# Modal verbs: word -> meaning label used by the transfer rules
MODALS = {
    "will": "future", "shall": "future", "would": "conditional",
    "can": "ability", "could": "ability", "may": "possibility",
    "might": "possibility", "must": "obligation", "should": "obligation",
}

NEGATIVES = {"not", "never"}

PREPOSITIONS = {
    "in", "on", "at", "to", "from", "with", "by", "for", "of", "into",
    "behind", "near", "under", "between", "about", "after", "before",
    "through", "towards", "without", "inside", "outside", "like",
}

# Words that join two clauses of equal rank (C13)
COORDINATORS = {"and", "but", "or", "so", "yet"}

# Words that start a subordinate clause (C14), with a label for the transfer rules
SUBORDINATORS = {
    "because": "reason", "if": "condition", "when": "time",
    "while": "time-during", "although": "concession", "though": "concession",
    "since": "reason", "unless": "negative-condition", "before": "time-before",
    "after": "time-after", "until": "time-until",
}

# Question words: word -> what is being asked about
WH_WORDS = {
    "who": "person", "whom": "person", "what": "thing", "which": "choice",
    "where": "place", "when": "time", "why": "reason", "how": "manner",
    "whose": "owner",
}

# Words that can start a relative clause after a noun (C15)
RELATIVE_WORDS = {"who", "whom", "which", "that", "whose"}

# Verbs that can be followed by "that" + a whole clause (C16)
SAY_THINK_VERBS = {"say", "know", "think", "believe", "hear", "tell", "see", "hope", "claim", "feel"}

# Small words that turn a verb into a phrasal verb: "stand up", "go out"
PARTICLES = {"up", "down", "out", "away", "back", "off", "in"}
PHRASAL_VERBS = {
    "stand up", "sit down", "go out", "pick up", "wake up", "give up",
    "come back", "go back", "turn off", "turn on", "run away", "come in",
}

# Adverbs of place, time and manner that are single words
ADVERBS = {
    "yesterday", "today", "tomorrow", "now", "early", "late", "already",
    "again", "always", "often", "sometimes", "soon", "here", "there",
    "inside", "outside", "indoors", "outdoors", "south", "north",
    "east", "west", "very", "too", "also", "hard", "well", "please", "loudly",
    "bitterly", "beautifully", "proudly", "consistently", "quickly", "slowly",
    "earlier", "later", "together", "everywhere",
}

# Possessive pronouns used alone: "The book is mine" -> Littafin nawa ne
POSSESSIVE_PRONOUNS = {"mine": ("1", "sg"), "yours": ("2", "sg"), "hers": ("3", "sg"),
                       "ours": ("1", "pl"), "theirs": ("3", "pl")}

# Pronouns that can only be a subject: the next word is a verb ("They hate ...")
SUBJECT_PRONOUN_WORDS = {"i", "you", "he", "she", "we", "they"}

# Time words that can be the subject of "be": "Today is Friday", "Tomorrow will be hot"
TIME_WORDS = {"today", "tomorrow", "yesterday", "tonight"}

# Multi-word expressions treated as one unit: written form -> label
MULTIWORD = {
    "every day": "ADV", "every week": "ADV", "every morning": "ADV",
    "last year": "ADV", "last week": "ADV", "last night": "ADV",
    "next year": "ADV", "next week": "ADV", "this morning": "ADV",
    "this evening": "ADV", "on time": "ADV", "a lot": "ADV",
    "going to": "FUTURE",
}

# Indefinite pronouns: word -> (person, number, negative?)
INDEFINITES = {
    "everyone": ("3", "sg", False), "everybody": ("3", "sg", False),
    "someone": ("3", "sg", False), "somebody": ("3", "sg", False),
    "anyone": ("3", "sg", False), "anybody": ("3", "sg", False),
    "nobody": ("3", "sg", True), "no one": ("3", "sg", True),
    "everything": ("3", "sg", False), "something": ("3", "sg", False),
    "anything": ("3", "sg", False), "nothing": ("3", "sg", True),
}

# ===== 2. Irregular English forms =====

# Irregular verbs: base -> (past, past participle)
IRREGULAR_VERBS = {
    "be": ("was", "been"), "have": ("had", "had"), "do": ("did", "done"),
    "go": ("went", "gone"), "come": ("came", "come"), "eat": ("ate", "eaten"),
    "see": ("saw", "seen"), "buy": ("bought", "bought"), "bring": ("brought", "brought"),
    "take": ("took", "taken"), "give": ("gave", "given"), "make": ("made", "made"),
    "say": ("said", "said"), "tell": ("told", "told"), "know": ("knew", "known"),
    "think": ("thought", "thought"), "find": ("found", "found"), "get": ("got", "got"),
    "sit": ("sat", "sat"), "stand": ("stood", "stood"), "run": ("ran", "run"),
    "win": ("won", "won"), "lose": ("lost", "lost"), "leave": ("left", "left"),
    "meet": ("met", "met"), "send": ("sent", "sent"), "spend": ("spent", "spent"),
    "read": ("read", "read"), "write": ("wrote", "written"), "speak": ("spoke", "spoken"),
    "break": ("broke", "broken"), "steal": ("stole", "stolen"), "teach": ("taught", "taught"),
    "catch": ("caught", "caught"), "begin": ("began", "begun"), "sing": ("sang", "sung"),
    "drink": ("drank", "drunk"), "sleep": ("slept", "slept"), "fly": ("flew", "flown"),
    "grow": ("grew", "grown"), "hear": ("heard", "heard"), "keep": ("kept", "kept"),
    "put": ("put", "put"), "cut": ("cut", "cut"), "hit": ("hit", "hit"),
    "become": ("became", "become"), "feel": ("felt", "felt"), "lead": ("led", "led"),
    "hold": ("held", "held"), "pay": ("paid", "paid"), "sell": ("sold", "sold"),
    "understand": ("understood", "understood"), "forget": ("forgot", "forgotten"),
    "fall": ("fell", "fallen"), "drive": ("drove", "driven"), "wear": ("wore", "worn"),
    "choose": ("chose", "chosen"), "swim": ("swam", "swum"), "throw": ("threw", "thrown"),
    "build": ("built", "built"), "feed": ("fed", "fed"), "fight": ("fought", "fought"),
    "seek": ("sought", "sought"), "mean": ("meant", "meant"), "wake": ("woke", "woken"),
    "let": ("let", "let"), "lend": ("lent", "lent"), "light": ("lit", "lit"),
    "shut": ("shut", "shut"), "ride": ("rode", "ridden"), "rise": ("rose", "risen"),
    "show": ("showed", "shown"), "hide": ("hid", "hidden"), "bite": ("bit", "bitten"),
    "sweep": ("swept", "swept"), "flee": ("fled", "fled"), "weep": ("wept", "wept"), "shoot": ("shot", "shot"),
    "dig": ("dug", "dug"), "hang": ("hung", "hung"), "bend": ("bent", "bent"),
}

# Irregular plurals: plural -> singular
IRREGULAR_PLURALS = {
    "children": "child", "men": "man", "women": "woman", "people": "person",
    "feet": "foot", "teeth": "tooth", "mice": "mouse", "wives": "wife",
    "knives": "knife", "lives": "life", "leaves": "leaf", "elders": "elder",
}

# Things there is only one of. English says "the"; Hausa has no -n/-r.
UNIQUE_NOUNS = {"rain", "sun", "moon", "sky", "weather", "light", "electricity", "world"}

# Nouns that have the same form in singular and plural
UNCOUNTABLE = {"rice", "water", "money", "food", "bread", "meat", "tea", "milk",
               "sheep", "fish", "news", "work", "homework", "music", "weather",
               "rain", "linguistics", "information", "advice", "furniture"}

# ===== 3. Names and the sex of people words =====
# Person names used in our test sentences. More names are read from the
# lexicon file data/lexicon/names.csv.
NAMES = {
    "ada": "f", "chika": "f", "ngozi": "f", "amina": "f", "aisha": "f",
    "musa": "m", "chinedu": "m", "audu": "m",
}
PLACE_NAMES = {"lagos", "kano", "abuja", "kaduna", "ibadan", "nigeria"}

# English nouns whose referent has a known sex (helps choose ya/ta, malami/malama)
FEMALE_NOUNS = {"girl", "woman", "mother", "sister", "wife", "daughter", "aunt",
                "queen", "grandmother", "lady", "mum", "mom"}
MALE_NOUNS = {"boy", "man", "father", "brother", "husband", "son", "uncle",
              "king", "grandfather", "gentleman", "dad"}

# ===== 4. Content words not (yet) in the lexicon =====
# These tell the analysis the word class. The Hausa translation still has to
EXTRA_NOUNS = {
    "bakery", "bird", "candle", "complaint", "fan", "light", "linguistics",
    "meal", "music", "player", "recommendation", "road", "seat", "wrapper",
    "student", "plate", "book", "pencil", "morning", "assignment", "lecturer",
    "problem", "accident", "uncle", "village", "window", "phone", "gift",
}
EXTRA_VERBS = {
    "apologize", "apologise", "applaud", "belong", "cheer", "continue", "cry",
    "enjoy", "fetch", "flood", "fly", "laugh", "lead", "live", "own", "pass",
    "remain", "repair", "request", "retire", "save", "smile", "solve", "spill",
    "start", "stay", "study", "submit", "succeed", "surprise", "travel", "use",
    "visit", "admire", "cause", "clean", "close", "enter", "finish", "open",
    "play", "prepare", "rain", "stop", "want", "wash", "call", "carry", "invite",
    "praise", "help", "arrive", "borrow", "cook", "like", "frighten", "attend",
}
EXTRA_ADJECTIVES = {
    "hungry", "thirsty", "sleepy", "careful", "quiet", "ready", "sick", "important", "interesting",
    "angry", "classical", "cloudy", "cold", "dangerous", "delicious",
    "difficult", "fascinating", "good", "happy", "hot", "loud", "narrow",
    "proud", "upset", "windy", "honest", "big", "small", "new", "old", "red",
    "heavy", "tired", "missing", "beautiful", "bad", "long", "short",
}
