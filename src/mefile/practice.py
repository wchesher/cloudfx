# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# practice - the practice library for rehearsing with your understudy, and "ask your own" questions

"""
Practice library
================

Everyday workplace situations, written for the product. They are NOT the Common Kit's questions
and are never used for scoring, profiles or evaluation. They exist so a person can see how their understudy
(Claude, an AI) answers as them, and mark each answer "sounds like me" or "not me".

Prompts follow the same shape as the kit's question prompts (the shape me.md's instructions are written for):
scenarios ask for a letter and one sentence within 60 words; writing tasks ask for the message only within 80
words. "Ask your own" questions are wrapped the same way, so the understudy answers in the person's voice and format.
"""

from __future__ import annotations

from dataclasses import dataclass

from .answers import Question

SCENARIO_LIMIT = 60
WRITING_LIMIT = 80
OWN_QUESTION_MAX_CHARS = 600


@dataclass(frozen=True)
class Situation:
    id: str
    topic: str
    type: str  # "scenario" | "writing"
    wording: str
    options: dict[str, str] | None = None


LIBRARY: tuple[Situation, ...] = (
    Situation("P01", "Deadlines", "scenario",
              "Your manager moves a deadline up by a week. You think the quality will suffer.",
              {"A": "Agree and work late to make it.", "B": "Say what can be done well by the new date, and what cannot.",
               "C": "Ask which other work can be dropped to make room.", "D": "Agree in the moment and raise concerns later in writing."}),
    Situation("P02", "Feedback", "scenario",
              "A peer asks for honest feedback on a presentation you thought was weak.",
              {"A": "Give two specific things to fix, privately.", "B": "Start with what worked, then one change.",
               "C": "Keep it general and encouraging.", "D": "Suggest you go through it together before the next one."}),
    Situation("P03", "Meetings", "scenario",
              "A recurring meeting has stopped being useful, but it is the team lead's favourite.",
              {"A": "Propose cutting it in the meeting.", "B": "Suggest a shorter format to the lead privately.",
               "C": "Keep attending and say nothing.", "D": "Stop attending and send updates in writing instead."}),
    Situation("P04", "Workload", "scenario",
              "Two people senior to you each ask for something urgent by the same afternoon.",
              {"A": "Ask both to agree on the priority between them.", "B": "Decide yourself and tell them both.",
               "C": "Do the quicker one first and apologise to the other.", "D": "Ask your own manager to decide."}),
    Situation("P05", "Mistakes", "scenario",
              "You notice a mistake in a report you sent to a client yesterday. Nobody has spotted it.",
              {"A": "Tell the client today with the correction.", "B": "Tell your manager first and agree how to handle it.",
               "C": "Fix it in the next version without mentioning it.", "D": "Wait to see if anyone notices."}),
    Situation("P06", "Help", "scenario",
              "A new colleague keeps asking you questions that slow down your own work.",
              {"A": "Set a daily slot for their questions.", "B": "Point them to the documentation first.",
               "C": "Keep answering as they come.", "D": "Ask your manager to arrange more onboarding."}),
    Situation("P07", "Disagreement", "scenario",
              "In a group decision, everyone favours an option you think will cause problems later.",
              {"A": "Make the case once, clearly, then support the group.", "B": "Ask the group to list the risks first.",
               "C": "Go along with it and note your concern in writing.", "D": "Talk to the decision-maker afterwards."}),
    Situation("P08", "Change", "scenario",
              "Your team is told to switch to a new tool next month. You liked the old one.",
              {"A": "Volunteer to help others learn the new one.", "B": "Ask why the change was made before deciding what you think.",
               "C": "Use the new tool only where you have to.", "D": "Raise the old tool's strengths with whoever decided."}),
    Situation("P09", "Recognition", "scenario",
              "Your manager thanks the team in an all-hands for work you mostly did alone.",
              {"A": "Leave it; the team got the win.", "B": "Mention your part to your manager privately.",
               "C": "Add a short note in the chat about what you did.", "D": "Bring it up at your next one-to-one."}),
    Situation("P10", "Uncertainty", "scenario",
              "You must choose between two approaches with no clear data. A wrong choice costs a week.",
              {"A": "Pick one now and set a checkpoint to review it.", "B": "Run a small test of both first.",
               "C": "Ask someone experienced to choose.", "D": "Wait a few days for more information."}),
    Situation("P11", "Conflict", "scenario",
              "Two teammates are openly frustrated with each other and it is affecting the work.",
              {"A": "Talk to each of them separately.", "B": "Bring them together to clear the air.",
               "C": "Stay out of it unless it gets worse.", "D": "Let your manager know what you are seeing."}),
    Situation("P12", "Boundaries", "scenario",
              "A colleague regularly messages you about work late in the evening.",
              {"A": "Reply the next morning without comment.", "B": "Tell them what hours you check messages.",
               "C": "Reply when you see it to keep things moving.", "D": "Turn off notifications and say nothing."}),
    Situation("P13", "Saying no", "writing",
              "A colleague asks you to take on a task you do not have time for this week. Write your reply."),
    Situation("P14", "Good news", "writing",
              "Your team just shipped something difficult. Write the message you post in the team channel."),
    Situation("P15", "Running late", "writing",
              "You will miss a deadline you promised a colleague by two days. Write the message you send them."),
    Situation("P16", "Asking for help", "writing",
              "You are stuck on a problem a colleague in another team knows well. Write your first message to them."),
    Situation("P17", "Pushing back", "writing",
              "A senior colleague asks for a change you think is a mistake. Write your reply in the shared document."),
    Situation("P18", "Thanks", "writing",
              "Someone stayed late to help you finish urgent work. Write the message you send them the next day."),
    Situation("P19", "Introductions", "writing",
              "You are joining a new project team. Write your first message in their chat."),
    Situation("P20", "A tricky follow-up", "writing",
              "A client has not replied to your last two emails about an overdue decision. Write the third email."),
)

