"""Score the system against the reference translations.

    python src/evaluate.py              English -> Hausa, the 128 development sentences
    python src/evaluate.py --phase 1    only Phase 1
    python src/evaluate.py --hausa      Hausa -> English
    python src/evaluate.py --blind      the 30 blind test sentences (add --hausa for Hausa -> English)

Scores: exact match, chrF and BLEU (see docs/results.md).
Results go to outputs/eval_results*.xlsx: one row per sentence, a summary, and missing words.
"""
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import sacrebleu

import transfer_en_ha
import transfer_ha_en

ROOT = Path(__file__).resolve().parent.parent
TESTSET = ROOT / "data" / "test" / "CLN731_Hausa_Test_Sentences_v2.xlsx"
BLIND_TESTSET = ROOT / "data" / "test" / "CLN731_Hausa_Blind_Test.xlsx"
GOLD_COLUMNS = ["Hausa (draft)", "Hausa (speaker)"]     # the column with the speaker's translation


def normalise(text):
    """Lower case, straight apostrophes, no final punctuation, single spaces."""
    text = str(text).replace("’", "'").replace("‘", "'").lower()
    text = re.sub(r"[.?!,;:]", " ", text)
    return " ".join(text.split())


def score_group(df):
    """exact-match %, mean chrF and corpus BLEU for a group of rows."""
    hyps, refs = df["System output"].map(normalise).tolist(), df["Reference"].map(normalise).tolist()
    return pd.Series({
        "Sentences": len(df),
        "Exact match (%)": round(100 * df["Exact"].mean(), 1),
        "chrF": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 1),
        "BLEU": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 1),
    })


def main():
    phase = None
    if "--phase" in sys.argv:
        phase = int(sys.argv[sys.argv.index("--phase") + 1])
    blind, hausa_in = "--blind" in sys.argv, "--hausa" in sys.argv
    testset = BLIND_TESTSET if blind else TESTSET
    results = ROOT / "outputs" / f"eval_results{'_blind' if blind else ''}{'_ha_en' if hausa_in else ''}.xlsx"
    tests = pd.read_excel(testset, sheet_name="Hausa test set", header=1, dtype=str)
    gold_col = next(c for c in GOLD_COLUMNS if c in tests.columns)
    if "Phase" not in tests:
        tests["Phase"] = None
    if phase:
        tests = tests[tests["Phase"] == str(phase)]

    rows, missing = [], Counter()
    for _, t in tests.iterrows():
        source, reference = (t[gold_col], t["English"]) if hausa_in else (t["English"], t[gold_col])
        try:
            if hausa_in:
                result = transfer_ha_en.translate(source)
                output, rules = result.english, result.rules
            else:
                result = transfer_en_ha.translate(source)
                output, rules = result.hausa, result.rules
            for kind, word in result.missing:
                if kind not in ("wh", "quantity"):      # question words are grammar rules, not lexicon
                    missing[(kind, word.lower())] += 1
        except Exception as err:               # a crash counts as a wrong answer
            output, rules = f"ERROR: {err}", []
        rows.append({
            "ID": t["ID"], "Phase": t["Phase"], "Construction": t["Our construction"],
            "Source": source, "Reference": reference, "System output": output,
            "Exact": normalise(output) == normalise(reference),
            "chrF": round(sacrebleu.sentence_chrf(normalise(output), [normalise(reference)]).score, 1),
            "Error type": "", "Notes": "", "Rules used": "\n".join(rules),
        })
    df = pd.DataFrame(rows)

    overall = score_group(df).rename("All")
    groups = [overall.to_frame().T]
    if df["Phase"].notna().any():
        by_phase = df.groupby("Phase").apply(score_group, include_groups=False)
        groups.append(by_phase.rename(index=lambda p: f"Phase {p}"))
    by_cons = df.groupby("Construction").apply(score_group, include_groups=False)
    # C1, C2 ... C10 in number order, then the named sections
    by_cons = by_cons.loc[sorted(by_cons.index, key=lambda c: (0, int(re.match(r"C(\d+)", c).group(1)), c)
                                 if re.match(r"C\d+", c) else (1, 0, c))]
    summary = pd.concat(groups + [by_cons])
    summary["Sentences"] = summary["Sentences"].astype(int)

    miss = pd.DataFrame([{"Word class": k, "Word": w, "Sentences": n} for (k, w), n in missing.most_common()],
                        columns=["Word class", "Word", "Sentences"])

    results.parent.mkdir(exist_ok=True)
    with pd.ExcelWriter(results, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="Sentences", index=False)
        summary.to_excel(xl, sheet_name="Summary", index_label="Group")
        miss.to_excel(xl, sheet_name="Missing words", index=False)
        widths = {"Sentences": [6, 6, 20, 45, 45, 45, 7, 7, 16, 30, 60],
                  "Summary": [26, 10, 16, 8, 8], "Missing words": [14, 24, 10]}
        for name, ws in xl.sheets.items():
            for col, w in zip("ABCDEFGHIJK", widths[name]):
                ws.column_dimensions[col].width = w
            ws.freeze_panes = "A2"

    pd.set_option("display.width", 120)
    print(summary.to_string())
    wrong = df[~df["Exact"]]
    print(f"\n{len(wrong)} sentence(s) differ from the reference translation:")
    for _, r in wrong.iterrows():
        print(f"  [{r['ID']}] {r['Source']}\n      system:    {r['System output']}\n      reference: {r['Reference']}")
    if len(miss):
        print(f"\nWords missing from the lexicon: {', '.join(miss['Word'])}")
    print(f"\nFull results: {results}")


if __name__ == "__main__":
    main()
