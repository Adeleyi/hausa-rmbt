# Hausa → English, explained

The Hausa → English system has the same three stages as English → Hausa:

| Stage | File | What it does |
| --- | --- | --- |
| 1. Hausa analysis | `hausa_analysis.py` | reads the Hausa sentence (see `hausa_analysis_explained.md`) |
| 2. Transfer | `transfer_ha_en.py` | decides the English tense, the English verb, *a/the*, word order |
| 3. English generation | `english_generate.py` | writes the words: *bought*, *did not buy*, *is cooking*, *children*, *an* |

The choices the linguists can change are in `english_grammar.py`.

## How to run it

```
python src/try_sentence.py --hausa              type Hausa, see the English
python src/try_sentence.py --hausa --rules      also show the rules used
python src/try_sentence.py --hausa --analysis   also show the Hausa analysis
python src/evaluate.py --hausa                  score all 128 test sentences
```

## A worked example

With `python src/try_sentence.py --hausa --rules`:

```
Hausa>   Musa bai halarci taron ba.
English: Musa did not attend the meeting.
Rules used:
  - Verb: halarci = halarta -> attend
  - PAC bai (3sg.m, negative completive) -> English past simple
  - -n/-r (or ɗin) -> the meeting
```

| Stage | What happens |
| --- | --- |
| Analysis | subject Musa · PAC *bai* = negative completive · *halarci* = *halarta* "attend" · *taron* = *taro* + "the" |
| Transfer | negative completive → past simple, negative · object definite → *the* |
| Generation | past + negative → *did not* + base verb: **Musa did not attend the meeting.** |

## What Hausa does not show, and the default the system uses

Hausa and English mark different things. Where English needs something Hausa does not say, the system uses a default. Every default is in `english_grammar.py`.

### Tense (`TENSE`)

| Hausa PAC | English default | Example | Overridden when |
| --- | --- | --- | --- |
| completive | past simple | ya iso → arrived | a state verb (*Na san* → I **know**); a state word (*ya ɓata* → **is** missing); after *idan* (→ present) |
| continuous | present progressive | tana dafa → is cooking | a habit (*kullum*, or a bare plural subject: *Tsuntsaye suna tashi* → Birds **fly**); a state verb (*yana son* → **likes**) |
| negative continuous | present simple | ba ya cin nama → does not eat meat | |
| future | *will* | zai sayi → will buy | |
| *Da …, da …* | *If … had …, … would have …* | | |

A subordinate clause follows a past main clause:
- *Saboda abincin **yana** da daɗi, kowa ya nemi ƙari* → "Because the food **was** delicious, everyone asked for more."
- *Mun tafi kafin ruwan sama ya fara* → "We left before the rain **started**."

### a / the (`np_words` in `transfer_ha_en.py`)

| Hausa | English |
| --- | --- |
| *-n/-r* or *ɗin* | the |
| a possessive suffix (*motata*) | my / your / his … |
| no marker, after a preposition | the (*a kasuwa* → in **the** market) |
| no marker, a thing there is only one of | the (*ruwan sama* → **the** rain) |
| no marker, plural or uncountable | nothing (*Tsuntsaye* → birds, *shinkafa* → rice) |
| no marker, singular | a / an (*keke* → **a** bicycle) |

### Choosing the English verb (`SENSE_RULES`)

One Hausa verb can stand for several English verbs. The rules choose from the context:

| Hausa | Context | English |
| --- | --- | --- |
| *ci* | + exam | pass |
| *ci* | + prize, gift, race | win |
| *ci* | otherwise | eat |
| *zauna* | continuous PAC | live |
| *zauna* | a command | sit down |
| *zauna* | + "in" a place | stay |
| *so* | continuous + a noun | like |
| *so* | + another verb | want (to) |
| *tashi* | a bird | fly |
| *ba* | + story | tell |
| *koya* / *faɗa* | with a receiver | teach / tell |
| *ci gaba da* | + a quality noun | remain (+ adjective) |

### Other choices

