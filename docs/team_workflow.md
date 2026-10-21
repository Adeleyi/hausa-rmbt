# Group workflow

How the group works on this repository.

## Every time you work

```
git pull                                   get the group's latest changes first
python src/try_sentence.py "The boy laughed."   check that everything still runs
... make your changes ...
python src/evaluate.py                     check English → Hausa did not get worse
python src/evaluate.py --hausa             check Hausa → English did not get worse
git status                                 see what you changed (.venv must not be listed)
git add -A
git commit -m "Say what you changed"
git push
```

- Write commit messages that say what changed, e.g. `Add plural for kujera to the lexicon`.
- If `git push` is rejected, someone pushed while you worked: run `git pull`, then `git push` again.
- Both directions share the lexicon, so a fix for one direction can break the other. Always run both scores.

## Rules

- **Only the lexicographer edits the lexicon workbook.** Git cannot merge two people's changes to an Excel file, so one set of edits would be lost. Everyone else sends lexicon changes to the lexicographer. If the workbook shows as changed and you are not the lexicographer, undo it before committing: `git restore data/lexicon/Hausa_RBMT_Lexicon_v3.xlsx`.
- **Linguists edit the data files** (`english_words.py`, `hausa_words.py`, `hausa_grammar.py`, `english_grammar.py`). They hold word lists and decisions, not logic.
- **The blind test is never used to write rules.** Its official score was recorded on 20 October 2026. If rules are fixed after studying its errors, report the new score separately as "after error analysis".
- Do not commit the `.venv` folder (`.gitignore` already excludes it).

## When a translation is wrong

1. Run it with `python src/try_sentence.py --analysis "the sentence"`.
2. Wrong word class or structure in the analysis → stage 1 (`english_analysis.py`, `hausa_analysis.py`, or their word lists).
3. Analysis right, wrong choice in "Rules used" → stage 2 (a transfer rule, or a setting in `hausa_grammar.py` / `english_grammar.py`).
4. A word in [brackets] → missing from the lexicon: send it to the lexicographer.
5. Add the case to the errors log in the group's working doc.
