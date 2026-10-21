"""Looking up Hausa words in the lexicon (data/lexicon/*.csv, one file per word class, read once).

When a word has several rows: "Wrong" rows are never used; "Preferred" comes first,
then "Checked", then the first row. A function returns None when the word is missing,
and the transfer stage writes the English word in [brackets].
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEXICON_DIR = ROOT / "data" / "lexicon"
# tab name used in the code -> CSV file
TAB_FILES = {"Nouns": "nouns.csv", "Verbs": "verbs.csv", "Adjectives": "adjectives.csv",
             "Function words": "function_words.csv", "Other": "other.csv", "Names": "names.csv"}

_TABS = None


def tabs():
    """Read the CSV files once and keep them in memory. Empty cells are ''."""
    global _TABS
    if _TABS is None:
        _TABS = {tab: pd.read_csv(LEXICON_DIR / name, dtype=str, keep_default_na=False, encoding="utf-8-sig")
                 for tab, name in TAB_FILES.items()}
    return _TABS


_INDEX = {}


def _candidates(tab, english):
    """All usable rows whose 'keys' contain this English word, best first."""
    if tab not in _INDEX:
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


# ===== Content words =====

def noun(english, sex=""):
    """Return a dict for an English noun, or None."""
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
    """Return a dict with every form of an English verb, or None."""
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


# ===== Function words (the "Function words" tab) =====

def _function(category, features_start):
    """The Hausa form whose features begin with features_start, e.g. '3sg.m; completive'."""
    fw = tabs()["Function words"]
    rows = fw[(fw["category"] == category) & (fw["features"].str.startswith(features_start))]
    if not len(rows):
        raise KeyError(f"{category}: no row with features '{features_start}'")
    return rows.iloc[0]["hausa"]


def pac(person, column):
    """PAC form, e.g. pac('3sg.f', 'continuous') -> 'tana'."""
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

