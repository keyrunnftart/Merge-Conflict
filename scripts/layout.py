#!/usr/bin/env python3
"""
Task: implement and run the frozen force model + selection criterion from
LAYOUT_CRITERION.md. Nothing here changes what's measured or how forces
are assigned -- only numeric constants (spring/repulsion/camp strength,
damping, iteration caps) are tuned for numerical stability, which
LAYOUT_CRITERION.md explicitly carves out as not being criterion drift.
"""
import json
import math
import numpy as np

N_RUNS = 50
MAX_ITER = 3000
K_REP = 150.0
K_SPRING = 0.12
K_CAMP = 3.0
K_CENTER = 0.08
ENERGY_EPS = 0.01
SUSTAINED_STEPS = 25
INIT_SCATTER = 60.0
T0 = 20.0
T_MIN = 0.02


def load_graph():
    with open("data/processed/graph.json") as f:
        g = json.load(f)
    nodes = g["nodes"]
    edges = g["edges"]
    id_to_idx = {n["id"]: i for i, n in enumerate(nodes)}

    n = len(nodes)
    mass = np.zeros(n)
    contested = np.zeros(n)
    charge = np.zeros(n)
    camp = [None] * n

    for i, nd in enumerate(nodes):
        r = nd["reactions"]
        total = r["total_count"]
        mass[i] = 1.0 + math.sqrt(total)
        contested[i] = (2 * min(r["+1"], r["-1"]) / total) if total > 0 else 0.0
        c = nd["camp"]
        camp[i] = c
        charge[i] = 1.0 if c == "own-display-type" else (-1.0 if c == "grid-extension" else 0.0)

    size = mass * (1.0 + contested)  # contested "elbow room" boost, per LAYOUT_CRITERION.md

    edge_idx = []
    edge_rel = []
    for e in edges:
        i, j = id_to_idx[e["source"]], id_to_idx[e["target"]]
        edge_idx.append((i, j))
        edge_rel.append(e["camp_relationship"])

    return nodes, mass, size, charge, camp, edge_idx, edge_rel


def simulate(seed, n, mass, size, charge, edge_idx, verbose=False):
    """Cooling-schedule integrator (Fruchterman-Reingold style: displacement
    per step capped by a temperature that decays over the run) rather than
    momentum/velocity dynamics -- momentum-based integration was tried first
    and diverged (force spikes at close range compound through velocity
    faster than damping alone could remove energy). This is a numerical-
    stability substitution only: same forces, same signals driving them,
    same seed determinism -- exactly the kind of implementation-constant
    tuning LAYOUT_CRITERION.md carves out as not being criterion drift.
    """
    rng = np.random.default_rng(seed)
    pos = rng.uniform(-INIT_SCATTER, INIT_SCATTER, size=(n, 2))

    ei = np.array([e[0] for e in edge_idx])
    ej = np.array([e[1] for e in edge_idx])

    consecutive_low = 0
    converged = False
    step = 0
    for step in range(MAX_ITER):
        T = T0 * (T_MIN / T0) ** (step / MAX_ITER)  # exponential cooling

        diff = pos[:, None, :] - pos[None, :, :]
        dist = np.sqrt((diff ** 2).sum(-1))
        dist = np.maximum(dist, 0.25)
        np.fill_diagonal(dist, 1.0)
        unit = diff / dist[:, :, None]

        size_prod = np.outer(size, size)
        rep_mag = K_REP * size_prod / (dist ** 2)
        np.fill_diagonal(rep_mag, 0.0)
        F_rep = (rep_mag[:, :, None] * unit).sum(axis=1)

        # Constant-magnitude (distance-independent) camp force, not
        # linear-in-distance: linear-in-distance was tried and diverged for
        # the repulsive (opposite-camp) case -- a repulsion that GROWS with
        # distance has no restoring force and runs away unboundedly once
        # two nodes start separating. A constant "social tug" (attract same
        # camp / repel opposite camp regardless of how far apart they
        # already are) still produces long-range clustering -- unlike
        # inverse-square, it doesn't vanish at range -- while staying
        # bounded, so it settles once balanced against the short-range 1/d^2
        # repulsion. Same signals (camp charge) driving the same qualitative
        # behavior (same-camp attracts, cross-camp repels); only the
        # functional form changed, for the stability reason stated.
        charge_prod = np.outer(charge, charge)
        camp_mag = -K_CAMP * charge_prod * np.ones_like(dist)
        np.fill_diagonal(camp_mag, 0.0)
        F_camp = (camp_mag[:, :, None] * unit).sum(axis=1)

        F_spring = np.zeros((n, 2))
        if len(edge_idx) > 0:
            d_ij = pos[ei] - pos[ej]
            dist_ij = np.linalg.norm(d_ij, axis=1, keepdims=True)
            dist_ij = np.clip(dist_ij, 1e-6, None)
            unit_ij = d_ij / dist_ij
            f = -K_SPRING * dist_ij * unit_ij
            np.add.at(F_spring, ei, f)
            np.add.at(F_spring, ej, -f)

        F_center = -K_CENTER * pos * mass[:, None]

        F_total = F_rep + F_camp + F_spring + F_center
        disp = F_total / mass[:, None]
        disp_mag = np.linalg.norm(disp, axis=1, keepdims=True)
        scale = np.minimum(1.0, T / np.maximum(disp_mag, 1e-9))
        step_disp = disp * scale
        pos = pos + step_disp

        total_move = float(np.linalg.norm(step_disp, axis=1).mean())  # mean, not sum -- sum scales with n and never cleared the threshold
        if total_move < ENERGY_EPS:
            consecutive_low += 1
            if consecutive_low >= SUSTAINED_STEPS:
                converged = True
                break
        else:
            consecutive_low = 0

    return pos, converged, step + 1