- **Pronouns:** *ka/ki* → "you"; *ya* → "he" (it could also be "it" for a thing; the system cannot tell).
- **Passives:** impersonal *an / aka* + verb + thing → English passive (*An gyara motar jiya* → "The car was repaired yesterday").
- **Focus:** X *ne/ce* + clause → "It was X who/that …".
- **Two objects:** *give, send, tell, buy, cook …* take two objects ("gave Ada a book"). Other verbs use *for* ("fetched water for the children"). See `DOUBLE_OBJECT_VERBS`.
- **Questions:** English moves the helper verb before the subject and adds *did/does* (*Musa ya iso?* → "Did Musa arrive?").

## Results on the 128 test sentences

The input is the speaker's Hausa; the reference is the original English.

| | Exact match | chrF | BLEU |
| --- | --- | --- | --- |
| Phase 1 (54) | 83.3% | 93.5 | 90.2 |
| Phase 2 (28) | 71.4% | 87.4 | 76.4 |
| Phase 3 (46) | 56.5% | 87.2 | 73.5 |
| **All (128)** | **71.1%** | **89.1** | **78.6** |

For comparison, English → Hausa scores 87.5% exact (chrF 95.8) on the same sentences.

### Why Hausa → English scores lower

The 37 sentences that differ fall into five groups:

| Group | Sentences | Example |
| --- | --- | --- |
| **Same Hausa, different English**: no system can get both | 3 | *Ada ta ba Musa littafi* is the Hausa for both "Ada gave Musa a book" and "Ada gave a book to Musa"; *Ngozi ce ta shirya abincin* is both "It was Ngozi who prepared the meal" and "The food was prepared by Ngozi" |
| A different word, also correct | 21 | studied **a lot** / **hard**; **the boy** / **the child** (*yaro*); **got** angry / **became** angry |
| Tense or aspect Hausa does not mark | 8 | **was sleeping** / **slept**; **can** leave / **may** leave; there **were** / there **have been** |
| Words missing from the lexicon | 3 | *dage* (persist), *cika* (fill), *jaririya* (baby girl) |
| Free translations by the speaker | 2 | *suka shiga ciki da gudu* (entered inside running) for "ran inside" |

The main reason is a general one in machine translation: **translating into a language that marks more distinctions is harder**. English needs *a/the*, simple or *-ing*, and *past* or *present perfect* in every sentence; Hausa often leaves these unmarked. The other direction loses less: English → Hausa only has to choose what Hausa marks and English doesn't (gender for *teacher* and *you*), and the group fixed defaults for those (A2/B11).

For the report, it is fair to count the first group as **unreachable**. chrF gives part credit for the second and third groups, which is why chrF (89.1) is much higher than exact match (71.1%).

### On new sentences

On the 30 blind test sentences, Hausa → English gets 8 exact (26.7%, chrF 55.3). See `blind_test_results.md`.

## Known limitations

- The system never reorders clauses, and never turns *An gyara motar* into "They repaired the car" (it always chooses the passive).
- Hausa *ya / shi* can mean "it" for a masculine thing; the system always says "he / him".
- The English word for a Hausa noun is the first row in the lexicon, unless `PREFERRED_ENGLISH` in `hausa_words.py` says otherwise.
- *ka* / *ki* both become "you"; the information about sex is lost, as it must be in English.

## How to fix a wrong translation

1. Run the sentence with `python src/try_sentence.py --hausa --analysis`.
2. If the **analysis** is wrong (a word read wrongly, wrong subject or object), see `hausa_analysis_explained.md`.
3. If the **English word** is wrong, add a rule to `SENSE_RULES` or an entry to `PREFERRED_ENGLISH`.
4. If the **tense or a/the** is wrong, check the defaults in `english_grammar.py`.
5. If the **English form** is wrong (*sweeped*), add the verb to `IRREGULAR_VERBS` in `english_words.py`.
6. Run `python src/evaluate.py --hausa` again, and also `python src/evaluate.py`: both directions share the lexicon, so check that neither score went down.
