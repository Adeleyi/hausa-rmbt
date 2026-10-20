"""Translate sentences you type.

Run from the project folder:
    python src/try_sentence.py                  English -> Hausa
    python src/try_sentence.py --hausa          Hausa -> English
    python src/try_sentence.py "I am coming."   translate one sentence and stop

For the group (checking and fixing the rules), add:
    --rules      also show the rules used and the words missing from the lexicon
    --analysis   also show the analysis (stage 1), then the rules

Type a sentence and press Enter. Type q (or press Enter on an empty line) to stop.
"""
import sys

import english_analysis
import hausa_analysis
import transfer_en_ha
import transfer_ha_en


def show(text, hausa_in, rules, analysis):
    if hausa_in:
        t = transfer_ha_en.translate(text)
        label, output, describe = "English", t.english, hausa_analysis.describe
    else:
        t = transfer_en_ha.translate(text)
        label, output, describe = "Hausa", t.hausa, english_analysis.describe
    if analysis:
        print(describe(t.analysis) + "\n")
    print(f"{label + ':':<9}{output}")
    if rules or analysis:
        print("Rules used:")
        for rule in t.rules:
            print(f"  - {rule}")
        if t.missing:
            print("Not in the lexicon: " + ", ".join(f"{word} ({kind})" for kind, word in t.missing))


def main():
    options = [a for a in sys.argv[1:] if a.startswith("--")]
    sentence = " ".join(a for a in sys.argv[1:] if not a.startswith("--"))
    hausa_in = "--hausa" in options
    rules, analysis = "--rules" in options, "--analysis" in options
    source = "Hausa" if hausa_in else "English"

    if sentence:                                  # one sentence from the command line
        show(sentence, hausa_in, rules, analysis)
        return
    print(f"Hausa RBMT: {source} -> {'English' if hausa_in else 'Hausa'}. Type q to quit.\n")
    while True:
        try:
            sentence = input(f"{source + '>':<9}").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if sentence.lower() in ("", "q", "quit", "exit"):
            break
        try:
            show(sentence, hausa_in, rules, analysis)
        except Exception as err:          # never crash: report the problem and carry on
            print(f"Sorry, the system failed on this sentence: {err}")
        print()


if __name__ == "__main__":
    main()
