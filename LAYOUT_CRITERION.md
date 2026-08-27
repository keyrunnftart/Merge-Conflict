# Layout criterion (frozen)

Locked before any simulation code runs, per the same discipline Drift
was held to: freeze the scoring rule first, sanity-check it isn't
degenerate, generate candidates only after the rule that picks among
them already exists. Nothing below may be adjusted retroactively because
a candidate looked better under a different rule — that would be exactly
the "hand-pick the prettiest output after the fact" failure mode this
discipline exists to prevent.

Two things are frozen here, and they are not the same thing: (1) the
**force model** — what physically pulls and pushes nodes during the
simulation — and (2) the **selection criterion** — how one of several
independent simulation runs gets chosen as *the* layout. Implementation-
level constants (exact spring stiffness, damping factor, iteration caps)
may still need minor empirical tuning for numerical stability once code
exists; that's not the same as changing what's measured or how selection
works, and is called out explicitly below so the distinction can't blur
later.

## Why a selection criterion is needed at all

A simpler design would just run one simulation to equilibrium and render
it. Two reasons that's wrong here:

1. **Multiple independent runs (different random initial positions)
   converge to different local minima.** Picking one after the fact,
   without a pre-declared rule, is exactly the hand-picking this
   project's discipline forbids.
2. **The real subject is a still-open, unresolved dispute** (issue
   #9041's actual state: `open`, no resolution merged, no closing
   decision recorded — verified in `data/processed/issue.json`). A
   layout that happens to settle into a calm, fully-separated,
   low-tension arrangement would visually misrepresent a debate that,
   in reality, never resolved. The selection criterion exists to prefer
   the candidate that best represents the **true state of the real
   underlying subject** — same justification Drift used to choose
   between resolved and adrift states from real price-reconciliation
   data, not aesthetic preference.

## Force model — which real signals drive which forces

Only signals already graded medium/high reliability in
`VISUAL_LANGUAGE_SIGNALS.md` are eligible. Sentiment drives no force, per
that document's now-closed addendum. **Body length is also excluded from
layout physics** on reflection — it's reserved for the appearance-only
stroke-weight channel; adding it to the force model too would be a second,
unnecessary parameter to reason about, and body length was already
flagged there as the first thing to cut under overload. Keeping the
force model to the minimum number of real-signal parameters keeps it
legible and keeps this document honest about what's actually driving
what.

