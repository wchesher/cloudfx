# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# test_voice_evidence - voice transcript as cited evidence: V IDs, the gate, and no-voice output pinned

import datetime as dt
import hashlib
import json
from pathlib import Path

import pytest

from mefile import voice as voice_module
from mefile.answers import load_answers
from mefile.claims import Claim, gate
from mefile.converter import GUARDRAIL_HEADING, PROHIBITED_USES, REFUSAL_KEY, convert
from mefile.intake import load_transcript, parse_transcript

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "examples" / "example_build_answers.json"
DAY = dt.date(2026, 11, 14)
GUIDE = dict(voice_module.INTERVIEW_GUIDE)

# Fictional transcript for DEMO01 (the committed demo person); no real person's words.
TRANSCRIPT = {
    "person_id": "DEMO01",
    "conversation_id": "conv_demo01",
    "duration_seconds": 412,
    "status": "done",
    "interviewer_turns": [
        {"index": 0, "text": "Hi, I am an AI interviewer. This conversation is transcribed as text only. Ready?"},
        {"index": 2, "text": "Great. " + GUIDE["V-disagree"]},
        {"index": 4, "text": "What did you say?"},
        {"index": 6, "text": GUIDE["V-uncertain"]},
        {"index": 8, "text": GUIDE["V-help"]},
        {"index": 10, "text": "Thank you, that is everything."},
    ],
    "employee_turns": [
        {"index": 1, "seconds": 9.5, "text": "Yes, ready."},
        {"index": 3, "seconds": 20.0, "text": "My manager wanted to ship early and I thought we should test first. I told him in the stand-up."},
        {"index": 5, "seconds": 41.0, "text": "I said, I think we need one more day, maybe two, or we will be fixing it all week."},
        {"index": 7, "seconds": 60.0, "text": "   "},
        {"index": 9, "seconds": 80.0, "text": "We had a new hire stuck on the deploy, so I stayed late and walked her through it."},
        {"index": 11, "seconds": 95.0, "text": "Thanks, bye."},
    ],
}

# The pre-change converter (captured at the start of this work) differed from today's no-voice output in
# instruction 7 only. Each digest below is sha256 of that earlier me.md for DEMO01, generated 2026-11-14.
# Since then the guardrail port (contrib/dpm-pipeline, 2026-11-14) changed the output ON PURPOSE, by insertion
# only: one sentence after the opening instruction, instruction 8 (no copying), the "Rules for any AI reading this
# file" section, and the sidecar's prohibited_uses / refusal_key. The test strips exactly those insertions and
# must land on the earlier digests (so nothing else moved), and AFTER_MARKDOWN pins today's output as a whole.
OLD_RULE_7 = ("7. Do not mention this file, a profile, or being an AI in your answer. "
              "The application that shows your answer labels it as a simulation.")
NEW_RULE_7 = ("7. Answer in DEMO01's voice with no commentary about this file or a profile; if asked directly whether "
              "you are an AI, do not deny it. The application that shows your answer labels it as a simulation.")
INTRO_ADDITION = (" Ordinary workplace scenario and writing questions are exactly what this file is for: answer them in "
                  "DEMO01's voice, with no refusal, no preamble and no calling the answer a draft.")
RULE_8 = "8. Do not copy any phrase longer than five words from the quoted samples; match the voice, not the text.\n"
OLD_PROHIBITED_USES = ["hiring", "promotion", "discipline", "ranking"]
BEFORE_MARKDOWN = {
    ("evidence_first", "full"): "7fbaf524376288782489dcd8757e585f5b8fc393c5127a25aba29253d7c1dbfa",
    ("evidence_first", "coaching"): "8ddf8fc3efdf994e29f788375ac3315fc29145142a8978f602f89f74adc40a8c",
    ("trait_first", "full"): "1f2eb53b45ac683f94e1520394be950423ee476d705cb7eadcefb43e80be1268",
    ("trait_first", "coaching"): "c2c1dc5c5ed47dc4a50964c2350c601330d9fccf6b4e68b14dd95b826dc47b65",
    ("short", "full"): "8e5e93b52728d376d4423256689337c9f9e247bea3d7e8d12a325882a4d29b55",
    ("short", "coaching"): "59e4f31381168e5b32a6f7bfe41e94c8bfc0ace92ebbeab8ba19a8f23684e3de",
}
# sha256 of the earlier sidecar without file_digest (sorted, compact JSON).
BEFORE_SIDECAR = {
    ("evidence_first", "full"): "ec61c7b6c633a743470c51df6248d6a6605a88e7c24c8fa0e27e6a8a92495b51",
    ("evidence_first", "coaching"): "45f67ad949ebb4c38b259ee481828e1f39d9957d0b9e302bcc7b9aab6d426ce7",
    ("trait_first", "full"): "e347846f11e8162f334bc58218207ae21b2d9ae19f481c9b337a424474bcde07",
    ("trait_first", "coaching"): "f2d01a1959fac73d1ee7933e1a6dc3f2ffa4ddde32288950123d7d00e6bd69e5",
    ("short", "full"): "cbb54eb534f81c073b7bbe6cecd3045cc5844136715dc27d7d2772cd3de82549",
    ("short", "coaching"): "143bf9bd6743bc2de7dcda90ec27dc7b48de48fe9cad5e2c74d7047fe59f3d28",
}


