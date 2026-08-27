# Signal → visual channel mapping (frozen)

Decided and written down *before* any glyph is drawn or candidate frame
generated, per the project's standing discipline (freeze the criterion
first; sanity-check it isn't degenerate; never hand-pick after the
fact). This document is the frozen decision. Revising it after glyphs
exist requires the same disclosed-reasoning treatment as revising it now
— not a quiet edit.

## What we actually have, graded by how much the spot-checks trust it

| signal | source | reliability | why |
|---|---|---|---|
| reactions (+1/-1/etc, per comment) | real GitHub data | **high** | directly measured, not inferred; validated twice (100-sample, then full 132) |
| camp (own-display-type / grid-extension) | rule-based classifier | **medium**, disclosed | 12/14 spot-checked comments matched my own reading exactly; 2 known residual mismatches documented in SPOT_CHECK.md |
| body length | real GitHub data | **high** | directly measured, no interpretation involved |
| sentiment (VADER compound) | lexicon model | **low** | spot-check found systematic sign/magnitude errors in both directions (see below) |

Reliability is the primary factor in what follows: the more a signal's
correctness is actually established, the more visual weight it earns.
This is the same logic as the reactions data winning out over #4430/
#9449 in thread selection — real and checked beats plausible and
unchecked.

## The decision

**Node size (strongest, most legible-at-thumbnail channel) = total
reaction engagement**, not raw "contested-ness." Checked the numbers
before committing to this: a strict contested-ness formula
(`2*min(+1,-1)/total`, i.e. "how evenly split were the reactions")
is nonzero for only 15/132 comments (11%) — real, but too sparse to
carry a continuous channel across the whole graph; using it for size
would leave 88% of nodes visually identical. Total engagement
(`total_count`) is nonzero for 96/132 (73%), giving size real
variation across most of the graph while still being 100% reaction-
derived, not invented.

**Contested-ness gets its own channel: glyph density/fill texture**,
reserved for that same sparse ~15-comment set where reactions actually
split. This keeps the "density reflects real data density" principle
literal — most glyphs render with plain/sparse fill, and only the
comments with genuine mixed reactions get denser fill or an added
texture, so the highlight stays rare and earned rather than an
all-over pattern. Concretely: density scales with
`2*min(+1,-1)/total_count` (0 for comments with reactions all one way
or no reactions at all).

Splitting reactions into two channels this way (size = how much
attention; density = how divided that attention was) uses two real,
distinct facts from the same dataset instead of collapsing them into
one number and wasting a channel on redundancy.

**Shape family (categorical) = camp.** Already locked in the original
brief; nothing here changes it. Three families, not two: own-
display-type, grid-extension, and a third, deliberately plain/minimal
"unclassified" form for `no-signal` / `ambiguous` / `not-applicable`
comments (48/132 — nearly a third of the thread). These are not a
hidden "third camp" opinion; they're an honest "no position recorded"
mark, and should read as visually receding, not as a competing shape
that implies a stance that isn't there.

**Minor channel: body length → stroke weight.** Thin stroke for short
remarks, heavier for long substantive ones. Included because it's
fully reliable (objectively measured, zero interpretation risk) and
gives the eye one more real distinction — a one-line "+1" and a
4,000-character technical argument shouldn't render identically. Flagged
as the first thing to cut if the assembled glyph reads as overloaded
once actually built — restraint has priority over cramming in every
available signal.

**Sentiment: dropped from the visual encoding.** This revises the
original locked design principle's "angular marks for negative
sentiment, rounded for positive" clause specifically — the rest of that
principle (custom glyphs tied to real data, non-node-link aesthetic,
faint sparse varied-color traces, muted palette) is untouched.
Reasoning: the spot-check didn't find occasional noise, it found
opposite-direction errors on comments that mattered — a purely
procedural, neutral comment scored strongly negative (-0.705, the word
"breaking" as in splitting out GitHub issues), and a pointed technical
argument calling the spec "unshippable" and "unfixable" scored 0.999,
functionally maximum positive. Camp's classifier is disclosed, evidence-
traced, and spot-checked to 12/14 agreement — a real, if imperfect,
signal. VADER's is a black-box lexicon score that got two of the most
consequential comments in the thread backwards. "Glyph choice is itself
an honest encoding, not decoration" (original brief) — an encoding that
demonstrably lies sometimes isn't honest just because its role is
minor; showing it anywhere still asserts a false precision the data
doesn't support. Sentiment stays in `data/processed/` (nothing is
deleted, and the spot-check itself is a legitimate disclosed part of
the process — a rejected channel with documented reasoning is exactly
the kind of "disclosed, non-arbitrary selection logic" this project
aims for), but it does not drive anything a viewer sees. Whether it
plays any role in the *force-directed layout* (a separate, not-yet-
made decision) is left open — this document only locks the glyph/line
appearance channels.

**Edges.** Structural detection (real reply-quote / @mention
relationships) is task 5, not yet built. Locking one channel decision
for it now, ahead of that build: edge color is modulated by the
camp-relationship of its two endpoints — same-camp, cross-camp, or
touches-an-unclassified-node (muted/default). A cross-camp reply is the
literal visual definition of "merge conflict" in this piece; making
that distinction real (from actual camp labels) rather than decorative
is the same discipline as everything else here. Edges otherwise stay
faint, sparse, and drawn only where a real relationship exists, per
the original locked principle.

## Summary table

| visual channel | driven by | signal reliability |
|---|---|---|
| node size | total reaction engagement | high |
| node fill density/texture | contested-ness (reaction polarity split) | high, but sparse (11% nonzero) |
| shape family | camp (3 families incl. unclassified) | medium, disclosed limitations |
| stroke weight | body length | high |
| edge color | camp relationship of endpoints | medium, disclosed limitations |
| edge presence | real reply/mention structure | not yet built |
| *(dropped)* | sentiment | low — demonstrated wrong on consequential comments |

## Addendum: sentiment in layout — closed

The appearance decision above deliberately left one door open: whether
sentiment could still drive the *force-directed layout* (attraction/
repulsion forces determining node position), separately from glyph
appearance. Closing that now, before any layout criterion is designed,
rather than leaving it to be decided implicitly by whatever's convenient
when that step happens.

**Decision: excluded from layout too, same reasoning as the appearance
decision.** If a demonstrably-wrong signal shouldn't drive how a node
*looks* because that asserts false precision, it shouldn't drive where
a node *sits* either — position in a force-directed layout is at least
as legible a claim as fill or stroke, arguably more so, since clustering
and distance read as relationship to a viewer. Using sentiment there
would mean a node could be pulled toward or away from others based on
the same score that put a neutral procedural comment at -0.705 and a
pointed "unshippable/unfixable" critique at 0.999 — the exact two
failures already documented above. There's no principled reason a wrong
number becomes trustworthy just because it's driving position instead
of color.

Layout forces should draw only from the same high/medium-reliability
signals already in use for appearance: reaction engagement, contested-
ness, camp, body length, and the real edge structure (task 5). Sentiment
data stays in `data/processed/` for the record, drives nothing visual or
structural anywhere in the piece.