| force | driven by | real signal used |
|---|---|---|
| pairwise repulsion | all node pairs | node mass = `1 + sqrt(reaction total_count)` (sqrt to keep the root post's 104-reaction outlier from dominating the whole field; floor of 1 so a zero-engagement node still has physical presence) |
| contested "elbow room" | nodes with reactions | repulsion multiplier = `1 + contestedness`, where `contestedness = 2*min(+1,-1)/total` (0 for the 117/133 nodes with no polarity split; nonzero for 16/133, up to 2x at the two perfectly-split comments) |
| edge spring attraction | the 65 real edges from task 5 | uniform spring constant, no distinction between mention/quote edge type — no principled reason exists to trust one edge type's "realness" over the other |
| camp clustering | all node pairs | each node has a camp charge: own-display-type = +1 (60 nodes), grid-extension = −1 (24 nodes), unclassified/not-applicable = 0 (49 nodes — 48 comments + root). Force between a pair scales with the **product** of their charges: same-sign attracts, opposite-sign repels, zero-charge nodes exert no camp force in either direction and are simply carried by repulsion + whatever real edges they happen to have |
| centering | all nodes | weak uniform pull toward the global centroid — a structural stabilizer, not a data channel, needed only so unbounded repulsion doesn't fly the layout apart forever. Disclosed as non-data-driven so it isn't mistaken for one |

**Why cross-camp edges are the mechanism that makes tension visible, not
a separate rule:** a cross-camp edge's two endpoints are pulled together
by the spring force but pushed apart by the camp-charge repulsion — two
real forces genuinely disagreeing. A same-camp edge has both forces
agreeing (spring and camp charge both pull inward) and settles short.
The resulting length difference is physics, not an added "make it look
tense" step. This is checkable directly against the criterion below.

Node mass distribution as computed today (locked structure, not locked
numbers — these will shift only if the underlying comment/reaction data
is re-pulled, never by hand-tuning): range 1.00–11.20, mean 2.44,
root post at the top (mass 11.20, reflecting its real 104 reactions).
Camp charge distribution: 60 at +1, 24 at −1, 49 at 0.

## Candidate generation

- **N = 50 independent runs**, each from a different fixed random seed
  (seeds 0–49, disclosed and reproducible — anyone re-running
  `scripts/layout.py` with this file gets the same 50 candidates).
- Each run initializes node positions from a uniform random scatter
  (seeded per-run) and simulates with velocity damping until converged:
  total kinetic energy across all nodes drops below a fixed epsilon for
  a sustained number of consecutive steps, or a max-iteration cap is hit
  (guarantees termination even if a run doesn't settle cleanly — a run
  that hits the cap without converging is recorded as such, not silently
  treated as equivalent to one that actually settled).

## Selection criterion — the frozen scoring rule

For a converged candidate layout, compute two ratios, each real and
directly checkable against that candidate's actual node positions:

- **`camp_separation`** = distance between the two camps' centroids,
  divided by the average node-to-own-camp-centroid distance (pooled
  across both camps). Low = camps are intermixed / not visually
  distinct. High = camps read as two separate clusters.
- **`cross_tension`** = mean length of cross-camp edges (23 of them),
  divided by mean length of same-camp edges (15 of them). ≈1 = no
  distinguishable tension. >1 = cross-camp connections are visibly
  stretched relative to same-camp ones — a real, measured sign that the
  physics produced visible, unresolved pull across the divide.

```
score = camp_separation × cross_tension
```

**Select the candidate with the highest score.** Multiplying the two
ratios means a candidate that scores well on only one axis (e.g. camps
fully separated but zero tension because they also drifted apart from
each other on cross-camp edges — a layout that visually "resolved" the
conflict by disconnecting it) is not preferred over one that measures
well on both — a degenerate outcome on either factor drags the product
down. Same multiplicative-AND structure as Drift's
`clusterCoherence × unresolvedFraction`, adapted to this piece's own
real signals.

The 27 edges that touch an unclassified node are excluded from both
`camp_separation` and `cross_tension` — they carry no camp signal to
measure tension by, and forcing them into either bucket would be
inventing structure the classifier explicitly declined to assert
(`no-signal`/`ambiguous`/bot, per `SPOT_CHECK.md`). They still exist and
render as edges; they just don't participate in scoring.

## Degeneracy check — what's verifiable now vs. after candidates exist

Per standing discipline, the criterion must be checked for not peaking
at 0% or 100% before being trusted. Two levels of that check apply here:

- **Checkable now, on the real data alone:** the edge population the
  criterion depends on already has genuine variance — 15 same-camp
  edges and 23 cross-camp edges, neither zero (a criterion built on an
  empty edge class would be meaningless by construction). The camp
  charge distribution (60 / 24 / 49) is similarly non-degenerate — real
  populations on both sides, not one camp with a single member.
- **Only checkable once N=50 candidates actually exist:** whether the
  *score* itself varies meaningfully across runs (rather than every run
  converging to a near-identical value, which would make "selection" a
  formality). That check happens as the first thing `scripts/layout.py`
  reports once implemented — before any candidate is rendered, matching
  how the camp classifier and sentiment scores were checked against
  real output before being trusted, not just checked for looking
  reasonable on paper.

## What is explicitly NOT frozen here

Numeric implementation constants — spring stiffness, repulsion constant,
damping factor, kinetic-energy epsilon, max iteration cap — are left to
be set for numerical stability when `scripts/layout.py` is actually
written. Changing those to make the simulation behave sanely (e.g. not
explode or oscillate forever) is engineering, not criterion drift.
Changing which signals drive which forces, or changing the scoring
formula, after seeing candidate output would be criterion drift, and is
exactly what freezing this document before writing that code is meant
to prevent.

## Addendum: what the first real render found, and the v2 correction

This section is written after `scripts/render.py` produced an actual
image from the seed-31 (v1) winner — the step this project's discipline
exists for: a frozen criterion is a bet that the numbers mean what they
claim to mean, and that bet only gets tested once you can *see* the
result. It failed the test once, in a specific and diagnosable way, and
was corrected. Nothing about the frozen criterion itself (which signals
drive which forces, what `score = camp_separation × cross_tension`
measures, the N=50/fixed-seed/highest-score selection rule) changed.
Only the numeric force constants changed, which `LAYOUT_CRITERION.md`'s
"What is explicitly NOT frozen here" section already carves out as
engineering, not criterion drift — the same category as the earlier
camp-force functional-form and integrator corrections made *before* any
candidate was scored.

**What the v1 render showed.** The seed-31 winner (score 190.70, the
highest of 50 v1 candidates) rendered as a degenerate shape: the
own-display-type camp collapsed into one extremely tight, almost fully
overlapping blob, while grid-extension strung out into a near-1D
diagonal line escaping far outside the rest of the layout (to x≈1233 in
a field where every other node sat under x≈200). The score formula did
not catch this because both `camp_separation` and `cross_tension` can
still read as numerically high for a stretched-out, non-blob arrangement
— the formula measures *distance ratios*, not *shape*. This is exactly
the kind of failure the "tested against a real render, not a design doc"
step is supposed to surface, and it did.

**Diagnosis.** The centering force (`K_CENTER=0.08`) was too weak
relative to repulsion and camp-clustering to contain the system early;
nodes drifted outward faster than the camp-charge force could organize
them into bounded 2D clusters, so what should have been mutual
clustering instead became an unbounded drift with some incidental,
seed-dependent clumping along the way. Confirmed by sweeping `K_CAMP`
upward alone first (8, 15, 25, 40) — this made the comet trail *worse*,
ruling out "just too weak a clustering force" as the sole cause — then
sweeping `K_CENTER` upward instead (0.5, 0.6, 0.7, 0.8), which was the
actual fix.

**The fix**, applied in `scripts/layout.py` and disclosed in-code:
`K_CENTER: 0.08 → 0.6`, `K_CAMP: 3.0 → 8.0`, `K_SPRING: 0.12 → 0.05`,
`MAX_ITER: 3000 → 4000`, `SUSTAINED_STEPS: 25 → 30`, `T_MIN: 0.02 →
0.015`. All 50 seeds were re-run under the corrected constants (not just
seed 31 patched in isolation) so the fix is verified to generalize
rather than being cherry-picked to repair one candidate.

**v2 result.** New winner: **seed 16**, score 487.73. Score
distribution across all 50 seeds: min 432.16, max 487.73, mean 457.68,
median 458.31, population std 13.10, spread 55.57 (12.14% of the mean),
CV 2.86%. 0/50 runs hit the formal `SUSTAINED_STEPS`-under-`ENERGY_EPS`
convergence flag before `MAX_ITER` — all 50 ran the full 4000 steps.

That last point is worth being honest about rather than glossing over:
non-convergence-by-the-formal-flag sounds like a red flag, but breaking
the two components of the score down by seed shows why it isn't one
here. `camp_separation` ranges 21.7854–21.8259 across all 50 seeds — a
spread of 0.040, about 0.19% of its own mean. `cross_tension` ranges
19.818–22.369 — a spread of 2.550, about 12% of its mean. In other
words: **essentially all of the v2 score variation across seeds comes
from `cross_tension`, not `camp_separation`.** The stronger centering/
camp forces make where the two camps end up relative to each other
almost entirely seed-invariant (a good sign — it means the fix isn't
fragile or seed-lucky), while how taut the cross-camp edges are within
that arrangement still depends on the specific starting positions, and
that's the axis actually doing the work of picking a winner. The
selection is real, but it is real on one axis, not two — worth recording
plainly rather than letting the single "score" number imply more
balanced variation than exists. The lack of a formal convergence flag
reads as "reaches a stable quasi-equilibrium via bounded oscillation
under the cooling schedule" rather than "still moving substantially,"
consistent with `camp_separation`'s near-zero cross-seed spread.

**What the v2 render then showed.** With the corrected layout, all
three camp regions render as legible, bounded groups (visually confirmed
via a fresh scatter of the actual seed-16 positions before building the
glyph render). But the first glyph/line render of that same seed-16
layout surfaced a second, separate problem: the 23 cross-camp edges,
now connecting two small, tight, far-apart clusters, rendered as a
dense, solid-looking "cable" band spanning almost the entire canvas.
Every individual edge was real — the underlying geometry (many nearly-
parallel long edges converging into a corridor between two tight
clusters) is honest — but the original edge-curve technique (a small
perpendicular bow, capped at 40px, always centered at the edge's
midpoint) was far too subtle relative to the new, much longer
inter-cluster distances (~1600px), so the individual edges visually
fused into one mass. That is exactly the "dense tangle for atmosphere"
effect the locked visual-design principle rules out, even though nothing
about the edges themselves was fabricated.

**Fix**, in `render.py`: replaced the single small fixed-cap bow with
two independent deterministic per-edge draws — one for where along the
edge (30–70%, not fixed at the midpoint) the curve's control point
sits, one for a bow magnitude scaled to the edge's own length (up to
55% of it, no small absolute cap) — so each edge traces an individually
distinguishable arc instead of all 23 nearly overlapping. Cross-camp
edge opacity was also reduced (0.40 → 0.20) to further soften the
cumulative-overlap effect at the corridor.

