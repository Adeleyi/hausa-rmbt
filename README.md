# Hausa Rule-Based Machine Translation (CLN 731 group project)

A transfer-based machine translation system between English and Hausa (Standard Kano Hausa), in both directions, written in Python. Every step is a hand-written rule: if a translation is wrong, a rule or a word list is wrong, and you can find it and fix it.

## Folders

| Folder | What is in it |
| --- | --- |
| `data/lexicon/` | The lexicon workbook (one tab per word class). |
| `data/test/` | The 128 development sentences, and the 30 blind test sentences, with the speaker's translations. |
| `src/` | The Python code. |
| `outputs/` | Reports and scores written by the programs. |
| `docs/` | Explanations of each stage, for the group and the report. |

## How the system is built

Both directions have the same three stages: **analysis → transfer → generation**.

| Stage | English → Hausa | Hausa → English |
| --- | --- | --- |
| 1. Analysis: read the sentence | `english_analysis.py` (word lists: `english_words.py`) | `hausa_analysis.py` (word lists: `hausa_words.py`) |
| 2. Transfer: one rule per construction | `transfer_en_ha.py` (choices: `hausa_grammar.py`) | `transfer_ha_en.py` (choices: `english_grammar.py`) |
| 3. Generation: write the words | `hausa_generate.py` | `english_generate.py` |

`hausa_lexicon.py` reads the lexicon workbook for both directions.

**Linguists edit the data files** (`english_words.py`, `hausa_words.py`, `hausa_grammar.py`, `english_grammar.py`) and the lexicon workbook. They contain word lists and the group's decisions, not program logic. The other files are the rules.

The three programs you run:

| Program | What it does |
| --- | --- |
| `try_sentence.py` | Type a sentence, see the translation. |
| `evaluate.py` | Score the system against the speaker's translations. |
| `run_analysis.py` | Check stage 1 on all 128 sentences and write the analysis reports. |

## First-time setup

1. Clone this repository in VS Code (Source Control → Clone Repository).
2. Open the VS Code terminal (Terminal → New Terminal) and run `python -m venv .venv`
3. Activate the environment:
   - Windows: `.venv\Scripts\activate`
   - Mac: `source .venv/bin/activate`
4. Install the libraries: `pip install -r requirements.txt`
5. Check that everything works: `python src/try_sentence.py "The boy laughed."` should print `Hausa:   Yaron ya yi dariya.`

On Linux or WSL (Ubuntu), use `python3 -m venv .venv` and `source .venv/bin/activate`.

## Translating

```
python src/try_sentence.py                  English -> Hausa: type sentences, see the Hausa
python src/try_sentence.py --hausa          Hausa -> English
python src/try_sentence.py "I am coming."   one sentence
```

```
English> I am coming.
Hausa:   Ina zuwa.
```

To see **why** a translation came out the way it did, add `--rules` (the rules used and any missing words) or `--analysis` (the stage 1 analysis as well):

```
English> I am coming.
Hausa:   Ina zuwa.
Rules used:
  - Construction: verbal sentence
  - Tense: present progressive -> continuous PAC
  - PAC: 1sg + continuous -> ina
  - Verbal noun after continuous PAC: zuwa
  - Subject pronoun left out: the PAC shows the person (1sg)
```

A word missing from the lexicon appears in [brackets].

## Scoring

```
python src/evaluate.py                    English -> Hausa, the 128 development sentences
python src/evaluate.py --phase 1          only Phase 1
python src/evaluate.py --hausa            Hausa -> English, the 128 development sentences
python src/evaluate.py --blind            English -> Hausa, the 30 blind test sentences
python src/evaluate.py --blind --hausa    Hausa -> English, the 30 blind test sentences
```

Each run writes a workbook to `outputs/` (one row per sentence, an empty "Error type" column for the group, scores per phase and construction, and the missing words).

## Results

| Test set | Direction | Exact match | chrF | BLEU |
| --- | --- | --- | --- | --- |
| Development (128) | English → Hausa | 87.5% (112) | 95.8 | 92.2 |
| Development (128) | Hausa → English | 71.1% (91) | 89.1 | 78.6 |
| **Blind (30)** | English → Hausa | **30.0% (9)** | **66.5** | **44.4** |
| **Blind (30)** | Hausa → English | **26.7% (8)** | **55.3** | **30.4** |

The rules were written for the development sentences. The blind sentences were translated by the speaker and run **once**, on 20 October 2026, with no rule changes before the score was recorded. The gap between the two sets is the main finding of the evaluation: see `docs/blind_test_results.md`.

| Phase | Constructions | Development set, English → Hausa |
| --- | --- | --- |
| 1 | C1–C10, existential, weather | 51 of 54 exact |
| 2 | C11–C13 (questions, compound), imperative, experiencer | 25 of 28 exact |
| 3 | C14–C16 (complex), relative clauses, focus, passive | 36 of 46 exact |

## Documentation

| File | About |
| --- | --- |
| `docs/english_analysis_explained.md` | Stage 1, English |
| `docs/english_to_hausa_explained.md` | English → Hausa transfer and generation, with the questions for the speaker |
| `docs/hausa_analysis_explained.md` | Stage 1, Hausa |
| `docs/hausa_to_english_explained.md` | Hausa → English transfer and generation |
| `docs/blind_test_results.md` | The blind test and its error analysis |

## Working rules

- **Pull** before you start work, **commit** and **push** when you finish.
- Write commit messages that say what changed, e.g. `Add PAC table to transfer rules`.
- **Only the lexicographer edits the lexicon workbook.** Git cannot merge two people's changes to an Excel file, so one set of edits would be lost. Everyone else sends lexicon changes to the lexicographer.
- After any change, run `python src/evaluate.py` and `python src/evaluate.py --hausa`. Both directions share the lexicon, so check that neither score went down.
- Do not commit the `.venv` folder (it is ignored automatically).

## Data sources and licences

- Wiktionary Hausa entries via Kaikki.org (CC BY-SA).
- English–Hausa word list, corrected by the group.
- Verb, demonstrative and question-word lists compiled by the group.
- Test sentences adapted from the group's construction list; Hausa translations checked by the group's Hausa speaker.
