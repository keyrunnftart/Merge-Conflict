#!/usr/bin/env python3
"""
Merge Conflict -- glyph/line visual language, built strictly from the
frozen signal->channel mapping in VISUAL_LANGUAGE_SIGNALS.md and the
frozen+run layout in LAYOUT_CRITERION.md / layout.json (seed 16 winner,
v2 constants -- see LAYOUT_CRITERION.md's addendum for why v1/seed 31
was superseded).

Every visual property below traces to a real, already-computed field in
graph.json / layout.json. Nothing here introduces a new data signal --
this step is purely "how do the already-locked channels get drawn."

Channel recap (see VISUAL_LANGUAGE_SIGNALS.md for the full reasoning):
  - shape family   = camp (own-display-type / grid-extension / unclassified)
  - size           = total reaction engagement
  - fill density   = contested-ness (sparse: real for ~16/133 nodes)
  - stroke weight  = body length
  - edge color     = camp relationship of endpoints
  - sentiment drives nothing here -- dropped per the frozen decision.
"""
import json
import math

with open("graph.json") as f:
    graph = json.load(f)
with open("layout.json") as f:
    layout = json.load(f)

nodes = graph["nodes"]
edges = graph["edges"]
raw_positions = layout["winner_positions"]
assert len(raw_positions) == len(nodes)

# ---------- palette: muted, restrained, no bright/saturated hues ----------
BG = "#F1ECE2"
INK = "#2B2620"
COLOR_OWN = "#3F6B72"        # muted teal-slate -- own-display-type
COLOR_EXT = "#A8703C"        # muted ochre/rust -- grid-extension
COLOR_UNCLASSIFIED = "#9C948A"  # neutral warm gray, deliberately recessive
COLOR_CROSS_EDGE = "#8B3A3A"    # muted maroon -- cross-camp tension
COLOR_SAME_EDGE_OWN = COLOR_OWN
COLOR_SAME_EDGE_EXT = COLOR_EXT
COLOR_NEUTRAL_EDGE = "#B9AFA0"

REAL_CAMPS = {"own-display-type", "grid-extension"}


def camp_family(camp):
    if camp == "own-display-type":
        return "own"
    if camp == "grid-extension":
        return "ext"
    return "unclassified"


def contestedness(r):
    total = r["total_count"]
    if total == 0:
        return 0.0
    return 2 * min(r["+1"], r["-1"]) / total


# ---------- per-node derived render attributes (all from real fields) ----------
class Node:
    pass


render_nodes = []
for nd, p in zip(nodes, raw_positions):
    n = Node()
    n.id = nd["id"]
    n.x, n.y = p
    n.family = camp_family(nd["camp"])
    total = nd["reactions"]["total_count"]
    # Floor raised 3.5->5.0 and 0.4->0.8 after the thumbnail-legibility audit
    # (see LAYOUT_CRITERION.md / progress log): at the smallest engagement
    # values -- which is most of grid-extension's real distribution (mean
    # half 5.01, max only 6.62, vs own's mean 5.45/max 12.05) -- the old
    # floor put glyphs and their outlines under ~1px at a 128-256px thumbnail
    # width, which is where this piece is most likely to actually be seen in
    # a listing. This is a uniform, camp-blind constant change (applied to
    # every node's floor, not targeted at grid-extension specifically) --
    # the sqrt(engagement) term is untouched, so real engagement differences
    # still scale the same way above the floor. It does not fabricate or
    # equalize data: grid-extension is still smaller and sparser on average
    # than own-display-type, honestly reflecting its real (fewer, lower-
    # engagement) comment population -- the floor only stops "smaller" from
    # crossing into "not there."
    n.half = 5.0 + 13.0 * math.sqrt(total / 104.0)   # 104 = root's real max engagement
    n.contested = contestedness(nd["reactions"])
    body_len = nd["body_length"]
    n.stroke_w = 0.8 + 2.2 * math.sqrt(min(body_len, 13191) / 13191.0)
    render_nodes.append(n)

id_to_node = {n.id: n for n in render_nodes}

# ---------- coordinate transform: data bbox -> canvas ----------
# Canvas aspect ratio follows the data's real bounding-box aspect ratio
# (clamped to a sane range) rather than forcing a square/standard frame --
# seed 16 (this run's frozen-rule winner) happens to arrange the three
# regions in a wide, fairly flat band. Forcing that into a square canvas
# would leave large dead margins above/below; distorting x/y differently
# to fill a square would misrepresent the real relative distances. A wide
# banner is the honest frame for this particular winner's real shape.
xs = [n.x for n in render_nodes]
ys = [n.y for n in render_nodes]
data_w = max(xs) - min(xs)
data_h = max(ys) - min(ys)
raw_aspect = data_w / data_h
aspect = min(max(raw_aspect, 1.2), 5.0)  # clamp so it stays a recognizable frame, not a sliver

