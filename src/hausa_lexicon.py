"""Looking up Hausa words in the lexicon workbook.

The workbook is read once. Every look-up goes through a function here, so the
rest of the program never has to know about Excel columns.

How a word is chosen when the workbook has several translations:
  1. rows marked "Wrong" are never used
  2. rows marked "Preferred" come first, then rows marked "Checked"
  3. otherwise the first row in the tab wins
So to change the translation the system uses, mark the row you want as
"Preferred" in the workbook.

A function returns None when the word is not in the workbook; the transfer
stage then writes the English word in [brackets] and lists it as missing.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEXICON_FILE = ROOT / "data" / "lexicon" / "Hausa_RBMT_Lexicon_v3.xlsx"

_TABS = None


def tabs():
    """Read the workbook once and keep it in memory."""
    global _TABS
    if _TABS is None:
        _TABS = pd.read_excel(LEXICON_FILE, sheet_name=None, dtype=str)
        for df in _TABS.values():
            df.fillna("", inplace=True)
    return _TABS


_INDEX = {}


def _candidates(tab, english):
    """All usable rows whose 'keys' contain this English word, best first."""
    if tab not in _INDEX:                      # build an index of the tab once
        index = {}
        for order, (_, row) in enumerate(tabs()[tab].iterrows()):
            if row.get("status") == "Wrong":
                continue
            rank = {"Preferred": 0, "Checked": 1}.get(row.get("status"), 2)
            for k in row["keys"].split(";"):
                k = k.strip().lower()
                if k:
                    index.setdefault(k, []).append((rank, order, row))
        for rows in index.values():
            rows.sort(key=lambda x: (x[0], x[1]))
        _INDEX[tab] = index
    return [r for _, _, r in _INDEX[tab].get(english.lower().strip(), [])]


def first(text):
    """'kekuna, kekunoni' -> 'kekuna' (first of several forms)."""
    return text.split(",")[0].strip()


# ---------------------------------------------------------------------------
# Content words
# ---------------------------------------------------------------------------

def noun(english, sex=""):
    """Return a dict for an English noun, or None.

    sex ('m'/'f') picks between rows such as malami / malama for "teacher".
    """
    rows = _candidates("Nouns", english)
    if not rows:
        return None
    if sex:
        matching = [r for r in rows if r["gender"] == sex]
        if matching:
            rows = matching
    row = rows[0]
    return {
        "hausa": row["hausa"], "gender": row["gender"] or "m",
        "plural": first(row["plural"]), "linked": row["linked_form"],
    }


FORM_COLUMNS = ["before_noun", "before_pronoun", "verbal_noun", "vn_with_object", "grade"]


def verb(english):
    """Return a dict with every form of an English verb, or None.

    The best row decides the Hausa verb, and its yi_verb and after_object
    columns are used as they are. Empty form columns are filled from other
    rows with the same Hausa verb and the same yi_verb value (so tafi "clap",
    a yi-verb, does not lend its forms to tafi "go"). Forms that are still
    empty fall back to the plain verb (correct for most grade 1 and 4 verbs).
    """
    rows = _candidates("Verbs", english)
    if not rows and " " in english:                  # "sit down" -> try "sit"
        rows = _candidates("Verbs", english.split()[0])
    if not rows:
        return None
    best = rows[0]
    hausa, yi = best["hausa"], best["yi_verb"]
    # rows for the same Hausa verb found under other English keys
    df = tabs()["Verbs"]
    same = [best] + [r for _, r in df[(df["hausa"] == hausa) & (df["yi_verb"] == yi)].iterrows()]
    out = {"hausa": hausa, "after_object": best["after_object"]}
    for col in FORM_COLUMNS:
        out[col] = next((r[col] for r in same if r[col]), "")
    out["yi_da"] = yi.replace(" ", "") == "Y+da"     # yi amfani da ...
    out["yi_verb"] = yi.startswith("Y")
    for col in ("before_noun", "before_pronoun", "verbal_noun", "vn_with_object"):
        out[col] = out[col] or hausa
    return out


def adjective(english):
    """Return {'masc', 'fem', 'plural', 'type'} for an English adjective, or None."""
    rows = _candidates("Adjectives", english)
    if not rows:
        return None
    row = rows[0]
    masc = row["masc"]
    return {"masc": masc, "fem": row["fem"] or masc, "plural": first(row["plural"]) or masc,
            "type": row["type"] or "adjective"}


def adverb(english):
    """Adverbs that are not in hausa_grammar.ADVERBS: try the lexicon."""
    fw = tabs()["Function words"]
    for _, row in fw[fw["category"] == "Adverb / quantifier"].iterrows():
        if english.lower() in [k.strip().lower() for k in row["english"].split(",")]:
            return row["hausa"]
    rows = _candidates("Other", english)
    if rows:
        return rows[0]["hausa"]
    return None


def name_gender(name):
    """'m' or 'f' for a person name in the Names tab, else ''."""
    df = tabs()["Names"]
    hit = df[df["name"].str.lower() == name.lower()]
    return hit.iloc[0]["gender"] if len(hit) else ""


# ---------------------------------------------------------------------------
# Function words (the "Function words" tab)
# ---------------------------------------------------------------------------

def _function(category, features_start):
    """The Hausa form whose features begin with features_start, e.g. '3sg.m; completive'."""
    fw = tabs()["Function words"]
    rows = fw[(fw["category"] == category) & (fw["features"].str.startswith(features_start))]
    if not len(rows):
        raise KeyError(f"{category}: no row with features '{features_start}'")
    return rows.iloc[0]["hausa"]


def pac(person, column):
    """PAC form, e.g. pac('3sg.f', 'continuous') -> 'tana'.

    person: 1sg, 2sg.m, 2sg.f, 3sg.m, 3sg.f, 1pl, 2pl, 3pl, or 4 (impersonal).
    Negative completive comes back with '…' where the verb goes: 'ba ta … ba'.
    """
    return _function("PAC", f"{person}; {column}")


def pronoun(kind, person):
    """kind: 'independent', 'direct object' or 'indirect object'. pronoun('direct object','3sg.m') -> 'shi'."""
    return _function(f"Pronoun: {kind}", person)


def possessive_suffix(person, feminine_head):
    """my -> '-na' (gida-na) or '-ta' (mota-ta). Returned without the hyphen."""
    head = "feminine head" if feminine_head else "masc./plural head"
    return _function("Possessive suffix", f"{person}; {head}").lstrip("-")


def number(english):
    fw = tabs()["Function words"]
    rows = fw[(fw["category"] == "Number") & (fw["english"] == english)]
    return rows.iloc[0]["hausa"] if len(rows) else english


def demonstrative(english, gender, num):
    """this -> wannan, that -> wancan/waccan, these -> waɗannan, those -> waɗancan."""
    fw = tabs()["Function words"]
    rows = fw[(fw["category"] == "Demonstrative") & (fw["english"] == english)]
    if english == "that" and len(rows) > 1:
        want = "fem." if gender == "f" else "masc."
        rows = rows[rows["features"].str.startswith(want)]
    return rows.iloc[0]["hausa"]


def existential(negative=False):
    """akwai (there is) / babu (there is no)."""
    fw = tabs()["Function words"]
    eng = "there is no" if negative else "there is / there are"
    return fw[(fw["category"] == "Existential") & (fw["english"] == eng)].iloc[0]["hausa"]

