#!/usr/bin/env python3
"""
Task 4: camp signal -- which side a substantive commenter is actually
arguing for: "own-display-type" (masonry as a new, separate `display:
masonry` layout mode -- the issue's own proposal) vs. "grid-extension"
(masonry folded into `display: grid` via `grid-template-rows/columns:
masonry`).

Grounded in real vocabulary read directly from the thread: commenters
repeatedly use a shared "CASE 1" (separate display type) / "CASE 2" (part
of grid) framing, plus recurring stance phrases quoted in each pattern's
comment below. Rule-based on purpose -- every label traces to a matched
phrase, debuggable at spot-check time instead of a black box.

Preprocessing (added after spot-check round 1 found real bugs):
  - Markdown blockquote lines (`> ...`, used constantly to quote the
    person being replied to) are stripped before scoring. Without this,
    a comment arguing AGAINST a quoted position was scored as if it held
    that position -- e.g. fantasai quoting @alisonmaher's "own display
    type" argument in order to rebut it was misread as fantasai's own
    stance. This was the single biggest source of spot-check mismatches.
  - Backticks are stripped so patterns match code-formatted terms like
    `` `display:grid` `` the same as plain "display:grid".
  - Two overfit/ambiguous patterns were found and removed/tightened in
    spot-check round 2: a generic "masonry in grid" GRID_EXTENSION
    pattern fired inside negated OWN_DISPLAY_TYPE phrases ("never been a
    fan of including masonry in grid"), and "evolve independently" fired
    the wrong way inside a negated sentence ("hasn't been a strong need
    ... to evolve independently"). See SPOT_CHECK.md for the full trail.

NOT run on is_meeting_transcript comments (IRC logs report OTHERS'
positions in third person, not the poster's own stance).

Output: camp label + matched phrase(s) as evidence, per comment; then a
per-author aggregate fallback for comments with no direct signal (many
replies don't restate a full position every time).
"""
import json
import re
from collections import defaultdict, Counter

OWN_DISPLAY_TYPE = [
    (r"own (display )?type", 2),
    (r"new display type", 2),
    (r"separate(?:d|ing)?\s+(?:the\s+)?(?:display\s+)?(?:layout\s+)?(?:type|property|mode|spec)", 2),
    (r"separat(?:e|ing)\s+masonry\s+(?:from|and)\s+grid", 2),
    (r"split(?:ting)?\s+the\s+layout\s+models", 2),
    (r"\bcase\s*1\b", 1),
    (r"never\s+been\s+a\s+fan\s+of\s+(?:including\s+)?masonry\s+in\s+grid", 2),
    (r"unshippable", 1),
    (r"unfixable", 1),
    (r"\+1[^.\n]{0,20}display:\s*masonry", 2),
    (r"display:\s*masonry[^.\n]{0,25}\+1", 2),
    (r"display:\s*masonry[^.\n]{0,40}(?:is\s+)?(?:clearer|better|more intuitive|makes more sense)", 2),
    (r"prefer(?:s|red)?\s+(?:this\s+)?(?:approach|proposal)?[^.\n]{0,30}display:\s*masonry", 1),
    (r"support(?:ing)?\s+(?:the\s+)?(?:idea\s+of\s+)?(?:a\s+)?(?:new\s+|separate\s+)?display\s*:\s*masonry", 1),
]

GRID_EXTENSION = [
    (r"part\s+of\s+(?:the\s+)?grid(?:\s+layout)?", 2),
    (r"integrat(?:e|ed|ing)\s+(?:as\s+part\s+of\s+|into\s+)?(?:the\s+)?grid", 2),
    (r"adding\s+masonry\s+to\s+display\s*:\s*grid", 2),
    (r"grid-template-(?:rows|columns)\s*:\s*masonry", 2),
    (r"masonry\s+within\s+grid", 1),  # tightened from generic "...in grid" after spot-check:
    # "in grid" alone is too generic and fires inside negated phrases like
    # "never been a fan of including masonry in grid" (an OWN_DISPLAY_TYPE
    # stance, not grid-extension). "within" is the actual recurring term.
    (r"\bcase\s*2\b", 1),
    (r"keep(?:ing)?\s+masonry\s+(?:in|part\s+of|unified\s+with)\s+grid", 2),
    (r"extend(?:ing)?\s+grid", 1),
    (r"gracefully\s+degrades\s+to[^.\n]{0,20}grid", 1),
    (r"masonry\s+(?:layout\s+)?should\s+be\s+integrated\s+as\s+part\s+of\s+(?:the\s+)?grid", 2),
]


