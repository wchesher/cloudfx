# Copyright (c) 2026 William Chesher. MIT License, see LICENSE.
# scoring - IPIP-50 domain scoring exactly as Common Kit Section 6 specifies, with the missing-answer rule

"""
IPIP-50 scoring (Common Kit Section 6)
======================================

- Positively keyed responses are kept; reverse-keyed responses become ``6 - response``.
- The domain score is the MEAN of the answered keyed items, from 1 to 5.
- Missing-answer rule (the kit's own): one or two skipped items -> average the answered items and
  say how many there were; three or more -> the domain is NOT SCORED. A gap is never filled with
  zero or the midpoint.
- The label stays Emotional Stability (not Neuroticism).

Bands are this converter's own reading convention, declared in the profile, and deliberately wide
in the middle: a score near 3 means "no clear tendency", not a weak version of a label.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import kit
from .answers import Answers

BAND_EDGES = (
    (4.0, "clearly higher"),
    (3.5, "somewhat higher"),
    (2.51, "middle: no clear tendency"),
    (2.01, "somewhat lower"),
    (0.0, "clearly lower"),
)


def band(mean: float) -> str:
    for edge, label in BAND_EDGES:
        if mean >= edge:
            return label
    return BAND_EDGES[-1][1]


def keyed(domain: kit.Domain, item_id: str, response: int) -> int:
    return 6 - response if item_id in domain.reverse else response


@dataclass
class DomainScore:
    domain: kit.Domain
    mean: float | None
    answered: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    keyed_scores: dict[str, int] = field(default_factory=dict)

    @property
    def scored(self) -> bool:
        return self.mean is not None

    @property
    def band(self) -> str:
        return band(self.mean) if self.mean is not None else "not scored"

    @property
    def tendency(self) -> str | None:
        """Plain-language direction, only when the band is outside the middle."""
        if self.mean is None:
            return None
        if self.mean >= 3.5:
            return self.domain.higher
        if self.mean <= 2.5:
            return self.domain.lower
        return None

    def conflicts(self, min_gap: int = 2) -> list[tuple[str, str]]:
        """Pairs of items in this domain that point in opposite directions after keying, largest gap first."""
        pairs = [(h, l) for h, hs in self.keyed_scores.items() for l, ls in self.keyed_scores.items()
                 if hs >= 4 and ls <= 2 and hs - ls >= min_gap]
        return sorted(pairs, key=lambda p: (self.keyed_scores[p[1]] - self.keyed_scores[p[0]], p))


def score_domains(answers: Answers) -> list[DomainScore]:
    results = []
    for domain in kit.DOMAINS:
        answered = [i for i in domain.items if i in answers.items]
        skipped = [i for i in domain.items if i not in answers.items]
        keyed_scores = {i: keyed(domain, i, answers.items[i]) for i in answered}
        mean = None
        if len(skipped) <= 2 and answered:
            mean = round(sum(keyed_scores.values()) / len(answered), 2)
        results.append(DomainScore(domain, mean, answered, skipped, keyed_scores))
    return results


def extreme_items(answers: Answers) -> list[tuple[str, int]]:
    """Items answered 1 or 5: the person's most emphatic self-descriptions."""
    return sorted((i, r) for i, r in answers.items.items() if r in (1, 5))