MARGIN = 110
INTERIOR_W = 1900
INTERIOR_H = INTERIOR_W / aspect
W = INTERIOR_W + 2 * MARGIN
H = INTERIOR_H + 2 * MARGIN

scale = min(INTERIOR_W / data_w, INTERIOR_H / data_h)
cx = (min(xs) + max(xs)) / 2
cy = (min(ys) + max(ys)) / 2


def to_canvas(x, y):
    sx = W / 2 + (x - cx) * scale
    sy = H / 2 + (y - cy) * scale  # SVG y grows downward; layout has no inherent "up", fine as-is
    return sx, sy


for n in render_nodes:
    n.sx, n.sy = to_canvas(n.x, n.y)

# ---------- edges: gentle organic curve (deterministic per-edge offset), dashed, faint ----------
edge_svg = []
id_to_idx = {n["id"]: i for i, n in enumerate(nodes)}
for k, e in enumerate(edges):
    a = id_to_node[e["source"]]
    b = id_to_node[e["target"]]
    rel = e["camp_relationship"]
    # Opacity bumped uniformly after live-platform review -- the dotted edges
    # read too faint against the cream background at the original values.
    # Relative hierarchy (cross-camp loudest, then same-camp, then neutral)
    # is preserved at the new values, same as before.
    if rel == "cross-camp":
        color = COLOR_CROSS_EDGE
        opacity = 0.32
        dash = "1,6"
        width = 1.0
    elif rel == "same-camp":
        src_family = camp_family(next(nd["camp"] for nd in nodes if nd["id"] == e["source"]))
        color = COLOR_SAME_EDGE_OWN if src_family == "own" else COLOR_SAME_EDGE_EXT
        opacity = 0.42
        dash = "3,4"
        width = 0.9
    else:  # touches-unclassified
        color = COLOR_NEUTRAL_EDGE
        opacity = 0.22
        dash = "1,4"
        width = 0.7

    dx, dy = b.sx - a.sx, b.sy - a.sy
    length = math.hypot(dx, dy) or 1.0
    # Two independent deterministic random draws per edge (seeded by edge
    # index, not by anything data-driven -- purely a rendering device):
    # where along the edge the curve bulges (not always the midpoint) and
    # how far it bulges, scaled generously with length. cross-camp edges
    # here span two tight, far-apart clusters, so nearly-parallel edges
    # bundled into a corridor is real geometry -- but drawn stick-straight
    # at that scale it read as a solid cable, exactly the "dense tangle"
    # the visual-language brief rules out. A wide, individually-varied fan
    # keeps every edge honest (same two real endpoints) while making each
    # one visually distinct instead of one indistinguishable mass.
    h1 = ((k * 2654435761) % 10007) / 10007.0
    h2 = ((k * 40503 + 17) % 10007) / 10007.0
    t = 0.30 + h1 * 0.40          # bulge point between 30-70% along the edge
    bow = (h2 - 0.5) * length * 0.55
    lx, ly = a.sx + dx * t, a.sy + dy * t
    px, py = -dy / length, dx / length
    ctrl_x, ctrl_y = lx + px * bow, ly + py * bow

    edge_svg.append(
        f'<path d="M {a.sx:.1f} {a.sy:.1f} Q {ctrl_x:.1f} {ctrl_y:.1f} {b.sx:.1f} {b.sy:.1f}" '
        f'fill="none" stroke="{color}" stroke-opacity="{opacity}" stroke-width="{width}" '
        f'stroke-dasharray="{dash}" stroke-linecap="round"/>'
    )

# ---------- glyphs: 3 shape families, custom (no circles) ----------
def diamond_path(cx_, cy_, half):
    # own-display-type: a self-contained rounded diamond -- "stands alone"
    r = half * 0.28  # corner rounding radius
    pts = [(cx_, cy_ - half), (cx_ + half, cy_), (cx_, cy_ + half), (cx_ - half, cy_)]
    d = []
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        vx, vy = x1 - x0, y1 - y0
        vlen = math.hypot(vx, vy)
        ux, uy = vx / vlen, vy / vlen
        sx_, sy_ = x0 + ux * r, y0 + uy * r
        ex_, ey_ = x1 - ux * r, y1 - uy * r
        if i == 0:
            d.append(f"M {sx_:.1f} {sy_:.1f}")
        d.append(f"L {ex_:.1f} {ey_:.1f}")
        nx0, ny0 = pts[(i + 2) % n] if i + 2 < n else pts[(i + 2) % n]
        # quadratic control = the corner vertex itself
        nxt = pts[(i + 1) % n]
        nxt2 = pts[(i + 2) % n]
        vx2, vy2 = nxt2[0] - nxt[0], nxt2[1] - nxt[1]
        vlen2 = math.hypot(vx2, vy2)
        ux2, uy2 = vx2 / vlen2, vy2 / vlen2
        sx2, sy2 = nxt[0] + ux2 * r, nxt[1] + uy2 * r
        d.append(f"Q {nxt[0]:.1f} {nxt[1]:.1f} {sx2:.1f} {sy2:.1f}")
    d.append("Z")
    return " ".join(d)


