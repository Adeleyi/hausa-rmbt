# English analysis, explained

The English analysis is stage 1 of our transfer system. It reads an English sentence and labels every part of it, so that the transfer rules (stage 2) can build the Hausa sentence.

## Files

| File | What it is | Who edits it |
| --- | --- | --- |
| `src/english_words.py` | Word lists: pronouns, auxiliaries, irregular verbs, names, and so on | Linguists |
| `src/english_analysis.py` | The rules that do the analysis | Coders |
| `src/run_analysis.py` | Runs the analysis on all test sentences and writes a report | Nobody (just run it) |
| `outputs/english_analysis_report.txt` | The report for every test sentence | Created automatically |

## How to run it

One sentence:

```
python src/try_sentence.py --analysis "The girls did not eat the rice."
```

All test sentences:

```
python src/run_analysis.py
```

## What the output looks like

```
Sentence: The girls did not eat the rice.
Words:    The/DET  girls/NOUN  did/DO  not/NEG  eat/VERB  the/DET  rice/NOUN
  Clause 1: main - statement
    subject:      The girls  [noun | base: girl | 3rd | plural | female | definite]
    verb:         did not eat  [base: eat | past | simple | negative]
    object:       the rice  [noun | base: rice | 3rd | singular | definite]
```

Each label is there because a Hausa rule needs it:

| Label | Hausa rule that uses it |
| --- | --- |
| subject: 3rd, plural | PAC row: *su* forms |
| verb: past, negative | PAC column: negative completive, *ba su … ba* (S4) |
| base: eat, base: girl | Lexicon look-up (the lexicon has "eat", not "ate") |
| definite | *-n / -r* suffix for "the" (A6) |
| object | Verb form before a noun object (B6) |
| female / male | *malami / malama*; *ya / ta* with names |

## The four steps

### Step 1: clean-up

Contractions are expanded and punctuation is split off.
*didn't* → *did not*, *can't* → *can not*, *Musa's* → *Musa* + *'s*.
Fixed expressions such as *every day* and *last year* become one unit.

### Step 2: word classes and base forms

Each word gets a class (tag) and a base form.

| Tag | Meaning | Example |
| --- | --- | --- |
| NOUN | noun | girls (base: girl) |
| NAME | person or place name | Ada, Lagos |
| PRON | pronoun | she, them |
| VERB | main verb | ate (base: eat) |
| BE, HAVE, DO, MODAL | helper verbs | is, has, did, will |
| NEG | not, never | not |
| DET, DEM, POSS | the/a, this/that, my/your | the |
| ADJ | adjective | red |
| ADV | adverb | yesterday |
| PREP | preposition | in, on, to |
| COORD | and, but, or, so | and |
| SUB | because, if, when, while ... | because |
| REL | who/which/that starting a relative clause | who |
| COMP | "that" starting a reported clause | that |
| WH | question word | what |

Where a word has more than one possible class, the words around it decide. For example, *cook* is a noun after *the* ("the cook smiled") and a verb after a name ("Ada cooked dinner").

Base forms come from the irregular lists (*went* → go, *children* → child) or from ending rules (*stopped* → stop, *babies* → baby).

### Step 3: splitting into clauses

The sentence is cut at commas, at *and/but/so/or* when a new subject and verb follow, and at *because/if/when/while/although/since/unless*. Each piece is labelled main, coordinated or subordinate, with its linking word.

Relative clauses (*the man who called*) stay inside their noun phrase. Reported clauses (*I know that she left*) stay inside their main clause.

### Step 4: inside each clause

The program looks for, in order:

1. Special patterns: focus (*It was Ada who …*), commands (*Sit down.*), questions (*Did …?*, *What …?*), *there is*.
2. The subject: the first noun phrase.
3. The verb group: helpers plus the main verb. From it come tense (past, present, future), aspect (simple, progressive, perfect), negation, modal (can, may) and passive.
4. What follows the verb: objects, the receiver (*gave **Ada** a book*), complements after *be* (*is **a teacher***, *is **happy***, *is **in the house***), places and times.

In questions, the helper verb is moved back after the subject before step 4: *What did Musa buy?* is treated as *Musa did buy what*.

## Results on the test set

All 128 test sentences are analysed with no problems flagged. "No problems flagged" means every clause has a subject and a verb; it does not prove every label is right. Read the report and log anything wrong in the errors log of the working doc.

## Known limitations

- "you" is always singular and of unknown sex; the transfer stage uses the masculine default (A2/B11).
- A past participle is read as an adjective only if it is in the Adjectives tab (*flooded* is, so *were flooded* is *be* + adjective). Otherwise *were* + participle is read as a passive.
- Weather *it* (*It is raining*) is analysed as a normal subject; the transfer stage must turn it into impersonal *ana*.
- A word not in any list is guessed from its ending and position. If the report shows a wrong tag, add the word to the right list in `english_words.py`.

## How to fix a wrong analysis

1. Find the sentence in the report and see which word has the wrong tag or base form.
2. If a word is missing or in the wrong list, edit `english_words.py` (no coding needed).
3. If the structure is wrong although every tag is right, tell the analysis engineer: a rule in `english_analysis.py` needs changing.
4. Run `python src/run_analysis.py` again and check that other sentences did not break.
