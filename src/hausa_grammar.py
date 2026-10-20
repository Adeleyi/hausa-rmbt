"""Hausa grammar tables and group decisions used by English -> Hausa (transfer_en_ha.py).

This file is DATA, not program logic. Linguists can edit it freely.

Hausa WORDS (PAC forms, pronouns, possessive suffixes, numbers, nouns, verbs)
live in the lexicon workbook. This file holds the CHOICES for English -> Hausa: which Hausa
preposition stands for which English one, which tense uses which PAC column,
and the decisions recorded in the working doc (A2, A6, A7, A17 ...).
"""

# ---------------------------------------------------------------------------
# 1. Group decisions (see the working doc). Change a value to change the rule.
# ---------------------------------------------------------------------------

# A2/B11: when English does not show the sex (you, the teacher), use masculine.
DEFAULT_SEX = "m"

# A6: "the" becomes -n/-r (yaron, miyar). Our speaker leaves it off after a
# preposition (cikin gida, a kasuwa, a kan tebur), so we do too.
DEFINITE_AFTER_PREPOSITION = False

# A7: a real adjective goes before the noun with a linker: babban gida.
ADJECTIVE_BEFORE_NOUN = True

# A17: the noun stays singular after a number: fensir biyu (not fensiroshi biyu).
SINGULAR_AFTER_NUMBER = True

# Subject pronouns are left out; the PAC already shows the person (Sun tsabtace ajin).
DROP_SUBJECT_PRONOUNS = True

# "is at the market": the preposition a is left out after a continuous PAC
# (Musa yana kasuwa), but cikin, kusa da, bayan ... stay (Yaran suna cikin gida).
DROP_A_IN_LOCATIVE = True

# A noun with no plural in the lexicon (wutar lantarki, kyandir) is treated as
# singular in Hausa, even when the English is plural. Fill in the plural if that is wrong.
NO_PLURAL_MEANS_SINGULAR = True

# A comma before kuma / amma / don haka when two clauses are joined (C13):
# Ada ta dafa abincin dare, kuma Chinedu ya wanke kwanukan.
COMMA_BEFORE_COORDINATOR = True

# ---------------------------------------------------------------------------
# 2. Which PAC column each English tense uses
# ---------------------------------------------------------------------------
# (English tense, English aspect) -> PAC column in the lexicon "Function words" tab.
# English simple present describes habits ("Birds fly south"), and Hausa uses
# the continuous for habits: Tsuntsaye suna tashi.
PAC_COLUMN = {
    ("past", "simple"): "completive",
    ("past", "perfect"): "completive",
    ("present", "perfect"): "completive",
    ("present", "simple"): "continuous",
    ("present", "progressive"): "continuous",
    ("past", "progressive"): "continuous",
    ("future", "simple"): "future",
    ("future", "progressive"): "future",
    ("future", "perfect"): "future",
}
# The negative columns used when the English sentence is negative.
NEGATIVE_COLUMN = {
    "completive": "negative completive",
    "continuous": "negative continuous",
    "future": "future",          # negative future = ba + future PAC ... ba (Ba zan tafi ba)
}

# ---------------------------------------------------------------------------
# 3. Prepositions
# ---------------------------------------------------------------------------
PREPOSITIONS = {
    "in": "a", "at": "a", "on": "a kan", "to": "zuwa", "towards": "zuwa",
    "from": "daga", "with": "da", "near": "kusa da", "behind": "bayan",
    "under": "ƙarƙashin", "between": "tsakanin", "into": "cikin", "inside": "cikin",
    "outside": "wajen", "for": "don", "about": "game da", "like": "kamar",
    "after": "bayan", "before": "kafin", "without": "ba tare da", "through": "ta",
}
# "in" + one of these nouns -> cikin (inside a container): cikin gida
INSIDE_NOUNS = {"house", "room", "classroom", "car", "box", "bag", "pot", "bus",
                "cup", "bottle", "water", "hall", "shop", "kitchen"}
# After these verbs, "to" + place has no preposition: Za mu tafi kasuwa.
MOTION_VERBS = {"go", "come", "return", "run", "walk", "travel", "move"}