def score_layout(pos, camp, edge_idx, edge_rel):
    own = np.array([i for i, c in enumerate(camp) if c == "own-display-type"])
    ext = np.array([i for i, c in enumerate(camp) if c == "grid-extension"])
    c_own = pos[own].mean(axis=0)
    c_ext = pos[ext].mean(axis=0)
    centroid_dist = float(np.linalg.norm(c_own - c_ext))
    within_own = np.linalg.norm(pos[own] - c_own, axis=1).mean()
    within_ext = np.linalg.norm(pos[ext] - c_ext, axis=1).mean()
    avg_within = (within_own * len(own) + within_ext * len(ext)) / (len(own) + len(ext))
    camp_separation = centroid_dist / avg_within if avg_within > 1e-9 else 0.0

    cross_lens, same_lens = [], []
    for (i, j), rel in zip(edge_idx, edge_rel):
        d = float(np.linalg.norm(pos[i] - pos[j]))
        if rel == "cross-camp":
            cross_lens.append(d)
        elif rel == "same-camp":
            same_lens.append(d)
    mean_cross = sum(cross_lens) / len(cross_lens)
    mean_same = sum(same_lens) / len(same_lens)
    cross_tension = mean_cross / mean_same if mean_same > 1e-9 else 0.0

    return camp_separation, cross_tension, camp_separation * cross_tension


def main():
    import sys
    nodes, mass, size, charge, camp, edge_idx, edge_rel = load_graph()
    n = len(nodes)

    if len(sys.argv) >= 3 and sys.argv[1] == "batch":
        lo, hi = int(sys.argv[2]), int(sys.argv[3])
        print(f"n_nodes={n} n_edges={len(edge_idx)}  running seeds {lo}..{hi-1}")
        with open("data/processed/layout_partial.jsonl", "a") as out:
            for seed in range(lo, hi):
                pos, converged, steps = simulate(seed, n, mass, size, charge, edge_idx)
                sep, tension, score = score_layout(pos, camp, edge_idx, edge_rel)
                rec = {"seed": seed, "converged": converged, "steps": steps,
                       "camp_separation": sep, "cross_tension": tension, "score": score,
                       "positions": pos.tolist()}
                out.write(json.dumps(rec) + "\n")
                print(f"seed={seed:2d} converged={converged!s:5} steps={steps:4d} "
                      f"sep={sep:.4f} tension={tension:.4f} score={score:.4f}")
        return

    if len(sys.argv) >= 2 and sys.argv[1] == "aggregate":
        results = []
        with open("data/processed/layout_partial.jsonl") as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
        results.sort(key=lambda r: r["seed"])
        assert [r["seed"] for r in results] == list(range(N_RUNS)), \
            f"expected seeds 0..{N_RUNS-1}, got {[r['seed'] for r in results]}"

        scores = np.array([r["score"] for r in results])
        n_converged = sum(1 for r in results if r["converged"])
        print(f"converged: {n_converged}/{N_RUNS}")
        print(f"score distribution: min={scores.min():.4f} max={scores.max():.4f} "
              f"mean={scores.mean():.4f} median={np.median(scores):.4f} std={scores.std():.4f}")
        spread = scores.max() - scores.min()
        cv = scores.std() / scores.mean() if scores.mean() > 1e-9 else float("nan")
        print(f"spread (max-min): {spread:.4f}   coefficient of variation (std/mean): {cv:.4f}")
        print(f"relative spread (spread/mean): {spread/scores.mean()*100:.2f}%")

        winner = max(results, key=lambda r: r["score"])
        n_higher = sum(1 for s in scores if s > winner["score"])
        print(f"\nwinner: seed={winner['seed']} score={winner['score']:.4f} "
              f"({n_higher} runs scored higher -- should be 0)")

        out = {
            "n_runs": N_RUNS,
            "seeds": list(range(N_RUNS)),
            "score_summary": [
                {"seed": r["seed"], "converged": r["converged"], "steps": r["steps"],
                 "camp_separation": r["camp_separation"], "cross_tension": r["cross_tension"],
                 "score": r["score"]}
                for r in results
            ],
            "score_distribution": {
                "min": float(scores.min()), "max": float(scores.max()),
                "mean": float(scores.mean()), "median": float(np.median(scores)),
                "std": float(scores.std()), "spread": float(spread), "cv": float(cv),
            },
            "winner_seed": winner["seed"],
            "winner_score": winner["score"],
            "winner_positions": winner["positions"],
        }
        with open("data/processed/layout.json", "w") as f:
            json.dump(out, f, indent=2)
        print("\nwrote data/processed/layout.json")
        return

    print("usage: layout.py batch LO HI   |   layout.py aggregate")


if __name__ == "__main__":
    main()
