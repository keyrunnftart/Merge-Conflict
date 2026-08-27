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
