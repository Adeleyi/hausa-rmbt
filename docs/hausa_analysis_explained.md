# Hausa analysis, explained

The Hausa analysis is stage 1 of the **Hausa → English** system. It reads a Hausa sentence and labels every part of it, so that the transfer rules (stage 2) can build the English sentence.

It uses the same knowledge as the English → Hausa system: the PAC table, pronouns, suffixes and verb forms in the lexicon. Here that knowledge is used **backwards**, to *read* Hausa instead of *writing* it.

## Why reading Hausa is hard

Written Hausa does not show tone or vowel length. One written form can therefore have several readings, and the program has to choose one from the words around it:

| Written | Possible readings | How the program decides |
| --- | --- | --- |
| *ta* | she (completive) · she (subjunctive) · her (object) · of (feminine) | Before a verb it is a PAC. After a verb it is an object. In *ta X ne/ce* it is "of". |
| *na* | I (completive) · of (masculine) | *na X ne/ce* at the end of the sentence means "belongs to X". |
| *ina* | I (continuous) · where? | It means "where" in a question when a noun follows. |
| *da* | and · with · relative "who/that" · counterfactual "if" | After a noun with *-n/-r* + a clause it starts a relative clause. After a continuous PAC it means "have". At the start of two clauses it marks a counterfactual. |
| *yaran* | the children · children of … | If another noun follows, it means "of": *gidan Musa*. |
| *ba ta* | negative completive · negative continuous | If the clause ends in *ba*, it is the completive (*ba ta … ba*). |

## Files

| File | What it is | Who edits it |
| --- | --- | --- |
| `src/hausa_words.py` | Small word lists for reading Hausa: linkers, question words, prepositions, adverbs, quantifiers, and which English word to prefer | Linguists |
| `src/hausa_analysis.py` | The rules that read Hausa | Coders |
| `src/run_analysis.py` | Runs the analysis on all 128 test sentences, checks it, writes a report | Nobody (just run it) |
| `outputs/hausa_analysis_report.txt` | The report | Created automatically |

Everything else is read from the lexicon workbook: nouns with their plurals and *-n/-r* forms, every verb form, adjectives, PAC forms, pronouns and possessive suffixes.

## How to run it

One sentence:

```
python src/try_sentence.py --hausa --analysis "Musa bai halarci taron ba."
```

All test sentences, with the check:

```
python src/run_analysis.py
```

## What the output looks like

```
Sentence: Musa bai halarci taron ba.
  Clause 1: main - statement - verbal
    subject:      Musa  [name | English: Musa | 3sg.m]
    PAC:          bai  [3sg.m | negative completive]
    verb:         halarci  [Hausa: halarta | English: attend | form: before_noun]
    object:       taron  [noun | English: meeting | 3sg.m | the]
    negative:     yes
```

Each label is there because an English rule needs it:

| Label | English rule that uses it |
| --- | --- |
| PAC: negative completive | past tense + *did not*: "did not attend" |
| PAC: 3sg.m, subject shown only by the PAC | the English pronoun: "he" |
| verb: Hausa *halarta*, form *before_noun* | *halarci* is traced back to *halarta* = "attend" |
| object: *the* | *taron* = *taro* + *-n* → "the meeting" |
| owner: 1sg | *motata* = *mota* + *-ta* → "my car" |

## The four steps

### Step 1: words and fixed expressions

The sentence is split into words. Fixed expressions become one unit: *abincin dare* (dinner), *lokacin da* (when), *da wuri* (early), *ci gaba da* (continue), *'yan wasa* (players). The last word may carry *-n/-r*: *abincin daren*, *aikin gidan*.

### Step 2: every possible reading of each word

The lexicon is read backwards. Every form points to its word:

| Written | Read as |
| --- | --- |
| *sayi*, *saye*, *sayen* | *saya* "buy" (before a noun / before a pronoun / verbal noun) |
| *yaran* | *yara* (plural of *yaro*) + "the" |
| *ɗaliban* | *ɗalibai* + "the" (plurals in *-ai* drop the *-i*) |
| *motata* | *mota* + "my" |
| *mahaifiyarta* | *mahaifiya* + "her" |
| *babban*, *jar* | *babba* "big", *ja* "red" before a noun |
| *dariya* after *yi* | the yi-verb "laugh" |

One rule from Hausa grammar removes wrong readings: a feminine noun in *-a* takes *-r* for "the", never *-n*. So *ɗaliban* cannot be *ɗaliba* (a female student) + "the".

### Step 3: splitting into clauses

