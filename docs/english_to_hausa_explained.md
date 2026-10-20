# English → Hausa: transfer and generation, explained

Stage 1 (the English analysis) labels every part of the English sentence. This document covers what happens next:

- **Stage 2, transfer:** decides what the Hausa sentence contains: which construction, which PAC, which verb form and which words.
- **Stage 3, generation:** writes the Hausa words out: *-n/-r*, possessive suffixes, adjective agreement, *ne/ce*, word order, the capital letter and the full stop.

So far the transfer rules cover:
- **Phase 1:** C1–C10, plus the existential and weather sections.
- **Phase 2:** C11–C13 (yes/no questions, question-word questions, compound sentences), plus commands and experiencer verbs.
- **Phase 3:** C14 (subordinate clauses, counterfactuals), C15 (relative clauses), C16 (reported clauses), focus (S10) and passives (S17).

All 128 test sentences are now covered by a rule.

## Files

| File | What it is | Who edits it |
| --- | --- | --- |
| `src/hausa_grammar.py` | Grammar tables and group decisions (A2, A6, A7, A17 …), prepositions, adverbs, weather words | Linguists |
| `data/lexicon/Hausa_RBMT_Lexicon_v3.xlsx` | All Hausa words, including the PAC table and pronouns in the "Function words" tab | Lexicographer only |
| `src/transfer_en_ha.py` | One rule per construction (stage 2) | Coders |
| `src/hausa_generate.py` | Word-building rules (stage 3) | Coders |
| `src/hausa_lexicon.py` | Reads the workbook and looks words up | Coders |
| `src/try_sentence.py` | Type a sentence, see the Hausa | Nobody (just run it) |
| `src/evaluate.py` | Scores the system against the speaker's translations | Nobody (just run it) |

## How to run it

```
python src/try_sentence.py                 type sentences, see the Hausa
python src/try_sentence.py --rules         the same, plus the rules used
python src/try_sentence.py --analysis      the same, plus the English analysis
python src/try_sentence.py --rules "Ada has a car."    one sentence
python src/evaluate.py --phase 1           score Phase 1
python src/evaluate.py                     score all 128 sentences
```

## A worked example

With `python src/try_sentence.py --rules`:

```
English> The teacher sent the students a message.
Hausa:   Malamin ya aika wa ɗaliban saƙo.
Rules used:
  - Construction: verbal sentence
  - A6: the teacher -> malamin
  - A6: the student -> ɗaliban
  - Receiver: verb + wa + receiver + object
  - Tense: past simple -> completive PAC
  - PAC: 3sg.m + completive -> ya
  - Verb form: aika (before the receiver: wa / masa)
```

| Stage | What happens |
| --- | --- |
| Analysis | subject *teacher* (definite); verb *send* (past simple); receiver *students* (plural, definite); object *message* |
| Transfer | Verbal sentence rule. *teacher* → *malami*, which is masculine, so the PAC is 3sg.m. Past simple uses the completive column, giving *ya*. *send* → *aika*. The receiver needs *wa*. |
| Generation | *malami* + "the" → *malamin*; *ɗalibai* + "the" → *ɗaliban*; words in Hausa order; capital letter and full stop |

## The construction rules

`transfer_en_ha.py` looks at the analysis and chooses one rule per clause:

