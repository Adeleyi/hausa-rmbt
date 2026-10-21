# Results

Scores are measured against the Hausa speaker's translations (English → Hausa) or the original English (Hausa → English).

- **Exact match:** the output is identical to the reference, ignoring capitals and final punctuation.
- **chrF** (0–100): how many letter sequences the output shares with the reference. It gives part credit for a nearly right word (*ɗalibai* for *ɗaliban*).
- **BLEU** (0–100): how many word sequences the output shares with the reference, over the whole test set.

## Overall

| Test set | Direction | Exact match | chrF | BLEU |
| --- | --- | --- | --- | --- |
| Development (128 sentences) | English → Hausa | 112 (87.5%) | 95.8 | 92.2 |
| Development (128 sentences) | Hausa → English | 91 (71.1%) | 89.1 | 78.6 |
| Blind (30 sentences) | English → Hausa | 9 (30.0%) | 66.5 | 44.4 |
| Blind (30 sentences) | Hausa → English | 8 (26.7%) | 55.3 | 30.4 |

The rules were written while looking at the 128 development sentences. The 30 blind sentences are everyday sentences the system had never seen; they were run once, on 20 October 2026, with no rule changes before the score was recorded. The blind score is the fair estimate for new sentences.

## Development set, by phase (English → Hausa)

| Phase | Constructions | Sentences | Exact |
| --- | --- | --- | --- |
| 1 | C1–C10 (simple sentences and negation), existential, weather | 54 | 51 (94.4%) |
| 2 | C11–C13 (yes/no questions, question words, compound sentences), commands, experiencer | 28 | 25 (89.3%) |
| 3 | C14–C16 (subordinate, relative and reported clauses), focus, passive | 46 | 36 (78.3%) |

## Blind test, by sentence type

| Sentence type | English → Hausa exact | Hausa → English exact |
| --- | --- | --- |
| Simple (10) | 7 | 6 |
| Compound (10) | 1 | 2 |
| Complex (10) | 1 | 0 |

## Other checks

- English analysis: 128 of 128 development sentences analysed with no problems flagged.
- Hausa analysis: 125 of 128 with no problems (3 words missing from the lexicon). It agrees with the English analysis of the same sentence on negation, sentence type and number of clauses for all 128.

## Why the scores differ

- **Hausa → English scores lower than English → Hausa** because English must mark things Hausa often leaves unmarked: *a/the*, *slept / was sleeping*, *got / became angry*. For 3 development sentences, two different English references share the same Hausa, so no system could match both.
- **The blind test scores lower than the development set** mainly because of words missing from the lexicon and fixed expressions and constructions the rules never saw. The error analysis is in [blind_test_results.md](blind_test_results.md).

## Reproducing the scores

```
python src/evaluate.py                 English → Hausa, development set
python src/evaluate.py --hausa         Hausa → English, development set
python src/evaluate.py --blind         English → Hausa, blind test
python src/evaluate.py --blind --hausa Hausa → English, blind test
```

Each run writes a workbook to `outputs/` with one row per sentence and the rules used.