BY_ID = {s.id: s for s in LIBRARY}


def prompt_for(situation: Situation) -> str:
    if situation.type == "scenario":
        options = "\n".join(f"{letter}. {text}" for letter, text in (situation.options or {}).items())
        return (f"Choose A, B, C or D and give one sentence explaining why. Use no more than {SCENARIO_LIMIT} words in total."
                f"\n\n{situation.wording}\n\n{options}")
    return f"Write the actual message you would send. Use no more than {WRITING_LIMIT} words.\n\n{situation.wording}"


def as_question(situation: Situation) -> Question:
    return Question(id=situation.id, type=situation.type, wording=situation.wording, options=situation.options,
                    word_limit=SCENARIO_LIMIT if situation.type == "scenario" else WRITING_LIMIT,
                    prompt=prompt_for(situation))


def own_question(text: str, kind: str = "open") -> Question:
    """Wrap a person's own situation so the understudy answers in their voice and within a word limit."""
    text = " ".join(str(text or "").split())
    if not text:
        raise ValueError("write a situation first")
    if len(text) > OWN_QUESTION_MAX_CHARS:
        raise ValueError(f"keep it under {OWN_QUESTION_MAX_CHARS} characters")
    if kind == "message":
        prompt = f"Write the actual message you would send. Use no more than {WRITING_LIMIT} words.\n\n{text}"
        return Question(id="OWN", type="writing", wording=text, options=None, word_limit=WRITING_LIMIT, prompt=prompt)
    prompt = ("Say what you would do and why, in your own voice, in one or two sentences. "
              f"Use no more than {SCENARIO_LIMIT} words.\n\n{text}")
    return Question(id="OWN", type="open", wording=text, options=None, word_limit=SCENARIO_LIMIT, prompt=prompt)


def library_json() -> list[dict]:
    return [{"id": s.id, "topic": s.topic, "type": s.type, "wording": s.wording, "options": s.options,
             "word_limit": SCENARIO_LIMIT if s.type == "scenario" else WRITING_LIMIT, "prompt": prompt_for(s)}
            for s in LIBRARY]