| Rule | When | Hausa pattern | Example |
| --- | --- | --- | --- |
| `existential_clause` | *there is / there was* | *Akwai* X · *Babu* X · *An yi* X | Akwai matsala. An yi ƙorafe-ƙorafe da yawa. |
| `weather_clause` | subject *it* or *the weather* + a weather word | impersonal PAC: *Ana* N · *An yi* N | Ana ruwa. Sama ya yi gajimare. |
| `become_clause` | *become* + adjective | PAC + *yi* + noun, or *zama* + adjective | Musa ya yi fushi. |
| `equational_clause` | *be* + noun (C6) | X N *ne/ce*; negative X *ba* N *ba ne/ce* | Ada malama ce. Ada ba malama ba ce. |
| `adjective_clause` | *be* + adjective (C7) | depends on the adjective's **type** (below) | Wannan gida babba ne. Miyar tana da zafi. |
| `locative_clause` | *be* + place (C8) | PAC (continuous) + place | Yaran suna cikin gida. Musa yana kasuwa. |
| `belong_clause` | *belong to* | X *na/ta* Y *ne/ce* | Littafin na Musa ne. |
| `possession_clause` | *have, own* (C9) | PAC (continuous) + *da* + Y; negative *ba* + pronoun + *da* | Ada tana da mota. Ba ni da mota. |
| `verbal_clause` | everything else (C1–C5, C10, C3 ditransitives), including questions and commands with a main verb | Subject + PAC + verb + receiver + object + place + time (+ *ba*) | Musa ya ba Ada littafi. |
| `where_is_clause` | *Where is X?* | *Ina* X + relative continuous PAC | Ina Musa yake? |
| `what_is_clause` | *What/Who is X?* | *Mene ne* X · *Wane ne* X | Wane ne malaminka? |
| `passive_clause` | *was repaired*, *was prepared by* (S17) | impersonal *an* + verb + thing; with *by*: doer + *ne/ce* + relative PAC | An gyara motar jiya. Ngozi ce ta shirya abincin. |
| `place_adverb_clause` | *be* + here/outside | PAC (continuous) + adverb | Muna nan. |
| `remain_future_clause` | *will remain* + adjective | future PAC + *ci gaba da* + noun | za ta ci gaba da fushi |

### Adjective types (new "type" column in the Adjectives tab)

Many English adjectives are nouns in Hausa. The `type` column tells the program which pattern to use:

| type | "X is ADJ" | "ADJ X" | Example words |
| --- | --- | --- | --- |
| adjective | Wannan gida **babba ne** | **babban** gida (A7) | big, new, small, red |
| noun with da | Miyar **tana da zafi** | miya **mai zafi** | hot, cold, loud |
| noun without da | Yaran **suna farin ciki** | yaro **mai farin ciki** | happy, angry |

### Which PAC column each tense uses

This table is `PAC_COLUMN` in `hausa_grammar.py`:

| English | PAC column | Example |
| --- | --- | --- |
| past simple, present perfect | completive | Chika **ta** sayi keke. |
| present progressive (*is cooking*) | continuous | **Tana** dafa shinkafa. |
| present simple (habits: *eats, fly*) | continuous | **Ina** cin shinkafa kullum. |
| future (*will, going to*) | future | **Za mu** tafi kasuwa gobe. |

The negatives work like this:
- Completive becomes *ba … ba*: Musa **bai** halarci taron **ba**.
- Continuous becomes *ba ya*: **Ba ya** cin nama.
- Future becomes *ba* + future + *ba*: **Ba zan** tafi **ba**.

*can* becomes PAC + *iya* + verbal noun (Ada ba ta iya iyo ba). *never* becomes negative completive + *taɓa* + verbal noun (Ban taɓa ganin komai ba). *nobody* becomes *Ba wanda* + relative PAC (Ba wanda ya zo).

### Which verb form

| After | Form | Lexicon column | Example |
| --- | --- | --- | --- |
| completive / future, noun object | before a noun | `before_noun` | ya **sayi** mota |
| completive / future, pronoun object | before a pronoun | `before_pronoun` | ya **saye** ta |
| completive / future, nothing after | plain verb | `hausa` | ya **saya** |
| before *wa* (receiver) | plain verb | `hausa` | ta **saya** wa mahaifiyarta zane |
| continuous, with object | verbal noun + object | `vn_with_object` | ina **cin** shinkafa |
| continuous, no object | verbal noun | `verbal_noun` | suna **tashi** |
| yi-verb (yi_verb = Y) | *yi* + noun / noun alone | `yi_verb` | ya **yi dariya** / suna **wasa** |

If a form column is empty, the plain verb is used. That is right for most grade 1 and grade 4 verbs.

## Phase 2 rules

### Yes/no questions (C11)

