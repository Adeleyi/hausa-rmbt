"""Run stage 1 (the analysis) on every development sentence, in both languages.

    python src/run_analysis.py

Writes outputs/english_analysis_report.txt and outputs/hausa_analysis_report.txt.
The Hausa report checks that both analyses agree on negation, sentence type,
number of clauses and the main verb.
"""
from pathlib import Path

import pandas as pd

import english_analysis as E
import hausa_analysis as H

ROOT = Path(__file__).resolve().parent.parent
TESTSET = ROOT / "data" / "test" / "CLN731_Hausa_Test_Sentences_v2.xlsx"
ENGLISH_REPORT = ROOT / "outputs" / "english_analysis_report.txt"
HAUSA_REPORT = ROOT / "outputs" / "hausa_analysis_report.txt"
BE_LIKE = {"equational", "adjective", "locative", "belong", "existential", "weather", "what-is", "become"}


# ===== Comparing the English and the Hausa analysis of one sentence =====

def is_negative(clauses, english):
    for cl in clauses:
        if english and (cl.verb and cl.verb.negative or getattr(cl.subject, "negative", False)):
            return True
        if not english and cl.negative:
            return True
        if is_negative(cl.clauses, english):
            return True
    return False


def main_clause(analysis):
    return next((c for c in analysis.clauses if c.role == "main"), analysis.clauses[0])


def main_verb_hausa(analysis):
    cl = main_clause(analysis)
    if cl.verb:
        return cl.verb.english
    if cl.construction == "possession":
        return "have"
    return "be" if cl.construction in BE_LIKE else cl.construction


def compare(english, hausa):
    """Return the list of disagreements between the two analyses (empty = they agree)."""
    out = []
    if is_negative(english.clauses, True) != is_negative(hausa.clauses, False):
        out.append("negation")
    e_mood, h_mood = main_clause(english).mood, main_clause(hausa).mood
    if e_mood != h_mood:
        out.append(f"sentence type ({e_mood} / {h_mood})")
    if len(english.clauses) != len(hausa.clauses):
        out.append(f"clauses ({len(english.clauses)} / {len(hausa.clauses)})")
    ev = main_clause(english).verb.lemma if main_clause(english).verb else "?"
    hv = main_verb_hausa(hausa)
    same = ev == hv or ev.split()[0] == hv.split()[0] or (ev in ("be", "become", "remain") and hv == "be") \
        or (ev in ("have", "own") and hv == "have")
    if not same:
        out.append(f"main verb ({ev} / {hv})")
    return out


# ===== The two reports =====

def main():
    tests = pd.read_excel(TESTSET, sheet_name="Hausa test set", header=1, dtype=str)
    n = len(tests)
    ENGLISH_REPORT.parent.mkdir(exist_ok=True)
    english_lines, hausa_lines = [], []
    english_problems = hausa_problems = 0
    agree = {"negation": 0, "sentence type": 0, "clauses": 0, "main verb": 0}

    for _, row in tests.iterrows():
        english = E.analyse(row["English"])
        hausa = H.analyse(row["Hausa (draft)"])
        english_problems += bool(english.problems)
        hausa_problems += bool(hausa.problems)
        english_lines += [f"[{row['ID']}] {row['Our construction']}", E.describe(english), ""]

        diffs = compare(english, hausa)
        for key in agree:
            agree[key] += not any(d.startswith(key) for d in diffs)
        hausa_lines += [f"[{row['ID']}] {row['Our construction']}   English: {row['English']}", H.describe(hausa)]
        if diffs:
            hausa_lines.append("  DIFFERS FROM THE ENGLISH ANALYSIS: " + "; ".join(diffs))
        hausa_lines.append("")

    english_summary = [f"{n} sentences analysed. "
                       f"{n - english_problems} with no problems flagged, {english_problems} with problems."]
    hausa_summary = [f"{n} sentences analysed. "
                     f"{n - hausa_problems} with no problems flagged, {hausa_problems} with problems.",
                     "Agreement with the English analysis of the same sentence:"]
    hausa_summary += [f"  {key:<14} {count}/{n}" for key, count in agree.items()]

    ENGLISH_REPORT.write_text("\n".join(english_summary) + "\n\n" + "\n".join(english_lines), encoding="utf-8")
    HAUSA_REPORT.write_text("\n".join(hausa_summary) + "\n\n" + "\n".join(hausa_lines), encoding="utf-8")
    print("English analysis: " + english_summary[0])
    print("Hausa analysis:   " + "\n".join(hausa_summary))
    print(f"Full reports: {ENGLISH_REPORT}\n              {HAUSA_REPORT}")


if __name__ == "__main__":
    main()
