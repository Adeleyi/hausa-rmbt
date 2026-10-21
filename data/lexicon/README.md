# Hausa RBMT lexicon (draft 3, 19 Oct)

One CSV file per word class. The program reads them through `src/hausa_lexicon.py`.

| File | Rows | What it holds |
|---|---|---|
| `nouns.csv` | 2,897 | nouns, with gender, plural and linked (-n/-r) form |
| `verbs.csv` | 781 | verbs, with grade and the forms before a noun, before a pronoun, verbal noun … |
| `adjectives.csv` | 200 | adjectives (masc., fem., plural), and the words Hausa expresses with a noun |
| `function_words.csv` | 234 | PAC table, pronouns, possessive suffixes, demonstratives, numbers … |
| `other.csv` | 324 | adverbs, interjections and other words |
| `names.csv` | 299 | person and place names, with gender |
| `changes_v3.csv` | 81 | every change made in draft 3 (not read by the program) |
| `review_of_group_lists.csv` | 21 | corrections suggested for the group's word lists (not read by the program) |

## Editing the files

- **Keep the files in UTF-8**, or the hooked letters (ɓ ɗ ƙ ƴ) are lost. VS Code, LibreOffice and Google Sheets do this by default. In Excel, use **File → Save As → "CSV UTF-8 (Comma delimited)"**, never plain "CSV".
- Do not rename, reorder or delete the columns the program uses (see below). Adding rows anywhere is fine.
- After editing, run both scores (`python src/evaluate.py` and `python src/evaluate.py --hausa`) to check nothing got worse.

## Conventions

**Sources.** A hand-added core list of about 130 everyday words used by the test sentences; Wiktionary (Kaikki) Hausa file; the English–Hausa CSV as corrected by the group on 17 Oct; the group's verb, demonstrative and question-word lists; the confirmed rules doc.

**One row = one meaning.** A Hausa word with three English meanings has three rows. `keys` holds the short English look-up words the program matches, separated by `;`. `english` is the full meaning, for people.

**Spelling.** Standard Nigerian spelling: hooked letters ɓ ɗ ƙ, 'y, one straight apostrophe; tone and length marks removed.

**`status`.** Not checked = from a source, not yet verified · Needs check = known problem or guessed gender · Checked = confirmed by the Hausa speaker · Preferred = confirmed, and the translation the program uses when there are several · Wrong = do not use.

**`gender_source`** (nouns). Core list = hand-added everyday word · Wiktionary = from the dictionary · Guess (-a = f) = to be checked with the "X ne / X ce" test.

**Verb forms.** `before_noun` / `before_pronoun` / `verbal_noun` / `vn_with_object` are filled for about 70 core verbs as a draft. The rest are blank until needed.

**`yi_verb`.** Y = the English verb is yi + this noun in Hausa (laugh → yi dariya). ji = used with ji.

**`type`** (adjectives). adjective = a real Hausa adjective (babba, sabo) · noun with da = Hausa uses a noun: 'tana da zafi', 'mai zafi' · noun without da = 'suna farin ciki', 'mai farin ciki' · noun after linker = 'waƙar gargajiya' · mai + noun = 'Ada mai gaskiya ce' · verb = 'Littafin ya ɓata'

**Priority.** Check the rows the test sentences use first. Filter `status` = Needs check to see the risky rows.

**Draft 3.** Words needed by Phases 1-3 added; the speaker's choices marked Preferred; new `type` column in adjectives and `after_object` column in verbs. See `changes_v3.csv`.

The lexicon was a single Excel workbook (`Hausa_RBMT_Lexicon_v3.xlsx`) until 21 Oct 2026; it is still in the git history.