def l_tromino_path(cx_, cy_, half):
    # grid-extension: an L of 3 grid cells -- "extends/tiles" rather than stands alone
    s = half * 0.72  # cell size
    x0, y0 = cx_ - s * 1.0, cy_ - s * 1.0
    pts = [
        (x0, y0), (x0 + 2 * s, y0), (x0 + 2 * s, y0 + s),
        (x0 + s, y0 + s), (x0 + s, y0 + 2 * s), (x0, y0 + 2 * s),
    ]
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
    return d


def square_path(cx_, cy_, half):
    # unclassified: plain, small, deliberately unremarkable
    s = half * 0.62
    return (f"M {cx_-s:.1f} {cy_-s:.1f} L {cx_+s:.1f} {cy_-s:.1f} "
            f"L {cx_+s:.1f} {cy_+s:.1f} L {cx_-s:.1f} {cy_+s:.1f} Z")


def hatch_lines(cx_, cy_, half, density, color):
    """Contested-ness texture: diagonal hatch, line count scales with the
    real contestedness value. Only emitted for nodes where contested > 0
    (sparse by construction -- ~16/133 nodes)."""
    if density <= 0:
        return ""
    n_lines = max(2, int(round(density * 7)))
    out = []
    span = half * 1.6
    for i in range(n_lines):
        t = (i + 0.5) / n_lines - 0.5
        off = t * span
        x0, y0 = cx_ - span / 2 + off * 0.3, cy_ + span / 2 - off * 0.3
        x1, y1 = cx_ + span / 2 + off * 0.3, cy_ - span / 2 - off * 0.3
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
                   f'stroke="{color}" stroke-width="0.6" stroke-opacity="0.55"/>')
    return "".join(out)


node_svg = []
for n in sorted(render_nodes, key=lambda nn: -nn.half):
    # fill_opacity bumped for own/ext only (0.30->0.36) -- these are the two
    # real opposing camps the piece's "two-state" legibility depends on
    # (LAYOUT_CRITERION.md / Drift precedent language); unclassified stays
    # at 0.20, unchanged, since it's deliberately recessive by design
    # (VISUAL_LANGUAGE_SIGNALS.md) and isn't part of that two-state reading.
    # stroke-opacity raised 0.85->1.0 for all three, uniformly -- the
    # outline is what actually carries shape at small scale (measured via
    # WCAG contrast ratio against BG: own 3.75, ext 2.84, unclassified 2.16
    # at the old 0.85; own already read fine, ext/unclassified didn't), and
    # a uniform full-opacity stroke doesn't erase the real color-driven
    # contrast hierarchy between camps (own's teal still reads highest-
    # contrast against the cream background than ext's rust or
    # unclassified's gray even at 100% stroke opacity -- that hierarchy
    # comes from hue/lightness choice, not this opacity value).
    if n.family == "own":
        color = COLOR_OWN
        path = diamond_path(n.sx, n.sy, n.half)
        fill_opacity = 0.36
    elif n.family == "ext":
        color = COLOR_EXT
        path = l_tromino_path(n.sx, n.sy, n.half)
        fill_opacity = 0.36
    else:
        color = COLOR_UNCLASSIFIED
        path = square_path(n.sx, n.sy, n.half)
        fill_opacity = 0.20

    clip_id = f"clip{n.id if isinstance(n.id, int) else 'root'}"
    node_svg.append(
        f'<g>'
        f'<clipPath id="{clip_id}"><path d="{path}"/></clipPath>'
        f'<path d="{path}" fill="{color}" fill-opacity="{fill_opacity}" '
        f'stroke="{color}" stroke-opacity="1.0" stroke-width="{n.stroke_w:.2f}"/>'
        f'<g clip-path="url(#{clip_id})">{hatch_lines(n.sx, n.sy, n.half, n.contested, color)}</g>'
        f'</g>'
    )

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>
<g id="edges">{"".join(edge_svg)}</g>
<g id="nodes">{"".join(node_svg)}</g>
</svg>
'''

with open("merge_conflict_v1.svg", "w") as f:
    f.write(svg)
print(f"wrote merge_conflict_v1.svg  ({len(render_nodes)} nodes, {len(edges)} edges)")
print(f"canvas {W}x{H}  scale={scale:.3f}  data bbox {data_w:.0f}x{data_h:.0f}")