def strip_quoted(text):
    """Drop markdown blockquote lines and backticks so we only score the
    commenter's own words, not text they're quoting to reply to."""
    lines = [ln for ln in text.split("\n") if not ln.strip().startswith(">")]
    return "\n".join(lines).replace("`", "")


def score_text(text, patterns):
    hits, total = [], 0
    for pat, weight in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            hits.append(m.group(0))
            total += weight
    return total, hits


MARGIN_THRESHOLD = 2  # min score gap to call it rather than "ambiguous" --
# added after spot-check found a 2-vs-1 margin mislabeling a co-editor's
# neutral both-sides framing as advocacy. A 1-point gap is noise, not signal.

def classify(body):
    text = strip_quoted(body)
    own_score, own_hits = score_text(text, OWN_DISPLAY_TYPE)
    ext_score, ext_hits = score_text(text, GRID_EXTENSION)
    if own_score == 0 and ext_score == 0:
        return "no-signal", [], own_score, ext_score
    margin = own_score - ext_score
    if margin >= MARGIN_THRESHOLD:
        return "own-display-type", own_hits, own_score, ext_score
    if -margin >= MARGIN_THRESHOLD:
        return "grid-extension", ext_hits, own_score, ext_score
    return "ambiguous", own_hits + ext_hits, own_score, ext_score


def main():
    with open("data/raw/comments_raw.json") as f:
        raw = json.load(f)
    with open("data/processed/comments.json") as f:
        processed = json.load(f)
    raw_by_id = {c["id"]: c for c in raw}

    for p in processed:
        if p["is_meeting_transcript"]:
            p["camp"] = {"label": "not-applicable", "evidence": [], "own_score": 0, "ext_score": 0}
            continue
        body = raw_by_id[p["id"]]["body"]
        label, hits, own_score, ext_score = classify(body)
        p["camp"] = {"label": label, "evidence": hits[:5], "own_score": own_score, "ext_score": ext_score}

    # Per-author aggregate fallback for comments with no direct signal.
    agg = defaultdict(lambda: {"own": 0, "ext": 0})
    for p in processed:
        if p["is_meeting_transcript"]:
            continue
        agg[p["author"]]["own"] += p["camp"]["own_score"]
        agg[p["author"]]["ext"] += p["camp"]["ext_score"]

    author_camp = {}
    for author, s in agg.items():
        if s["own"] == 0 and s["ext"] == 0:
            author_camp[author] = "no-signal"
        elif s["own"] > s["ext"]:
            author_camp[author] = "own-display-type"
        elif s["ext"] > s["own"]:
            author_camp[author] = "grid-extension"
        else:
            author_camp[author] = "ambiguous"

    for p in processed:
        if p["is_meeting_transcript"]:
            p["camp"]["effective_label"] = "not-applicable"
            p["camp"]["effective_source"] = "not-applicable"
        elif p["camp"]["label"] != "no-signal":
            p["camp"]["effective_label"] = p["camp"]["label"]
            p["camp"]["effective_source"] = "this-comment"
        else:
            author_label = author_camp[p["author"]]
            p["camp"]["effective_label"] = author_label
            p["camp"]["effective_source"] = "author-aggregate" if author_label != "no-signal" else "no-signal"

    with open("data/processed/comments.json", "w") as f:
        json.dump(processed, f, indent=2)

    label_counts = Counter(p["camp"]["effective_label"] for p in processed)
    src_counts = Counter(p["camp"]["effective_source"] for p in processed)
    n_authors = sum(1 for v in author_camp.values() if v not in ("no-signal", "ambiguous"))
    print("effective_label counts:", dict(label_counts))
    print("effective_source counts:", dict(src_counts))
    print(f"authors with a determined camp: {n_authors} / {len(author_camp)}")


if __name__ == "__main__":
    main()