# ---------------------------------------------------------------------------
# 4. Adverbs and time expressions (looked up here first, then in the lexicon)
# ---------------------------------------------------------------------------
ADVERBS = {
    "today": "yau", "tomorrow": "gobe", "yesterday": "jiya", "now": "yanzu",
    "every day": "kullum", "always": "kullum", "early": "da wuri", "late": "a makare",
    "here": "nan", "there": "can", "outside": "a waje", "inside": "a ciki",
    "outdoors": "a waje", "indoors": "a cikin gida",
    "south": "zuwa kudu", "north": "zuwa arewa", "east": "zuwa gabas", "west": "zuwa yamma",
    "this morning": "da safiyar yau", "this evening": "da yammacin yau",
    "last night": "jiya da dare", "last week": "makon da ya wuce", "next week": "mako mai zuwa",
    "last year": "bara", "next year": "baɗi", "every week": "kowane mako",
    "every morning": "kowace safiya", "on time": "a kan lokaci",
    "very": "sosai", "a lot": "sosai", "too": "ma", "also": "ma", "together": "tare",
    "quickly": "da sauri", "slowly": "a hankali", "please": "don Allah",
    "hard": "sosai", "well": "da kyau", "beautifully": "da kyau", "loudly": "da ƙarfi",
    "already": "tuni", "again": "kuma", "still": "har yanzu", "soon": "nan ba da jimawa ba",
    "bitterly": "sosai", "earlier": "da wuri", "proudly": "cike da alfahari",
    "consistently": "akai-akai", "regularly": "akai-akai",
}
# After a motion verb, these adverbs lose the "a": sun so su tafi waje
MOTION_ADVERBS = {"outside": "waje", "inside": "ciki", "home": "gida", "indoors": "cikin gida"}

# ---------------------------------------------------------------------------
# 5. Quantifiers and indefinite pronouns
# ---------------------------------------------------------------------------
# quantifier -> (Hausa word, goes "before" or "after" the noun, noun number)
QUANTIFIERS = {
    "many": ("da yawa", "after", "pl"), "a lot of": ("da yawa", "after", "pl"),
    "some": ("wasu", "before", "pl"), "several": ("wasu", "before", "pl"),
    "few": ("kaɗan", "after", "pl"), "all": ("duk", "before", "pl"),
    "every": ("kowane", "before", "sg"), "each": ("kowane", "before", "sg"),
    "enough": ("isasshen", "before", "sg"),
}
# quantifier forms that agree with the noun: kowane/kowace; isasshen/isasshiyar/isassun
AGREEMENT = {"kowane": {"f": "kowace"},
             "isasshen": {"f": "isasshiyar", "pl": "isassun"}}
# "more", "much" used alone (kowa ya nemi ƙari)
QUANTITY_WORDS = {"more": "ƙari", "much": "da yawa", "many": "da yawa", "enough": "isasshe"}

INDEFINITES = {
    "everyone": "kowa", "everybody": "kowa", "anyone": "wani", "anybody": "wani",
    "someone": "wani", "somebody": "wani", "everything": "komai", "anything": "wani abu",
    "something": "wani abu", "nothing": "komai", "nobody": "kowa", "no one": "kowa",
}
# In a negative sentence "anyone/anything" become kowa/komai: Ban ga kowa ba. Ban taɓa ganin komai ba.
NEGATIVE_INDEFINITES = {"anyone": "kowa", "anybody": "kowa", "anything": "komai"}
# "Nobody came" -> Ba wanda ya zo (ba wanda + relative completive PAC)
NOBODY_SUBJECT = "ba wanda"

# ---------------------------------------------------------------------------
# 6. Special verbs and constructions
# ---------------------------------------------------------------------------
# Verbs that describe a state use the completive in the simple present:
# Na san cewa ... (I know), Musa ya yarda cewa ... (Musa believes), hanyar da ta kai ƙauyen
STATIVE_VERBS = {"know", "believe", "understand", "agree", "remember", "forget", "lead", "mean"}
# Feelings use the continuous even in the simple past: ɗaliban suke girmamawa (admired)
FEELING_VERBS = {"admire", "respect", "love", "like", "hate", "fear"}
# After these verbs "to X" is an object: hanyar da ta kai ƙauyen
TO_AS_OBJECT = {"lead", "reach"}
# English verbs that mean "have": Ada tana da mota
POSSESSION_VERBS = {"have", "own", "possess"}
# Hausa verbs that take the receiver directly, without "wa": ya ba Ada littafi
VERBS_WITHOUT_WA = {"ba"}
# English modal "can/could" -> iya + verbal noun: Ada ta iya iyo
ABILITY_VERB = "iya"
# English "never" -> taɓa + verbal noun: Ban taɓa ganin komai ba
NEVER_VERB = "taɓa"

# English modal -> Hausa word placed before a subjunctive PAC: Dole ne ka tafi
MODAL_BEFORE_SUBJUNCTIVE = {"obligation": "dole ne"}
# "would" (not in a counterfactual) uses the future PAC: Me ya sa wani zai yi haka?
CONDITIONAL_COLUMN = "future"
# "do that / do this" -> yi haka
DO_THAT = "haka"
# "remain / stay + adjective" = "still be + adjective": suna cike da ruwa har yanzu
# ("still" is translated through ADVERBS above)
REMAIN_VERBS = {"remain", "stay"}

# ---------------------------------------------------------------------------
# 7. Questions (C11, C12)
# ---------------------------------------------------------------------------
# Yes/no questions (C11) keep the statement word order: Musa ya iso?
# "Can you ...?" is a request and uses the future: Za ka iya taimake ni?
ABILITY_QUESTION_COLUMN = "future"
# "already" in a question goes first as har: Har za ka tafi?
ALREADY_IN_QUESTION = "har"

