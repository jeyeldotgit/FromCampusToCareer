"""Skill extraction using spaCy PhraseMatcher.

Matches canonical skill names and their alias variants against raw posting
text. Returns a set of matched canonical skill names. This is rule-based,
not transformer-based, which keeps it deterministic and fast at scale.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import spacy
from spacy.matcher import PhraseMatcher

from core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_nlp() -> spacy.language.Language:
    """Load and cache the spaCy model (called once per process).

    Returns:
        Loaded spaCy Language object.
    """
    logger.info("Loading spaCy model: %s", settings.spacy_model)
    nlp = spacy.load(settings.spacy_model, disable=["parser", "ner"])
    return nlp


def build_matcher(skill_patterns: dict[str, str]) -> tuple[spacy.language.Language, PhraseMatcher]:
    """Build a PhraseMatcher from a {pattern_text: canonical_name} dictionary.

    Each entry in skill_patterns maps a lowercase skill string (canonical name
    or alias) to its canonical skill name.

    Args:
        skill_patterns: Mapping of lowercase pattern text to canonical skill name.

    Returns:
        Tuple of (nlp, matcher) ready for extraction.
    """
    nlp = _load_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

    # Group patterns by canonical name to add them as a single label
    by_canonical: dict[str, list[str]] = {}
    for pattern_text, canonical in skill_patterns.items():
        by_canonical.setdefault(canonical, []).append(pattern_text)

    for canonical, patterns in by_canonical.items():
        docs = list(nlp.pipe(patterns))
        matcher.add(canonical, docs)

    logger.info("PhraseMatcher built with %d canonical skill labels", len(by_canonical))
    return nlp, matcher


def extract_skills(
    text: str,
    nlp: spacy.language.Language,
    matcher: PhraseMatcher,
) -> set[str]:
    """Extract canonical skill names found in the given text.

    Args:
        text: Raw job posting text to search.
        nlp: Loaded spaCy Language object.
        matcher: Compiled PhraseMatcher.

    Returns:
        Set of matched canonical skill name strings (deduplicated).
    """
    if not text or not text.strip():
        return set()

    doc = nlp(text[:50_000])  # guard against very long descriptions
    matches = matcher(doc)
    return {nlp.vocab.strings[match_id] for match_id, _start, _end in matches}