Hausa keeps the statement word order and adds the question mark: **Musa ya iso?** · **Ka gama aikin gidan?**

- *Can you …?* is a request and uses the future: **Za ka iya taimake ni?** (`ABILITY_QUESTION_COLUMN`).
- *already* in a question goes first as *har*: **Har kana tafiya?**

### Question-word questions (C12)

The question word goes **first** and the PAC changes to its **relative** form (`RELATIVE_COLUMN`):

| English | Hausa | What happens |
| --- | --- | --- |
| Who opened the door? | **Wa ya** buɗe ƙofar? | *who* is the subject: *wa* + relative completive |
| What did Musa buy? | **Me** Musa **ya saya**? | *what* is the object: *me* first; the verb has no object after it, so *saya* (not *sayi*) |
| Where did the children go? | **Ina** yaran **suka** tafi? | relative completive: *sun* → *suka* |
| Why is the baby crying? | **Me ya sa** jaririn **yake** kuka? | relative continuous: *yana* → *yake* |
| Which student solved the problem? | **Wane ɗalibi ne** ya warware matsalar? | *wane/wace/waɗanne* + noun + *ne/ce* |
| Who did not come? | Wa **bai** zo **ba**? | negatives keep the ordinary negative PAC |

The question words are in `QUESTION_WORDS` in `hausa_grammar.py`.

### Compound sentences (C13)

Clauses joined by *and / but / so* get a comma and *kuma / amma / don haka*: **Ada ta dafa abincin dare, kuma Chinedu ya wanke kwanukan.** A repeated pronoun subject is left out as usual: *…, kuma ya ci jarrabawar.*

### Commands

| English | Hausa | Rule |
| --- | --- | --- |
| Sit down. | **Zauna.** | the bare verb, no PAC |
| Please close the door. | **Don Allah ka** rufe ƙofar. | *don Allah* + subjunctive PAC |
| Do not touch that. | **Kada ka** taɓa wancan. | *kada* + subjunctive PAC |

### Experiencer verbs and verbs with two parts

Some verbs are written with extra columns in the Verbs tab:

| Verb | Hausa | Lexicon |
| --- | --- | --- |
| enjoy | tana **jin daɗin** waƙa | `vn_with_object` = *jin daɗin* |
| surprise | ya **ba** ɗaliban **mamaki** | `before_noun` = *ba*, new column `after_object` = *mamaki* |
| use | mun **yi amfani da** kyandir | `yi_verb` = *Y + da* |
| remain + adjective | suna cike da ruwa **har yanzu** | rule: *remain* = "still be" (`REMAIN_VERBS`) |

## Phase 3 rules

### Subordinate clauses (C14)

The clauses keep the English order. A subordinate clause that comes first is followed by a comma. **The linker decides the PAC** of its clause (`SUBORDINATE_PAC` in `hausa_grammar.py`):

| English | Hausa linker + PAC | Example |
| --- | --- | --- |
| when (past) | *lokacin da* + relative completive; the main clause also takes the relative completive | Lokacin da malamin ya shiga ajin, ɗaliban **suka** tashi tsaye. |
| when (not past) | *idan* + completive | Idan ka zo, za mu ci. |
| while | *yayin da* + relative continuous | Yayin da jaririn **yake** barci, … |
| if | *idan* + completive (even for English present) | Idan ka **gama** da wuri, za ka iya tafiya. |
| unless | *sai dai idan* + completive | Sai dai idan ka ba da haƙuri, … |
| before / until | *kafin / har* + subjunctive | kafin ruwan sama ya fara · har ka zo |
| after | *bayan* + relative completive | Bayan Musa ya tafi, … |
| because, since, although | *saboda, tun da, ko da yake* + the normal PAC | Saboda ya yi karatu sosai, ya ci jarrabawar. |
| **counterfactual**: If X had …, Y would have … | *da* + completive in **both** clauses | **Da** Ngozi ta iso da wuri, **da** ta haɗu da malamin. |