# Question words (C12) go first, and the PAC changes to its relative form:
#   completive -> relative completive (Me Musa ya saya? Ina yaran suka tafi?)
#   continuous -> relative continuous (Me ya sa jaririn yake kuka?)
QUESTION_WORDS = {
    "who": "wa", "whom": "wa", "what": "me", "where": "ina", "when": "yaushe",
    "why": "me ya sa", "how": "yaya",
}
# "which" + noun: wane (masc.) / wace (fem.) / waɗanne (plural), then ne/ce
WHICH = {"m": "wane", "f": "wace", "pl": "waɗanne"}
# "What is X?" / "Who is X?" -> Mene ne X? / Wane ne X?
WHAT_IS, WHO_IS = "mene ne", "wane ne"
RELATIVE_COLUMN = {"completive": "relative completive", "continuous": "relative continuous",
                   "future": "future", "subjunctive": "subjunctive"}

# ---------------------------------------------------------------------------
# 8. Commands (imperatives)
# ---------------------------------------------------------------------------
# A plain command is the bare verb: Zauna. Kawo littattafan nan.
# With "please" it is Don Allah + subjunctive PAC: Don Allah ka rufe ƙofar.
# A negative command is kada + subjunctive PAC: Kada ka taɓa wancan.
PLEASE = "don Allah"
NEGATIVE_COMMAND = "kada"

# ---------------------------------------------------------------------------
# 9. Joining clauses (C13, C14) and reported clauses (C16)
# ---------------------------------------------------------------------------
# A subordinate clause that comes first is followed by a comma:
# Saboda ya yi karatu sosai, ya ci jarrabawar.
COMMA_AFTER_SUBORDINATE = True

# Some linkers decide the PAC of their clause (when the English is a simple tense):
#   linker -> (Hausa linker, PAC column, relative form?)
SUBORDINATE_PAC = {
    "when (past)": ("lokacin da", "completive", True),   # Lokacin da ruwan sama ya fara
    "when": ("idan", "completive", False),               # When you come -> Idan ka zo
    "while": ("yayin da", "continuous", True),           # Yayin da jaririn yake barci
    "if": ("idan", "completive", False),                 # Idan ka gama da wuri
    "unless": ("sai dai idan", "completive", False),     # Sai dai idan ka ba da haƙuri
    "before": ("kafin", "subjunctive", False),           # kafin ruwan sama ya fara
    "until": ("har", "subjunctive", False),              # har ka zo
    "after": ("bayan", "completive", True),              # bayan ya tafi
}
# The main clause after a past "when" clause also takes the relative completive:
# Lokacin da malamin ya shiga ajin, ɗaliban suka tashi tsaye.
RELATIVE_AFTER_PAST_WHEN = True
# Counterfactual (If X had ..., Y would have ...): da + completive in both clauses
# Da Ngozi ta iso da wuri, da ta haɗu da malamin.
COUNTERFACTUAL = "da"

# Reported clauses: verb + cewa + clause (Na san cewa ta tafi).
COMPLEMENTISER = "cewa"
# "say" + clause is ce, without cewa: Malamin ya ce jarrabawar tana da wuya.
REPORT_VERBS = {"say": "ce"}
# "tell X that ..." -> X is the receiver: Musa ya faɗa mini cewa ...
TELL_VERBS = {"tell", "inform", "show", "promise", "remind"}

# Infinitive: "wanted to go" -> sun so su tafi (subjunctive PAC + verb)

# Relative clauses (C15): noun + -n/-r + da + relative PAC: Mutumin da ya kira jiya
RELATIVE_MARKER = "da"
CLAUSE_LINKERS = {
    "and": "kuma", "but": "amma", "or": "ko", "so": "don haka", "yet": "amma",
    "because": "saboda", "if": "idan", "when": "lokacin da", "while": "yayin da",
    "although": "ko da yake", "though": "ko da yake", "since": "tun da",
    "unless": "sai dai idan", "before": "kafin", "after": "bayan", "until": "har",
}

# ---------------------------------------------------------------------------
# 10. Place names that are spelled differently in Hausa
# ---------------------------------------------------------------------------
PLACE_NAMES = {"lagos": "Legas", "nigeria": "Najeriya", "london": "Landan"}

# ---------------------------------------------------------------------------
# 11. Weather
# ---------------------------------------------------------------------------
# Hausa has no dummy "it". Weather uses the impersonal PAC: Ana ruwa, An yi iska.
# english word -> (Hausa noun, Hausa subject or None for impersonal)
WEATHER = {
    "rain": ("ruwa", None), "cold": ("sanyi", None), "hot": ("zafi", None),
    "windy": ("iska", None), "sunny": ("rana", None), "cloudy": ("gajimare", "sama"),
}
WEATHER_SUBJECTS = {"it", "weather"}