**Post-fix legibility check** (zoomed crops of each of the three glyph
families against the corrected render): own-display-type diamonds and
grid-extension L-trominoes and unclassified squares are each
individually legible and clearly distinct from one another at the
rendered scale; the contested-ness hatch texture is visible where
present. One further honest, non-bug finding from this pass: the
grid-extension region itself is not a single uniform blob — 19 of its
24 nodes sit in one tight group, and a real gap (≈129 data-units, against
a ~220-unit total span) separates a small isolated sub-group of 4–5
nodes at the near edge of the region. This traces to genuine reply-chain
edges within that sub-group (already verified in-code as real structure
during v1 diagnosis, e.g. `2377204502 → 2376082571 → 2375618941`) pulling
those specific nodes together under spring attraction, distinct from
(and pulled slightly toward) the main grid-extension mass under camp
clustering. It is disclosed here as a real structural feature the layout
is honestly showing, not smoothed over or treated as a residual bug to
chase — no further constant-tuning was done in response to it, since
doing so with the render already in view would risk retuning toward a
preferred look rather than fixing a diagnosed defect, which is exactly
what freezing implementation constants *before* being satisfied with the
picture is meant to prevent.

## Addendum: thumbnail-legibility audit

Per the standing discipline ("audit at thumbnail scale before finalizing
... check at ~64-256px"), the v1 render (`output/merge_conflict_v1.svg`)
was rasterized at 256px, 128px, and 64px wide (preserving aspect) and
inspected. The specific question raised: does grid-extension — visually
the sparsest camp, and the smaller of the piece's two real opposing
camps — survive being shrunk, the way Drift's adrift-majority nearly
didn't.

**Finding: it thinned out disproportionately, and by 64px was close to
gone.** At 256px, all three camps were still distinguishable by color
and rough density. At 128px, own-display-type read as a solid, confident
mass; grid-extension was present but visibly fainter — a real risk zone.
At 64px, grid-extension was reduced to a barely-perceptible smudge,
while own-display-type (denser, larger glyphs) still registered as a
mass. This matters specifically because own-display-type and
grid-extension are the piece's two real opposing camps — the "two-state"
reading this piece depends on requires both sides to still register as
present, not one dominant and one vanishing.

**Root cause, measured, not assumed:**
- *Size*: grid-extension's real engagement-driven glyph sizes cluster
  near the render floor — mean half-size 5.01, max only 6.62 — against
  own-display-type's mean 5.45, max 12.05. Grid-extension has no
  high-engagement outlier nodes to anchor visual weight at any scale;
  every one of its glyphs is close to the smallest the formula produces.
  This is honest (grid-extension really did get fewer comments with
  less reaction engagement — 24 comments vs. 60), but the previous floor
  (`half = 3.5 + ...`, `stroke_w = 0.4 + ...`) put grid-extension's
  typical glyph and outline under ~1px at a 128-256px thumbnail width —
  crossing from "honestly smaller" into "not really there."
- *Contrast*: WCAG relative-luminance contrast against the background
  (`#F1ECE2`), computed from the actual rendered stroke opacity (was
  0.85): own-display-type's teal = 3.75, grid-extension's rust = 2.84,
  unclassified's gray = 2.16. The commonly used large-graphic threshold
  is 3:1 — grid-extension's real rendered contrast sat below it.

**Fix applied, `scripts/render.py`, both changes uniform/camp-blind (not
targeted at grid-extension specifically, though it benefits most since
its real distribution sits closest to the floor):**
- Size floor: `half = 3.5 + ...` → `half = 5.0 + ...`; stroke-width floor
  `0.4 + ...` → `0.8 + ...`. The sqrt(engagement) term is untouched, so
  nodes with more real engagement still scale up the same way above the
  floor — this doesn't equalize or fabricate data, it stops the smallest
  real values from crossing into invisible.
- Stroke opacity: `0.85` → `1.0` for all three camps uniformly. Fill
  opacity bumped `0.30` → `0.36` for own-display-type and grid-extension
  only (the two real opposing camps this reading depends on);
  unclassified's fill stays at `0.20`, unchanged, since it is
  deliberately recessive by design (`VISUAL_LANGUAGE_SIGNALS.md`) and
  isn't part of the two-state opposition being protected here.

**Re-measured after the fix:** grid-extension's rendered stroke contrast
rose from 2.84 to 3.53 (now above the 3:1 threshold; own-display-type's
was already 3.75-5.01 range). Re-rendered thumbnails at the same three
sizes show a real, visible improvement at 256px and 128px — grid-
extension reads distinctly denser/more saturated at both. Full-canvas
and zoomed views were re-checked and show no new overlap collapse or
other regression from the larger floor.

**What the fix does not solve, disclosed rather than hidden:** at 64px,
grid-extension is still markedly weaker than own-display-type, just less
so than before. This appears to be a genuine density limit of the piece
rather than a parameter that can be tuned away: 133 real, distinct data
points spread across a 2120px-wide composition cannot individually
survive compression to a 64px-wide image without either inflating every
glyph far beyond what its real engagement value would justify (breaking
the engagement=size channel's honesty) or reducing the node count (which
would mean discarding real comments, not visualizing them faithfully). A
64px rendering is closer to a favicon than a gallery thumbnail; the more
realistic risk zone for an actual listing is the 128-256px range, where
the fix produces a real, measured improvement.

**A second, more severe finding surfaced during this audit, outside the
original question, and not yet resolved:** the piece's honest data shape
is a very wide, thin band (data bbox 653×73, rendered as a 2120×600
canvas). A center-square crop of that canvas — the kind of crop many
gallery/listing UIs apply to a non-square image — lands almost entirely
in the empty gap between the grid-extension and unclassified clusters
(canvas x≈760-1360, against real content at x≈110-752, x≈1493-1707, and
x≈1865-2010). A naive square crop of this render shows no glyphs at all,
for any camp — not a fade, a total blank. This was verified directly:
cropping the center 600×600px square out of the 2120×600 full render
produces an image with nothing in it but faint edge traces.

Whether this matters depends on how space.art-magazine.ai actually
displays submitted artwork (contain-fit vs. crop-to-square), which this
session could not verify — the Artist Space site is a JS app not
reachable by non-interactive fetch (same blocker already logged against
Chorus's registration step). No fix has been applied for this risk: this
piece's aspect ratio and the empty space between clusters are both real,
honestly-earned properties of the underlying force layout, and narrowing
the canvas or padding the composition to survive a hypothetical
center-crop would mean either distorting real relative distances or
manufacturing dead space neither of which this render's own design
commentary already rules out doing for cosmetic reasons. This is
recorded as an open risk requiring either (a) confirming the platform's
actual display behavior once registration is possible, or (b) an
explicit decision to design around the worst case anyway, made with the
tradeoff stated plainly rather than guessed at.