*may* (permission) becomes future + *iya*: za ka iya tafiya. After *iya*, a verb with no object takes its verbal noun (*iya tafiya, iya iyo*); a verb with an object keeps its verb form (*iya taimake ni*).

### Relative clauses (C15)

Noun + linker *-n/-r* + **da** + a clause with the **relative PAC**. A noun followed by a relative clause always takes the linker, never *ɗin*.

| Gap | Example | What happens |
| --- | --- | --- |
| subject | Mutumin **da ya** kira jiya kawuna ne. | no subject in the relative clause; the PAC agrees with *mutum* |
| object | Matar **da muka** ziyarta tana zama a Legas. | the verb has no object after it: *ziyarta* (not *ziyarci*) |
| whose + noun | Yarinyar da **mahaifinta** likita ne ta ci kyautar. | the owned noun takes the owner's suffix |
| whose + passive | Yaron da **aka** sace **masa** keke ya yi kuka sosai. | impersonal *aka* + the owner as *masa* |

### Reported clauses (C16)

Verb + **cewa** + clause: Na san **cewa** ta tafi. *say* + clause is **ce**, without *cewa*: Malamin ya **ce** jarrabawar tana da wuya. *tell X that* makes X the receiver: Musa ya faɗa **mini** cewa ya sayi mota.

State verbs (*know, believe*) use the completive in the simple present: **Na** san, Musa **ya** yarda (`STATIVE_VERBS`). Feelings (*admire*) use the continuous even in the simple past: ɗaliban **suke** girmamawa (`FEELING_VERBS`).

*to* + verb becomes subjunctive PAC + verb: yaran sun so **su** tafi waje · Tana fatan **ta** yi tafiya.

### Focus (S10)

The focused part goes first, then *ne/ce*, then the rest with the **relative PAC**:

| English | Hausa |
| --- | --- |
| It was Ada who cooked the soup. | **Ada ce** ta dafa miyar. |
| It was the book that Ada borrowed. | **Littafin ne** Ada ta aro. |
| It was yesterday that the teacher arrived. | **Jiya ne** malamin ya iso. |
| It is in Lagos that they live. | **A Legas ne** suke zama. |

### Passives (S17)

Hausa has no passive verb form. Without *by*, it uses the impersonal PAC: **An** gyara motar jiya · **Ba a** rufe ƙofar **ba**. With *by*, the doer is put in focus: **Ngozi ce** ta shirya abincin.

## Noun phrase rules

