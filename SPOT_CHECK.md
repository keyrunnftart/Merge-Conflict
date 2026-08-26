# Task 3 & 4 manual spot-check

Both automated passes (sentiment, camp) were manually sanity-checked
against the actual comment text before being treated as ground truth for
the eventual graph, per instruction. This file records the methodology,
what was found, what was fixed, and what remains a documented limitation.

## Task 3: sentiment (VADER compound score)

**Method:** ran `scripts/sentiment.py` (VADER) over all 132 comments,
then read the actual body text (via `data/raw/`, never committed) for the
5 most negative, 5 most positive, and 5 near-zero comments, and judged
by eye whether the score matched an honest read of the tone.

**Result: mixed. Real, systematic limitations found — not fixed, because
fixing them would mean hand-tuning a sentiment lexicon for one thread,
which stops being "lightweight" and starts being curve-fitting.**

Matches (score direction and rough magnitude are right):
- tabatkins (-0.948), rachelandrew (-0.753): genuine critical/disagreement
  tone, correctly read as negative.
- cat394 (0.992): genuinely warm, thank-you-toned reply, correctly
  positive.
- rachelandrew (0.000, different comment): genuinely neutral informational
  reply, correctly near-zero.

Systematic mismatches found:
1. **Calm technical rebuttal reads as strongly negative.** chrisarmstrong
   (-0.803) and nicoburns (-0.757) are measured, non-hostile disagreement
   — VADER's lexicon treats words like "problem", "mistake", "badly",
   "exacerbate" as negative regardless of whether the overall comment
   is emotionally negative or just describing tradeoffs analytically.
2. **Neutral procedural text reads as negative.** fantasai's comment
   listing spun-off GitHub issues (-0.705) is purely administrative —
   the word "Breaking" (as in "breaking issues out") triggered the
   lexicon's negative sense of "break."
3. **Confident, critical technical argument reads as maximally
   positive.** tabatkins's tl;dr calling the current spec "unshippable"
   and "unfixable" scored 0.999 — other words in a long, structured
   comment outweighed the pointed criticism.
4. **Short affirmations score exactly 0 (neutral) when they're actually
   mild positive support in context** — "+1 for display:masonry",
   "+1 to Tab's and Rachel's comments" — VADER's lexicon has nothing to
   key on in text that short.
5. **Automated meeting-transcript comments (css-meeting-bot, 3 comments)
   score as strongly positive (0.994–0.998) but this is meaningless** —
   it's an IRC log of a multi-person meeting, not one person's sentiment.

**Decision:** keep VADER compound score as a coarse, documented-limitation
signal (per the original "lightweight sentiment analysis" scope), but:
- `is_meeting_transcript: true` comments (css-meeting-bot, 3 of 132) are
  flagged and should be excluded from any per-author sentiment encoding
  in the graph — their score is not a real person's sentiment.
- Sentiment should be treated as a **secondary** signal in the eventual
  graph, not the primary contested-ness measure — the validated reaction
  data (real 👍/👎 counts, already checked against the 100-comment sample
  and the full 132) is the stronger, less ambiguous signal for that.

## Task 4: camp classification

**Method:** rule-based classifier (`scripts/camp.py`) matching real
phrases read directly from the thread — commenters repeatedly use a
shared "CASE 1" (separate `display: masonry`) / "CASE 2" (masonry folded
into `display: grid`) framing, plus recurring stance phrases. Every label
traces to a matched phrase (`evidence` field), so it's debuggable, not a
black box. Spot-checked against 14 comments I read in full myself first
(the same ones used to build the pattern vocabulary, plus a couple
picked blind afterward), covering both camps and genuinely ambiguous
cases, per instruction.

**Round 1 found 2 real bugs, both fixed:**
1. **Blockquoted text was being scored as the commenter's own stance.**
   fantasai quoting `@alisonmaher`'s argument *in order to rebut it* was
   misread as fantasai personally advocating that argument. Fixed by
   stripping markdown `> ` blockquote lines before scoring. This was the
   single biggest source of mismatches.
2. **Backtick-wrapped code terms weren't matching.** nmn's "support for
   adding masonry to `` `display:grid` ``" didn't match because the
   regex expected plain text. Fixed by stripping backticks before
   scoring.

**Round 2 found 2 more real bugs after re-checking, both fixed:**
3. A generic "masonry in grid" pattern (meant to catch "masonry within
   Grid") also matched inside the negated phrase "never been a fan of
   **including masonry in grid**" — scoring rachelandrew's clearly
   own-display-type comment as contested. Tightened to require the
   actual recurring term "within," not generic "in."
4. An "evolve independently" pattern (built from one example, jcnevess)
   fired the wrong direction inside a negated sentence elsewhere
   ("hasn't been a strong need ... to evolve independently" — an
   argument *for* grid-extension, matched as *against* it). Removed —
   one example isn't enough to trust a phrase that breaks under negation,
   and there was no simple negation-context check worth building for a
   single occurrence.

**Also added a margin threshold** (own/ext score must differ by ≥2, not
just >0) after a 2-vs-1 margin mislabeled a legitimately neutral,
both-sides-framing comment as advocacy. Below that margin the comment is
now labeled `ambiguous` rather than forced into a camp.

**Final spot-check pass — 12 of 14 manually-verified comments now match
my own reading exactly:**

| commenter | expected (my read) | classifier |
|---|---|---|
| SebastianZ | own-display-type | own-display-type ✓ |
| tabatkins (tl;dr) | own-display-type | own-display-type ✓ |
| rjgotten | own-display-type | own-display-type ✓ |
| rachelandrew | own-display-type | own-display-type ✓ |
| xaddict | own-display-type | own-display-type ✓ |
| jcnevess | own-display-type | own-display-type ✓ |
| suethepooh | own-display-type | own-display-type ✓ |
| cat394 (#1) | grid-extension | grid-extension ✓ |
| cat394 (#2) | grid-extension | grid-extension ✓ |
| nmn (#1) | grid-extension | grid-extension ✓ |
| nmn (#2, hedged) | grid-extension (leans) | grid-extension ✓ |
| fantasai (#3, agenda framing) | genuinely neutral/procedural | own-display-type ✗ |
| fantasai (#4, rebuts a quote) | genuinely neutral/procedural | own-display-type ✗ |
| GrimLink ("+1 to Tab's and Rachel's") | own-display-type (by reference) | no-signal (known miss) |

**Two documented residual limitations, not silently fixed:**
- **fantasai** (CSS WG co-editor, publicly known role) reads across all 5
  of her comments as largely neutral/procedural — chairing the debate,
  not advocating a side — but 2 of her comments happen to use the phrase
  "[separate/new] display type" while *describing* an option evenhandedly,
  which the classifier can't distinguish from *advocating* it. Both are
  low-margin calls (2-vs-0, the minimum to clear the threshold). **This
  specific author's camp label should not be trusted without a human
  look before it drives graph placement** — flagged here rather than
  hand-coded around, since "editor therefore neutral" is an assumption
  about her, not something derived from this comment's content.
- **First-name-only endorsements** ("+1 to Tab's and Rachel's comments")
  aren't attributed — the classifier has no name→handle mapping, so
  these fall to `no-signal` rather than a wrong guess. Conservative
  miss, not a wrong label.

**Aggregate note:** 33 of 132's 64 non-bot commenters (excluding
css-meeting-bot) have a determined camp from real content; the rest are
genuinely single-remark participants with no restated position — that's
a property of the thread, not a classifier failure, and `no-signal`
comments should render as visually distinct (unclassified) nodes in the
graph rather than being forced into a camp.
