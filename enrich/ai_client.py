"""Offline stub for the AI enrichment step.

This is deliberately kept simple. It looks and acts like a real client
(same method signature, same "model" identifier) so switching to a real
provider approved by ITE is a one-line change in enrich_feedback.py.

Behaviour is DETERMINISTIC. No network, no randomness. Given the same
text, it always returns the same label. That is what lets us run this in
labs and in tests without an internet connection.

The classification logic is a very ordinary keyword classifier: count how
many "positive" words the comment contains, how many "negative" words,
and pick the winner. If they tie, or neither shows up, return "neutral".

Two things about this design are on purpose:

1. The keyword lists are all English. Singlish words like "shiok", "sian",
   "jialat" or "buay tahan" are not in them, so many Singlish comments
   fall through to "neutral" even when the sentiment is clear to a human.
   The fairness discussion in Block 3 is about exactly this bias.

2. The word "damn" is on the negative list, because in most English
   corpora it IS negative. In Singlish it is an intensifier ("damn
   shiok" = super good). That single word is enough to flip several
   Singlish positives to negative. It is a good example of how a
   classifier trained on one variety of English can quietly under-serve
   speakers of another.

Failure simulation:
    AI_STUB_FAIL=1  makes every classify() call raise an exception, so
    participants can see the fallback path taken in enrich_feedback.py.
"""

import os
import re

# --- Keyword lists ---------------------------------------------------------

POSITIVE_WORDS = {
    "enjoyed", "enjoy", "great", "best", "love", "loved", "excellent",
    "understand", "useful", "helpful", "helpfull", "engaging", "appreciated",
    "relevant", "interesting", "fair", "rewarding", "good", "thanks",
    "motivated", "learned", "fun", "well",
}

NEGATIVE_WORDS = {
    "stress", "stressed", "stressful", "confusing", "confused", "confuse",
    "frustrating", "boring", "unclear", "hard", "difficult", "exhausting",
    "lost", "unfair", "terrible", "wasted", "waste", "overwhelmed",
    "struggling", "dread", "chaotic", "hate", "cannot", "damn", "dragged",
    "bad",
}

# Multi-word negative phrases (matched as substrings, case-insensitive).
NEGATIVE_PHRASES = {
    "too tight", "too fast", "too much", "give up", "no life",
}

WORD_RE = re.compile(r"[A-Za-z']+")


class OfflineStubClient:
    """A tiny classifier that pretends to be an AI service."""

    model_id = "offline-stub-v1"

    def classify(self, text, labels):
        """Return one of `labels`, chosen by keyword counts.

        The `labels` list is honoured: if a caller asks for labels the
        stub doesn't know, "neutral" (or the first label) is returned.
        """
        if os.environ.get("AI_STUB_FAIL") == "1":
            raise RuntimeError("Simulated AI outage (AI_STUB_FAIL=1)")

        text_lower = text.lower()
        tokens = set(WORD_RE.findall(text_lower))

        positive = len(tokens & POSITIVE_WORDS)
        negative = len(tokens & NEGATIVE_WORDS)
        # Phrase hits count as one negative each.
        negative += sum(1 for p in NEGATIVE_PHRASES if p in text_lower)

        if positive > negative and "positive" in labels:
            return "positive"
        if negative > positive and "negative" in labels:
            return "negative"
        if "neutral" in labels:
            return "neutral"
        return labels[0]


# Module-level instance. To use a real provider approved by ITE, replace
# this one line - e.g. `ai_client = MyRealClient(api_key=os.environ[...])`.
ai_client = OfflineStubClient()