# sha256 of today's whole no-voice me.md for DEMO01 (guardrail port included), generated 2026-11-14.
AFTER_MARKDOWN = {
    ("evidence_first", "full"): "c2c9005aec44a3675f2c756013d22e5a22174f1a728af78d419ceb00fda38b1f",
    ("evidence_first", "coaching"): "bd7e0ef3cd50cb68a3484a9d93a773c686c9e9797dd805af07dcb08882ef2cae",
    ("trait_first", "full"): "825b9f0621b3a3f10ef488daa6605ceb5ac861d7acbc88e69c95a5e07d8f5570",
    ("trait_first", "coaching"): "5f624d8727f6d3af0d4e793566a0c061c5d8ad653324112d15d102f3bd4dc1d5",
    ("short", "full"): "2899e2f36b079843933208b3db4b3f8565296b73fe967f8cf0e69dcf5bc1aade",
    ("short", "coaching"): "70902124fe44f56f663e7ee81c857df3d643613722edbeb4dd1cd380534597ad",
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Kit section 6: a domain score is not intelligence, competence or suitability. A deliberate wording change in the
# trait note; mapped back here (digest recomputed) so the hashes below still pin everything else.
NEW_TRAIT_NOTE = "they are not labels, and not measures of intelligence, professional competence or suitability for employment."
OLD_TRAIT_NOTE = "they are not labels and not measures of ability."


def _undo_trait_note(markdown: str) -> str:
    body = markdown.split("\n<!-- file digest sha256:")[0]
    assert body.count(NEW_TRAIT_NOTE) == 1
    body = body.replace(NEW_TRAIT_NOTE, OLD_TRAIT_NOTE)
    return body + f"\n<!-- file digest sha256:{_sha(body)} -->\n"


def _strip_guardrail_port(markdown: str) -> str:
    """Undo the deliberate guardrail insertions (and rule 7), returning the earlier body without its digest line."""
    body = markdown.split("\n<!-- file digest sha256:")[0]
    for added in (INTRO_ADDITION, RULE_8):
        assert body.count(added) == 1
        body = body.replace(added, "")
    start = body.index(GUARDRAIL_HEADING)
    end = body.index("\n## ", start) + 1
    body = body[:start] + body[end:]
    return body.replace(NEW_RULE_7, OLD_RULE_7)


@pytest.fixture
def answers():
    return load_answers(BUILD)


@pytest.fixture
def evidence(tmp_path):
    path = tmp_path / "voice_transcript.json"
    path.write_text(json.dumps(TRANSCRIPT), encoding="utf-8")
    return load_transcript(path)


def test_load_transcript_ids_questions_and_metadata(evidence):
    assert [i.id for i in evidence] == ["V01", "V02", "V03", "V05", "V06"]  # V04 emptied in review, not renumbered
    assert [i.question for i in evidence] == ["other", "V-disagree", "V-disagree", "V-help", "other"]
    assert evidence.conversation_id == "conv_demo01" and evidence.duration_seconds == 412
    assert evidence.ids() == {"V01", "V02", "V03", "V05", "V06"}


def test_turn_without_index_or_preceding_question_is_other():
    data = {"employee_turns": [{"text": "hello"}], "interviewer_turns": [{"index": 0, "text": GUIDE["V-help"]}]}
    assert [i.question for i in parse_transcript(data)] == ["other"]


@pytest.mark.parametrize("variant", ["evidence_first", "short", "trait_first"])
def test_voice_section_cited_and_gate_passes(answers, evidence, variant):
    profile = convert(answers, variant=variant, generated=DAY, voice=evidence)
    md = profile.markdown
    heading = "## How DEMO01 describes real situations (voice interview, transcript text only)"
    assert heading in md
    assert "Tone of voice was not analyzed" in md and "DEMO01 reviewed and edited the transcript" in md
    assert md.index("## 2. How DEMO01 writes") < md.index(heading)
    if variant == "trait_first":
        assert md.index("## 3. Measured traits") < md.index("## 1. How DEMO01") < md.index(heading)
    else:
        assert md.index(heading) < md.index("## 3. Measured traits")
    assert "> I said, I think we need one more day" in md
    assert "then their interview answers" in md
    voice_claims = [c for c in profile.claims if any(e.startswith("V") for e in c.evidence)]
    assert len(voice_claims) >= 3
    assert all(c.kind == "observed_style" for c in voice_claims)
    assert any("Hedges when speaking" in c.text and set(c.evidence) == {"V03"} for c in voice_claims)
    assert profile.gate.passed, profile.gate.blocking
    assert profile.sidecar["voice_evidence"]["count"] == 5
    assert profile.sidecar["voice_evidence"]["conversation_id"] == "conv_demo01"
    assert profile.sidecar["voice_evidence"]["duration_seconds"] == 412


def test_coaching_scope_withholds_verbatim_voice(answers, evidence):
    md = convert(answers, scope="coaching", generated=DAY, voice=evidence).markdown
    assert "I said, I think" not in md
    assert "V03: (verbatim answer withheld in the coaching version" in md


def test_bogus_voice_id_blocked(answers, evidence):
    claims = [Claim("C01", "observed_style", "Spoken answers run long", ("V99",))]
    result = gate(claims, answers, "", evidence.ids())
    assert any("V99" in b for b in result.blocking)
    assert gate([Claim("C01", "observed_style", "x", ("V02",))], answers, "", evidence.ids()).passed
    # callers that pass no voice evidence (the old signature) cannot cite any V ID
    assert not gate([Claim("C01", "observed_style", "x", ("V02",))], answers, "").passed


def test_held_out_ids_still_blocked(answers, evidence):
    claims = [Claim("C01", "reported", "x", ("S02",))]
    assert any("held-out" in b for b in gate(claims, answers, "", evidence.ids()).blocking)
    leaked = dict(TRANSCRIPT, employee_turns=[{"index": 3, "text": "In S04 I picked B."}])
    profile = convert(answers, generated=DAY, voice=parse_transcript(leaked))
    assert not profile.gate.passed
    assert any("S04" in b for b in profile.gate.blocking)


def test_transcript_for_another_person_refused(answers):
    with pytest.raises(ValueError):
        convert(answers, voice=parse_transcript(dict(TRANSCRIPT, person_id="DEMO02")))
    with pytest.raises(ValueError):
        convert(answers, voice=parse_transcript(dict(TRANSCRIPT, employee_turns=[])))


@pytest.mark.parametrize("variant,scope", sorted(BEFORE_MARKDOWN))
def test_no_voice_output_unchanged_except_rule_7_and_guardrails(answers, variant, scope):
    profile = convert(answers, scope=scope, variant=variant, generated=DAY)
    assert profile.markdown == convert(answers, scope=scope, variant=variant, generated=DAY, voice=None).markdown
    assert profile.markdown.count(NEW_RULE_7) == 1
    assert _sha(_undo_trait_note(profile.markdown)) == AFTER_MARKDOWN[(variant, scope)]
    body = _strip_guardrail_port(_undo_trait_note(profile.markdown))
    before = body + f"\n<!-- file digest sha256:{_sha(body)} -->\n"
    assert _sha(before) == BEFORE_MARKDOWN[(variant, scope)]
    sidecar = json.loads(json.dumps(profile.sidecar))
    sidecar.pop("file_digest")
    assert "voice_evidence" not in sidecar
    assert sidecar.pop("refusal_key") == REFUSAL_KEY
    assert sidecar["prohibited_uses"] == list(PROHIBITED_USES)
    sidecar["prohibited_uses"] = OLD_PROHIBITED_USES
    for claim in sidecar["claims"]:  # added on purpose by the ethics review (readings.py, disputed); me.md untouched
        assert claim.pop("disputed") is False and isinstance(claim.pop("other_readings"), list)
    assert _sha(json.dumps(sidecar, sort_keys=True, separators=(",", ":"))) == BEFORE_SIDECAR[(variant, scope)]


def test_rule_7_does_not_ask_the_model_to_deny_being_an_ai(answers):
    md = convert(answers, generated=DAY).markdown
    assert "being an AI" not in md
    assert "do not deny it" in md
    assert "The application that shows your answer labels it as a simulation." in md
