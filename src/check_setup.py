"""Check that Python, the libraries and the data files are set up.

Run from the project folder:   python src/check_setup.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEXICON = ROOT / "data" / "lexicon" / "Hausa_RBMT_Lexicon_v3.xlsx"
TESTSET = ROOT / "data" / "test" / "CLN731_Hausa_Test_Sentences_v2.xlsx"


def main():
    # 1. Load every tab of the lexicon into a dictionary of tables
    lexicon = pd.read_excel(LEXICON, sheet_name=None, dtype=str)
    print("Lexicon loaded. Rows per tab:")
    for tab, table in lexicon.items():
        if tab != "README":
            print(f"  {tab:<22} {len(table):>5}")

    # 2. Look up one English word in the Nouns tab
    nouns = lexicon["Nouns"].fillna("")
    hits = nouns[nouns["keys"].str.split("; ").apply(lambda keys: "house" in keys)]
    first = hits.iloc[0]
    print(f'\nLook-up test: "house" -> {first["hausa"]} (gender {first["gender"]}, plural {first["plural"]})')

    # 3. Load the test sentences (the header is on the second row)
    tests = pd.read_excel(TESTSET, sheet_name="Hausa test set", header=1)
    print(f"\nTest set loaded: {len(tests)} sentences.")
    print(f'  Example: {tests.iloc[0]["English"]}  ->  {tests.iloc[0]["Hausa (draft)"]}')

    print("\nEverything works. You are ready for the next step.")


if __name__ == "__main__":
    main()
