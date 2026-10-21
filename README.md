# English ↔ Hausa rule-based machine translation

A transfer-based machine translation system between English and Hausa (Standard Kano Hausa), in both directions, written in Python. Every translation comes from hand-written grammar rules and a lexicon, not from machine learning, so every output can be traced to the rules that produced it.

Built by a group of five for the course CLN 731.

**Try it online:** [live demo](https://hausa-rbmt.streamlit.app) · **Results:** English → Hausa gets 87.5% of our 128 development sentences exactly right, and 30% of 30 new sentences ([details](docs/results.md)).

## How it works

Both directions have the same three stages: **analysis → transfer → generation**.

| Stage | English → Hausa | Hausa → English |
| --- | --- | --- |
| 1. Analysis: read the sentence | `src/english_analysis.py` | `src/hausa_analysis.py` |
| 2. Transfer: one rule per construction | `src/transfer_en_ha.py` | `src/transfer_ha_en.py` |
| 3. Generation: write the word forms | `src/hausa_generate.py` | `src/english_generate.py` |

The word lists and the group's grammar decisions are in plain data files that linguists can edit: `english_words.py`, `hausa_words.py`, `hausa_grammar.py`, `english_grammar.py`. The lexicon is a set of CSV files (`data/lexicon/`, one per word class), read by `src/hausa_lexicon.py`.

## Setup

```
python -m venv .venv
source .venv/bin/activate          (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
```

## Use

```
python src/try_sentence.py                     English → Hausa: type sentences
python src/try_sentence.py --hausa             Hausa → English
python src/try_sentence.py "I am coming."      one sentence
python src/try_sentence.py --rules             also show the rules used
python src/try_sentence.py --analysis          also show the analysis

python src/evaluate.py                         score English → Hausa (add --hausa, --blind, --phase 1)
python src/run_analysis.py                     check the analysis on all test sentences
streamlit run app.py                           the web demo, on your own computer
```

```
English> I am coming.
Hausa:   Ina zuwa.
```

## Folders

| Folder | Contents |
| --- | --- |
| `src/` | the code |
| `data/lexicon/` | the lexicon, one CSV file per word class (see its README) |
| `data/test/` | the 128 development sentences and the 30 blind test sentences, with the speaker's translations |
| `outputs/` | scores and analysis reports written by the programs |
| `docs/` | explanations of each stage, results, and the group's workflow |

## Documentation

- [Results and error analysis](docs/results.md)
- [English analysis](docs/english_analysis_explained.md) · [English → Hausa](docs/english_to_hausa_explained.md)
- [Hausa analysis](docs/hausa_analysis_explained.md) · [Hausa → English](docs/hausa_to_english_explained.md)
- [Blind test](docs/blind_test_results.md)
- [Deploying the web demo](docs/deploy_demo.md) · [Group workflow](docs/team_workflow.md)

## Licence and data sources

- **Code:** MIT licence (see `LICENSE`).
- **Data** (`data/`): CC BY-SA 4.0, because the lexicon includes entries from Wiktionary.
- Sources: Wiktionary Hausa entries via [Kaikki.org](https://kaikki.org/) (CC BY-SA); the [AfriDict](https://huggingface.co/datasets/taresco/afri-dict) English–Hausa list (TARESCo), corrected by the group; verb, demonstrative and question-word lists compiled by the group. Test sentences adapted from the group's construction list and translated or checked by the group's Hausa speaker.
