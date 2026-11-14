# A real judge mistake: a formal writer flagged for "losing" contractions she never uses

This is a reproducible mistake in the part of the judge that runs without a model (`features.style_fidelity`).
It was found by running the code on small fictional inputs; no real person's text is involved. It is pinned
as documented behaviour in `tests/test_judge_known_mistakes.py`. A second, LLM-side failure is described at
the end and is **untested**, because no judge model was available when this was written.

## The case

A fictional person writes formally and **never uses a contraction**. She writes "I will", "I am", "I do not".
She does use possessives: "the supplier's invoice", "Monday's meeting", "the committee's notes", "the team's data".

A response written as her keeps that register exactly:

> I am sorry, but I cannot attend. I will read the notes and reply on Friday.

The judge flags it P3, "lost signature marker: the person contracts".

## Reproduce it

From the repository root:

```bash
PYTHONPATH=src .venv/bin/python - <<'EOF'
from mefile.judge.features import PersonCorpus, style_fidelity, style_features
from mefile.judge.rubric import render_style_flags

# Fictional person: formal, never contracts, but writes possessives ('s).
corpus = PersonCorpus(
    writing={
        "W01": "Good morning. The supplier's invoice arrived today. I will review it and I will reply by Friday.",
        "W03": "I am unable to attend Monday's meeting. Please send me the committee's notes.",
    },
    explanations={"S01": "I do not change a plan unless the team's data supports it."},
)
# A response in exactly the person's register: formal, no contractions.
response = "I am sorry, but I cannot attend. I will read the notes and reply on Friday."

result = style_fidelity(response, "writing", None, corpus)
print("person 'contractions' per sample:", [style_features(t)["contractions"] for t in corpus.writing.values()])
print("categories:", result["categories"])
print(render_style_flags(result, "writing"))
EOF
```

## Actual output

```
person 'contractions' per sample: [1, 2]
categories: ['P3']
Style flags (deterministic, relative to this person; scored through style_deduction):
  - P3 "I am": lost signature marker: the person contracts (3 contractions in their own text); the response never does
  - P3 "I will": lost signature marker: the person contracts (3 contractions in their own text); the response never does
Gates: memorization=no, baseline=no
Politeness markers per 100 words: response 6.2, the person's own 3.3
Length: response 16 words; the person's own range 15-15
```

The block after `categories` is `render_style_flags`, which is exactly what the judge model is shown inside
`<computed_features>`.

Control: rewrite the person's three sentences without `'s` ("the invoice from the supplier", "the meeting on
Monday", ...) and the same response raises **no flags at all**. The possessive is the whole cause.

## Why it is wrong

- `CONTRACTION_PATTERN` in `src/mefile/judge/features.py` is `\b[A-Za-z]+['’](?:s|t|re|ve|ll|d|m)\b`. It
  matches `supplier's`, `Monday's`, `committee's` as contractions. Possessive `'s` and contracted `'s`
  ("it's", "that's") look the same to a regular expression.
- `signature_flags` then raises P3 on the first `I am` / `I will` when the person has **one or more**
  "contractions" and the response has none. One possessive anywhere in the person's samples is enough.
- The flag is the opposite of the truth: the response is faithful **because** it does not contract. The
  detail text states a false fact about the person ("the person contracts (3 contractions...)"), and the
  model reads that sentence as evidence.
- The mistake mirrors in the other direction: a person who really contracts ("I'm", "don't", "can't"), and a
  response that never contracts but mentions "Sam's place", raises **no** P3 flag, because the response's
  possessive counts as its contraction (third test in the test file).
- `docs/judge.md` says "Thin evidence means fewer flags, not false ones." This case is a false flag from
  ordinary evidence. It also hits the people the fairness rules are meant to protect: formal writers, and
  many non-native writers, who tend not to contract.
- The same counter feeds the "N contractions" figure in the style markers the model sees, so that number is
  inflated by possessives too.

## What the system does about it today

- **The flag does not set the score by itself.** For a writing answer the model must confirm (`counted: true`)
  or dismiss each flag. The code then deducts at most 1 point per counted category and at most 2 in total
  (`judge._writing_reference`). If the model confirms this flag, a 4 becomes a 3. For a scenario the flags
  are shown but never scored.
- **The model is told to dismiss flags that come from plain or non-native English.** That helps with a
  non-native writer, but this flag claims something about the person, not about the language, and the model
  has no way to check that the "3 contractions" are possessives unless it rereads her samples. Whether it
  does is not measured.
- **No quote, no flag.** The quote ("I am") is real, so this safeguard does not catch it. It stops invented
  spans, not wrong reasons.
- **Fail closed** covers broken or invalid verdicts. It does not catch a valid verdict built on a wrong flag.
- **Human blind ratings and agreement statistics** are the real check. Raters see the question, the person's
  recorded answer and the response, never the flags, so they score this response on resemblance. `agreement`
  reports exact and within-1 agreement, Spearman, weighted kappa and the three largest judge-versus-human
  disagreements. A 1-point deduction may not reach the top three, so a systematic 1-point bias against
  formal writers would show as a mean difference across items, not as one striking case.
- **The self-check does not cover it.** Its fairness probes compare polished and plain answers for DEMO01,
  who contracts. No probe has a person who never contracts.

## What we would change (not done here; judge code is unchanged)

1. Count only real contractions: `n't`, `'re`, `'ve`, `'ll`, `'m`, `'d`, and `'s` only after pronouns and
   function words (it, that, he, she, there, here, what, who, where, how, let).
2. Require real evidence before a "lost marker" flag: for example at least 2 contractions across at least
   2 samples, and the person contracting more often than writing the expanded form.
3. Put the counts in the detail ("person: 3 contracted, 5 expanded"), so the model and a human reviewer
   can see how strong the habit is.
4. Add a self-check probe: a formal person who never contracts, and a faithful formal reply, which must
   raise no P3 flag and lose no points.
5. Flip `tests/test_judge_known_mistakes.py` to assert the correct behaviour when 1 lands.

## A plausible LLM-judge failure (UNTESTED)

**Untested:** no Anthropic API key was available, so this has not been run against the judge model. It is a
reading of `src/mefile/judge/rubric.py`, not a measurement.

**Likely length bias in `profile_consistency`.** Scenario reasons are protected from length: they are
rebuilt as neutral decision cards, and the prompt says "Wording, tone and length must not affect the cards".
Writing scores are partly protected: style habits, length included, go only through the style deduction.
`profile_consistency` has no such protection. It is a free 0-4 judgment against the 55 build answers, and the
prompt asks the model to "cite the evidence IDs you relied on". A longer answer touches more topics, so it
gives the model more chances to find a matching build answer and cite it. That suggests a longer, fluent
answer would score higher on `profile_consistency` than a short answer with the same stance, even when the
short one is closer to how the person writes. LLM judges have a known tendency to favour longer answers,
and nothing in this dimension counters it. No self-check probe varies length while holding content fixed.

**How to test it:** add paired probes with the same stance at two lengths (for example 20 and 80 words) and
assert `profile_consistency` stays within 1 point. Then check the human ratings for a correlation between
response length and the judge-minus-human difference.
