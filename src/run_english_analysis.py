"""Run the English analysis on every test sentence and write a report.

Run from the project folder:   python src/run_english_analysis.py
The report is written to outputs/english_analysis_report.txt
"""
from pathlib import Path

import pandas as pd

from english_analysis import analyse, describe

ROOT = Path(__file__).resolve().parent.parent
TESTSET = ROOT / "data" / "test" / "CLN731_Hausa_Test_Sentences_v2.xlsx"
REPORT = ROOT / "outputs" / "english_analysis_report.txt"


def main():
    tests = pd.read_excel(TESTSET, sheet_name="Hausa test set", header=1)
    REPORT.parent.mkdir(exist_ok=True)
    lines, with_problems = [], 0
    for _, row in tests.iterrows():
        result = analyse(row["English"])
        if result.problems:
            with_problems += 1
        lines.append(f"[{row['ID']}] {row['Our construction']}")
        lines.append(describe(result))
        lines.append("")
    summary = (f"{len(tests)} sentences analysed. "
               f"{len(tests) - with_problems} with no problems flagged, {with_problems} with problems.")
    REPORT.write_text(summary + "\n\n" + "\n".join(lines), encoding="utf-8")
    print(summary)
    print(f"Full report: {REPORT}")


if __name__ == "__main__":
    main()