| Rule | Example | Where it is |
| --- | --- | --- |
| *the* becomes *-n/-r* (A6) | yaron, miyar, ɗaliban | `generate.linker` |
| …but not after a preposition (our speaker's usage) | cikin gida, a kan tebur | `DEFINITE_AFTER_PREPOSITION` |
| plurals in *-ai* drop the *-i* | ɗalibai → ɗaliban | `generate.add_suffix` |
| adjective before the noun with a linker (A7) | babban gida, sabuwar mota | `ADJECTIVE_BEFORE_NOUN` |
| noun stays singular after a number (A17) | fensir biyu | `SINGULAR_AFTER_NUMBER` |
| possessive suffix | motata, mahaifiyarta | lexicon "Possessive suffix" rows |
| owner after the noun | gidan Musa | `generate.noun_phrase` |
| this/that before the noun | wannan gida | lexicon "Demonstrative" rows |
| *many* after, *some* before | ɗalibai da yawa, wasu yara | `QUANTIFIERS` |
| masculine when the sex is unknown (A2/B11) | malami, *you* = ka | `DEFAULT_SEX` |
| a consonant-final noun takes *ɗin* for "the" | fim ɗin | `generate.linker` |
| no *-n/-r* for things there is only one of | ruwan sama ya tsaya | `UNIQUE_NOUNS` |
| no plural in the lexicon → singular in Hausa | wutar lantarki **ta** … | `NO_PLURAL_MEANS_SINGULAR` |
| *mai* becomes *masu* before a plural noun | kujeru masu kyau | `transfer.to_np` |
| adjective type "noun after linker" | waƙar gargajiya | Adjectives tab |
| *anyone / anything* in a negative → *kowa / komai* | Ban ga kowa ba. | `NEGATIVE_INDEFINITES` |
| words that are plural in Hausa (gender `pl`) | kuɗi, iyaye → *isassun kuɗi*, *iyayenka za su* | Nouns tab, gender column |
| quantifiers that agree | isasshen / isasshiyar / isassun | `AGREEMENT` |
| place names spelled differently | Lagos → Legas | `PLACE_NAMES` |
| subject pronouns left out | Sun tsabtace ajin | `DROP_SUBJECT_PRONOUNS` |

## How the lexicon chooses a word

When the workbook has several translations for one English word, the program picks in this order:
1. rows marked **Preferred**
2. then rows marked **Checked**
3. then the first row in the tab

Rows marked **Wrong** are never used.

**To change the translation the system uses, mark the row you want as Preferred.** *Preferred* is a new status in v3. It is needed because some words have two Checked rows: *finish* has *ƙare* and *gama*, and the speaker uses *gama*.

Lexicon v3 adds the words the three phases needed and marks the speaker's choices as Preferred, for example *mahaifiya* for "mother", *gama* for "finish" and *mutum* for "man". It also adds two columns: `type` in Adjectives and `after_object` in Verbs. Every change is listed in the workbook's "Changes in v3" tab.

Five common words (*wait, think, hope, tired, sick*) were added while testing sentences outside the test set. They are marked **Needs check**, not Preferred, because the speaker has not seen them.

## Evaluation

`evaluate.py` compares each output with the speaker's translation in the test set. It uses three scores:

- **Exact match:** the same sentence, ignoring capitals and punctuation.
- **chrF:** shared letter sequences, from 0 to 100. It gives part credit, which suits Hausa because one wrong suffix (*shinge* / *shingen*) is a small error.
- **BLEU:** shared word sequences, from 0 to 100. This is the standard MT score, computed over the whole set.

`outputs/eval_results.xlsx` has one row per sentence and an empty **Error type** column for the group to fill in (wrong word, wrong PAC, wrong order, missing rule, lexicon gap …). That gives you an error analysis for the report.

### Results

| | Sentences | After Phase 1 rules | After Phase 2 rules | After Phase 3 rules (final) |
| --- | --- | --- | --- | --- |
| Phase 1 | 54 | 94.4% exact · chrF 98.6 | 94.4% · 98.6 | **94.4% · 98.6** |
| Phase 2 | 28 | 14.3% · 62.1 | 89.3% · 96.7 | **89.3% · 96.7** |
| Phase 3 | 46 | 0.0% · 47.1 | 2.2% · 51.0 | **78.3% · 93.8** |
| All | 128 | 43.0% · 65.4 | 60.2% · 74.2 | **87.5% · 95.8** (BLEU 92.2) |

Each column is a "before and after" for the phase built next. Writing a later phase never changed an earlier phase's output; `evaluate.py` was re-run after every change to check.

**Important for the report:** the rules were written while looking at these sentences, so these scores are optimistic. The fair test is a held-out set of new sentences that nobody looked at while writing rules. Expect a lower score there, mostly from missing words.

### The sentences that differ

| ID | System | Speaker | Question for the speaker |
| --- | --- | --- | --- |
| 18.4 | Chika ta faɗa wa yaran labari. | Chika ta ba yaran labari. | Is *faɗa wa … labari* also correct? If only *ba* is used with *labari*, we can add a rule: tell + story → ba. |
| 49.3 | Akuyar tana bayan shinge. | Akuyar tana bayan shingen. | Your other sentences leave *-n/-r* off after a preposition (*cikin gida, a kan tebur, kusa da taga*). When is it used after *bayan*? |
| 52.4 | An yi iska jiya. | An yi iska sosai jiya. | *sosai* ("a lot") is not in the English. Is it needed, or is *An yi iska jiya* also fine? |
| 2.5 | Wutar lantarki ta fita, … | Wutar lantarki ta ɗauke, … | Lights "go out" with *ɗauke*, people "go out" with *fita*. Is *fita* possible for lights? If not, the choice depends on the subject; that needs a new rule. |
| 41.3 | Har kana tafiya? | Har za ka tafi? | Is *Har kana tafiya?* acceptable? If not: is the future always used for "be leaving / going" when it refers to a plan? |
| 51.3 | Ngozi tana jin daɗin waƙar gargajiya. | … waƙoƙin gargajiya. | English "music" is singular, but the speaker uses the plural *waƙoƙi*. Is the singular also fine? |
| 6.5 | … ya yi ritaya bara. | … shekaran da ta wuce. | Is *bara* fine for "last year"? (This was already on the list to re-check; should it be *shekarar*?) |
| 8.3 | A Legas ne suke zama. | A Legas ne suke zaune. | Sentence 6.2 uses *tana zama a Legas*. For "live", is it *zama* or *zaune*, and when? |
| 4.4 | … mahaifiyar ta tsabtace gidan … | … ta share gidan … | Sentence 1.6 uses *tsabtace* for "clean". Is *tsabtace* fine here, or is *share* (sweep) the normal word for a house? |
| 4.5 | Tun da hanyoyin suna cike da ruwa, … su tafi waje. | … sun cika da ruwa, … su fita waje. | Sentence 2.2 uses *suna cike da ruwa*. Are both fine? Is *fita* needed for "go outside"? |
| 26.4 | … cewa kasuwar ta rufe da wuri. | … cewa an rufe kasuwar da wuri. | Is *kasuwar ta rufe* acceptable, or must "the market closed" be impersonal? |
| 4.1 | … ruwan sama mai nauyi ne … 'yan kallon … | … ruwan sama yana da ƙarfi … 'yan kallo … | Heavy rain is *ƙarfi*, not *nauyi* (which is for weight); the lexicon needs a sense note. Why no *-n* on *'yan kallo* ("the fans")? |
| 12.4 | Mahaifiyarta ce ta ɗauki jaririn. | … jaririyar. | The speaker made the baby a girl because of "her". The program cannot see that; is *jaririn* acceptable? |
| 3.1, 4.3, 13.1 | literal versions (*suka gudu ciki*, *yi karatu akai-akai*, *za ka ci*) | free translations (*shiga ciki da gudu*, *dage da karatu*, *ci jarrabawa*) | Are the literal versions acceptable Hausa? If yes, the report can count them as correct. |

## Known limitations

- Free or idiomatic translations (*dage da karatu*) are out of reach: the system translates word by word, within the rules.
- Choices that depend on meaning are not made: heavy rain (*ƙarfi*) or a heavy bag (*nauyi*); lights going out (*ɗauke*) or people going out (*fita*).
- Clauses are only joined in the English order; the system never reorders them.
- *it* as an object is always *shi* (masculine), because the program does not know what *it* refers to (*Ada ba ta ci shi ba* for "Ada did not eat it", where the rice is feminine).
- Some verbs have no verbal noun in the lexicon yet. *I can read* gives *Na iya karanta* where it should be *karatu*. Fill the `verbal_noun` column.
- Where the lexicon's first translation is not the everyday one, mark the right row as Preferred.
- *you* is always singular masculine (*ka*).
- Weather words with their own subject (*Sama ya yi gajimare*) are listed in `WEATHER` in `hausa_grammar.py`.

## How to fix a wrong translation

1. Run the sentence with `python src/try_sentence.py --rules` and read "Rules used".
2. **Wrong or missing word:** fix the lexicon (mark the right row Preferred, or add the word or form).
3. **Wrong choice, but the rule is right** (preposition, adverb, a group decision): edit `hausa_grammar.py`.
4. **Wrong English labels:** run with `--analysis` and see `english_analysis_explained.md`.
5. **Wrong construction or word order:** tell the coder; a rule in `transfer_en_ha.py` or `hausa_generate.py` needs changing.
6. Run `python src/evaluate.py` and `python src/evaluate.py --hausa` again, and check that no other sentence got worse.