The sentence is cut:
- at commas
- at *kuma / amma / don haka*
- at *idan, lokacin da, yayin da, saboda, ko da yake, tun da, sai dai idan, kafin, har*
- at *cewa*

*Da …, da …* at the start of two clauses marks a counterfactual.

Relative clauses stay inside their noun phrase. Reported clauses stay inside their main clause.

### Step 4: inside each clause — the PAC is the anchor

The program first looks for special patterns:
1. *akwai / babu* → there is / there is no
2. a question word first → *Me Musa ya saya?*
3. X + *ne/ce* + a clause → focus: *Ada ce ta dafa miyar*
4. a clause that ends in *ne/ce* with no PAC → *Ada malama ce*, *Littafin na Musa ne*, *Motata sabuwa ce*
5. *ba* + pronoun + *da* → *Ba ni da mota*
6. no PAC, starts with a verb → a command: *Zauna.*

Otherwise it finds the **PAC**:
- Everything before it is the **subject**.
- If there is nothing before it, the PAC alone shows the subject (*Sun tsabtace ajin*).

After the PAC:

| After a continuous PAC | Meaning | Example |
| --- | --- | --- |
| *da* + quality noun | is + adjective | Miyar tana **da zafi** (is hot) |
| *da* + noun | has | Ada tana **da mota** |
| quality noun | is + adjective | Yaran suna **farin ciki** (are happy) |
| place | is in / at | Yaran suna **cikin gida**, Musa yana **kasuwa** |
| weather noun (impersonal *ana*) | weather | **Ana ruwa** (it is raining) |

| After any PAC | Meaning | Example |
| --- | --- | --- |
| *yi* + yi-verb noun | that verb | ya **yi dariya** (laughed) |
| *yi* + quality noun | became + adjective | ya **yi fushi** |
| *iya* + verb | can | ta **iya** iyo |
| *taɓa* + verbal noun | ever / never | ban **taɓa** ganin … ba |
| verb + *wa* + noun | receiver | ya aika **wa ɗaliban** saƙo |
| *ba* + noun + noun | give X Y | ya ba **Ada** **littafi** |
| *ba* + noun + *mamaki* | surprise X | ya ba ɗaliban **mamaki** |
| a final *ba* | negative | bai halarci taron **ba** |

**Relative clauses:** noun-*n/-r* + *da* + clause. If the PAC agrees with the noun, the noun is the missing subject (*Mutumin da **ya** kira jiya*). If not, it is the missing object (*Matar da **muka** ziyarta*). If the owner suffix or *masa* points back to the noun, it is *whose* (*Yarinyar da mahaifi**nta** likita ne*).

## The check against the English sentences

Every Hausa test sentence has an English partner, so `run_analysis.py` compares the Hausa analysis with the English analysis of the same sentence:

| Agreement on | Result |
| --- | --- |
| negation | 128/128 |
| sentence type (statement / question / command) | 128/128 |
| number of clauses | 128/128 |
| main verb | 109/128 |

The 19 verb differences are not reading errors. The Hausa verb was found correctly every time, but it has several English meanings, and the first one in the lexicon is not the one in the English sentence:

- *ci*: eat / pass / win
- *zauna*: sit / live / stay
- *so*: want / like
- *tashi*: stand up / fly

Choosing the right meaning from the context (*ci* + *jarrabawa* → pass) is a job for the transfer stage. A few are free translations by the speaker: *shiga ciki da gudu* for "ran inside", *share* (sweep) for "clean".

## Known limitations

- Three words are not in the lexicon: *dage* (persist), *cika* (fill), *jaririya* (baby girl). The report flags them.
- The English word chosen for a Hausa word is the first row in the lexicon, unless `PREFERRED_ENGLISH` in `hausa_words.py` says otherwise. The final choice by context comes in the transfer stage.
- *ka / ki* tell us the sex of "you", but English does not show it, so nothing is lost there. In the other direction, Hausa *ya* often stands for "it" (a masculine thing); the transfer stage must decide between "he" and "it".
- Spelling must follow the lexicon: hooked letters (ɓ ɗ ƙ), *'y*, no tone marks.

## How to fix a wrong analysis

1. Find the sentence in the report and see which word has the wrong reading.
2. A word missing or with the wrong English: fix the lexicon, or add it to `PREFERRED_ENGLISH` in `hausa_words.py`.
3. A linker, question word, adverb or preposition missing: add it to `hausa_words.py`.
4. The structure is wrong although every word is right: tell the coder; a rule in `hausa_analysis.py` needs changing.
5. Run `python src/run_analysis.py` again and check that the agreement figures did not go down.
