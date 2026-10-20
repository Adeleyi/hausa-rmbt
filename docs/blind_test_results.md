# Blind test results

## What the blind test is

The rules were written while looking at the 128 development sentences. A score on those sentences shows how well the rules fit sentences the group has *seen*. It does not show how the system does on new sentences.

The blind test measures that. The group's Hausa speaker translated 30 new everyday sentences (10 simple, 10 compound, 10 complex: `data/test/CLN731_Hausa_Blind_Test.xlsx`). The system was run on them **once**, on 20 October 2026, and no rule was changed before the score was recorded.

```
python src/evaluate.py --blind            English -> Hausa
python src/evaluate.py --blind --hausa    Hausa -> English
```

## Scores

| Sentences | English → Hausa exact | chrF | Hausa → English exact | chrF |
| --- | --- | --- | --- | --- |
| Simple (10) | 7 | 88.1 | 6 | 73.6 |
| Compound (10) | 1 | 59.1 | 2 | 50.3 |
| Complex (10) | 1 | 64.8 | 0 | 52.2 |
| **All (30)** | **9 (30.0%)** | **66.5** (BLEU 44.4) | **8 (26.7%)** | **55.3** (BLEU 30.4) |
| *Development set (128), for comparison* | *112 (87.5%)* | *95.8* | *91 (71.1%)* | *89.1* |

## What the scores show

1. **The core rules generalise.** Simple sentences score 7/10 in English → Hausa. The PAC choice, verbal nouns after the continuous, possessive suffixes, *-n/-r*, locatives and adjective clauses all work on sentences the system has never seen: *Jaririn yana kuka*, *Abokina yana jira a waje*, *Na manta littafina*, *Ruwan yana da sanyi*.
2. **Compound and complex sentences fail mostly on words and expressions, not on clause structure.** The clause linkers and PACs are usually right (*Idan ruwan sama ya tsaya, za mu …*), but one missing word or one fixed expression is enough to miss an exact match.
3. **The development score overstates the system.** This is the expected result for a rule-based system: rules written while looking at the test sentences fit those sentences. The blind score is the honest estimate for new sentences.

## Error analysis: English → Hausa (21 sentences differ)

Each sentence is counted once, under its main cause.

| Cause | Sentences | Examples |
| --- | --- | --- |
| A word or word form missing from the lexicon | 8 | *bath, thirsty, floor, dishes, knocked, joke, hungry, kitchen*; *buƙatar* (the before-noun form of *buƙata* "need") |
| The lexicon has a word, but the speaker uses another | 5 | *ice* / **bishiya** (tree), *sami* / **isa** (get home), *tafi* / **fita** (go outside), *tafi* / **je**, *sauya* / **kashe** (switch off) |
| A construction with no rule | 4 | *at work* → **wurin aiki**; *or (else)* → **in ba haka ba**; *feel sick* → **ban ji daɗi ba**; *tell me why …* → **dalilin da ya sa** |
| A grammar choice where the speaker differs from our default | 4 | narrative *muka* (see below); *can* → **za ka iya**; *cannot* → **ba zan iya … ba**; *wanted* → **Ina so** |

Three linguistic findings for the report:

- **Being hungry, thirsty or sick is "feeling" in Hausa.** *I was thirsty* → *Ina jin ƙishin ruwa*; *you are hungry* → *kana jin yunwa*; *I was feeling sick* → *ban ji daɗi ba*. Our adjective rule (C7) has no pattern for continuous PAC + *jin* + noun.
- **Narrative sequence uses the relative completive.** The speaker writes *Mahaifiyata ta shirya abincin dare, kuma **muka** ci tare* and *saboda haka **muka** zauna*. In a sequence of past events, the later clauses take *muka/suka*. Our rules only use the relative completive after *when* (C14).
- **"Can" has two Hausa patterns.** Ability uses the completive (*Ada ta iya iyo*, development set); possibility or permission uses the future (*Za ka iya zama a nan*). The analysis cannot tell them apart from English *can* alone.

## Error analysis: Hausa → English (22 sentences differ)

| Cause | Sentences | Examples |
| --- | --- | --- |
| A word not in the lexicon (or not in that form) | 8 | *ƙishin, shago, ƙwanƙwasa, barkwanci, yunwa, ɗakin girki, je, gaya, maƙwabta*; *babu wanda* (nobody) |
| A fixed expression read word by word | 6 | *saboda haka* (so) read as "because"; *wurin aiki* (at work); *ni kuma* (and I); *in ba haka ba* (or else); *duk da haka* (yet); *ko kuma* (or) |
| The meaning is right, the wording is not the reference | 7 | *I will bathe* / I am going to take a bath; *turn off the lamp* / switch off the light; *She went to the school* / She has gone to school; *rejoice* / be happy |
| A verb read as a noun | 1 | *Ina buƙatar …* read as "I am at the need" instead of "I need" |

The third group is partly a problem with exact match as a measure: *Before you leave, please turn off the lamp* is a correct translation. chrF gives it part credit.

## What would fix the most

In order of how many blind sentences each would fix. The official blind score above stays as it is. If the group fixes these, report the new figures separately, as "after error analysis", because the system has now seen these sentences.

1. **Add the missing words to the lexicon** (both lists above): affects 8 + 8 sentences.
2. **Add the fixed expressions** to `hausa_words.py` (*saboda haka, duk da haka, ko kuma, in ba haka ba, babu wanda, wurin aiki*) and their English equivalents to `hausa_grammar.py`.
3. **Add a "feeling" rule:** *be hungry / thirsty / sick* → continuous PAC + *jin* + noun.
4. **Mark the everyday Hausa word as Preferred** in the lexicon (*bishiya, kashe, fita, isa, shago, fitila*).
5. **Narrative *muka/suka*** after *and / so* in a past sequence: a change to the clause-linker rule (C13), worth discussing with the speaker first.
