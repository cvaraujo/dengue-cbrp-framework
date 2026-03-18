#!/usr/bin/env python3
"""Generate the Simheuristic flow diagram programmatically."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "Liberation Serif"],
    "mathtext.fontset": "cm",
})

W, H = 14, 30
fig, ax = plt.subplots(figsize=(10.0, 21.4))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")

COLORS = {
    "blue":   {"border": "#4A90C4", "fill": "#EAF2FA", "arrow": "#2E6DA4"},
    "green":  {"border": "#5AAA5A", "fill": "#EAF6EA", "arrow": "#3D8B3D"},
    "orange": {"border": "#D4952B", "fill": "#FDF4E3", "arrow": "#C47F17"},
    "purple": {"border": "#8B6BAE", "fill": "#F2EDF7", "arrow": "#6B4E8E"},
    "salmon": {"border": "#CC7766", "fill": "#FCEEE8", "arrow": "#B05545"},
}

CX = 7.0
INTER = 0.65


def group_box(x, y, w, h, label, ckey):
    c = COLORS[ckey]
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                          fc=c["fill"], ec=c["border"], lw=2.5, zorder=1)
    ax.add_patch(rect)
    tw = len(label) * 0.16 + 0.6
    tab = FancyBboxPatch((x + 0.15, y + h - 0.52), tw, 0.44,
                         boxstyle="round,pad=0.06", fc=c["border"], ec="none",
                         alpha=0.13, zorder=2)
    ax.add_patch(tab)
    ax.text(x + 0.35, y + h - 0.30, label, fontsize=11.5, fontweight="bold",
            color=c["border"], va="center", zorder=3)


def box(cx, cy, w, h, text, sub=None, fs=9.5):
    rect = FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                          boxstyle="round,pad=0.05", fc="white", ec="#888888",
                          lw=1.0, zorder=2)
    ax.add_patch(rect)
    if sub:
        ax.text(cx, cy + h * 0.17, text, fontsize=fs, ha="center",
                va="center", fontweight="medium", zorder=3)
        ax.text(cx, cy - h * 0.22, sub, fontsize=max(fs - 1.5, 7),
                ha="center", va="center", color="#555555", style="italic",
                zorder=3)
    else:
        ax.text(cx, cy, text, fontsize=fs, ha="center", va="center",
                fontweight="medium", zorder=3)


def diamond(cx, cy, w, h, text, fs=9):
    d = plt.Polygon([(cx, cy + h / 2), (cx + w / 2, cy),
                     (cx, cy - h / 2), (cx - w / 2, cy)],
                    fc="white", ec="#888888", lw=1.0, zorder=2)
    ax.add_patch(d)
    ax.text(cx, cy, text, fontsize=fs, ha="center", va="center", zorder=3)


def arr(x1, y1, x2, y2, c="#555555", lw=1.2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=c, lw=lw), zorder=2)


def line(pts, c="#555555", lw=1.2, ls="-"):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=c, lw=lw, ls=ls, zorder=2)


def big_arr(cx, y1, y2, ckey, label):
    c = COLORS[ckey]
    ax.annotate("", xy=(cx, y2), xytext=(cx, y1),
                arrowprops=dict(arrowstyle="-|>", color=c["arrow"], lw=4,
                                mutation_scale=20), zorder=4)
    # my = (y1 + y2) / 2
    # circ = plt.Circle((cx + 0.45, my), 0.22, fc=c["arrow"], ec="white",
    #                   lw=2, zorder=5)
    # ax.add_patch(circ)
    # ax.text(cx + 0.45, my, label, fontsize=10, ha="center", va="center",
    #         color="white", fontweight="bold", zorder=6)


def label(x, y, text, color="#555555", fs=10, ha="center", bold=True):
    ax.text(x, y, text, fontsize=fs, color=color, ha=ha, va="center",
            fontweight="bold" if bold else "normal", zorder=4)


# ── Shared 2×2 grid dimensions ──
BW = 5.2
BH = 0.62
COL_GAP = 1.0
ROW_GAP = 0.60
LBL_H = 0.70
PAD_B = 0.28

LX = CX - (BW + COL_GAP) / 2
RX = CX + (BW + COL_GAP) / 2


def grid_2x2(items, y_top, fs=9.5):
    cy1 = y_top - BH / 2
    cy2 = cy1 - BH - ROW_GAP

    pos = [(LX, cy1), (RX, cy1), (LX, cy2), (RX, cy2)]
    for (t, s), (px, py) in zip(items, pos):
        box(px, py, BW, BH, t, s, fs=fs)

    arr(LX + BW / 2, cy1, RX - BW / 2, cy1)

    mid_y = (cy1 - BH / 2 + cy2 + BH / 2) / 2
    line([(RX, cy1 - BH / 2), (RX, mid_y), (LX, mid_y)])
    arr(LX, mid_y, LX, cy2 + BH / 2)

    arr(LX + BW / 2, cy2, RX - BW / 2, cy2)
    return cy2 - BH / 2


GRP_X = 1.0
GRP_W = 12.0

# ═══════════════════════════════════════════════════════════════════
# GROUP 1 — Environment Setup
# ═══════════════════════════════════════════════════════════════════
g1_top = 28.0
g1_h = LBL_H + 2 * BH + ROW_GAP + PAD_B
g1_bot = g1_top - g1_h
group_box(GRP_X, g1_bot, GRP_W, g1_h, "1. Environment Setup", "blue")

grid_2x2([
    ("Load city map (OpenStreetMap)", "Build graph: nodes, arcs, blocks"),
    ("Retrieve real dengue cases", "Infected / recovered per block"),
    ("Write graph input file (graph.txt)", "Nodes, arcs, block infections"),
    ("Create initial population", "People, mosquitoes, breeding sites"),
], g1_top - LBL_H)

big_arr(CX, g1_bot, g1_bot - INTER, "blue", "")

# ═══════════════════════════════════════════════════════════════════
# GROUP 2 — Start Services
# ═══════════════════════════════════════════════════════════════════
g2_top = g1_bot - INTER
g2_h = LBL_H + BH + PAD_B
g2_bot = g2_top - g2_h
group_box(GRP_X, g2_bot, GRP_W, g2_h, "2. Start Services", "green")

cy2 = g2_top - LBL_H - BH / 2
box(LX, cy2, BW, BH, "Start GAMA Simulation Server",
    "Agent-based epidemic simulation", fs=9.5)
box(RX, cy2, BW, BH, "Start C++ Optimization Server",
    "Graph loading, Floyd-Warshall, ZMQ", fs=9.5)
line([(LX + BW / 2 + 0.12, cy2), (RX - BW / 2 - 0.12, cy2)],
     c="#bbbbbb", lw=1.2, ls="--")

big_arr(CX, g2_bot, g2_bot - INTER, "green", "2")

# ═══════════════════════════════════════════════════════════════════
# GROUP 3 — Initial Scenario Generation
# ═══════════════════════════════════════════════════════════════════
g3_top = g2_bot - INTER
g3_h = LBL_H + 2 * BH + ROW_GAP + PAD_B
g3_bot = g3_top - g3_h
group_box(GRP_X, g3_bot, GRP_W, g3_h, "3. Initial Scenario Generation", "orange")

grid_2x2([
    ("Run GAMA batch simulation", "14 epidemic cycles, stochastic variation"),
    ("Generate stochastic scenarios", "Infected per block, for each scenario"),
    ("Store scenarios in database", "Accumulate for future evaluations"),
    ("Load scenarios into optimizer", "Send load command via ZMQ"),
], g3_top - LBL_H)

big_arr(CX, g3_bot, g3_bot - INTER, "orange", "3")

# ═══════════════════════════════════════════════════════════════════
# GROUP 4 — Optimization Loop  (manually laid out)
# ═══════════════════════════════════════════════════════════════════
g4_top = g3_bot - INTER

FBW = 7.2
FBH = 0.58
BBW = 4.2
BBH = 0.58
DW = 3.6
DH = 1.3

ya = g4_top - LBL_H - FBH / 2
yb = ya - FBH / 2 - 0.40 - FBH / 2
yc = yb - FBH / 2 - 0.55 - DH / 2

yr1 = yc - 0.85
yr2 = yr1 - BBH / 2 - 0.40 - BBH / 2
yr3 = yr2 - BBH / 2 - 0.40 - BBH / 2

left_bottom = yr2 - BBH / 2
right_bottom = yr3 - BBH / 2
merge_y = min(left_bottom, right_bottom) - 0.40

ye = merge_y - 0.35 - FBH / 2
yf = ye - FBH / 2 - 0.50 - DH / 2
yg = yf - DH / 2 - 0.55 - DH / 2
g4_bot = yg - DH / 2 - 0.50

g4_h = g4_top - g4_bot
G4_X, G4_W = 0.5, 13.0
group_box(G4_X, g4_bot, G4_W, g4_h,
          "4. Optimization Loop", "purple")

lcx = 3.0
rcx = 11.3

# ── A: Call optimizer ──
box(CX, ya, FBW, FBH, "Call C++ optimization algorithm",
    "Multi-start heuristic generates a candidate solution", fs=10)
arr(CX, ya - FBH / 2, CX, yb + FBH / 2)

# ── B: Receive solution ──
box(CX, yb, FBW, FBH, "Receive candidate solution",
    "Blocks to visit + deterministic OF value", fs=10)
arr(CX, yb - FBH / 2, CX, yc + DH / 2)

# ── C: Diamond — surrogate mode? ──
diamond(CX, yc, DW, DH, "Surrogate\nmode?", fs=10)

# Left branch (Yes): horizontal line → turn down → box (same pattern as No)
label(CX - DW / 2 - 0.35, yc + 0.35, "Yes", "#3D8B3D", fs=10)
line([(CX - DW / 2, yc), (lcx, yc)])
arr(lcx, yc, lcx, yr2 + BBH / 2)
box(lcx, yr2, BBW*0.8, BBH, "Sample from\nstored scenarios (fast)", None, fs=9)

# Right branch (No): horizontal line → turn down → boxes
label(CX + DW / 2 + 0.3, yc + 0.35, "No (every N iter.)", "#CC4444", fs=9)
line([(CX + DW / 2, yc), (rcx, yc)])
arr(rcx, yc, rcx, yr1 + BBH / 2)

box(rcx, yr1, BBW, BBH, "Run new GAMA simulation",
    "Fresh epidemic scenarios", fs=9)
arr(rcx, yr1 - BBH / 2, rcx, yr2 + BBH / 2)

box(rcx, yr2, BBW, BBH, "Add scenarios to pool",
    "Load into C++ optimizer", fs=9)
arr(rcx, yr2 - BBH / 2, rcx, yr3 + BBH / 2)

box(rcx, yr3, BBW, BBH, "Reactivate surrogate mode", None, fs=9)

# Merge branches
line([(lcx, yr2 - BBH / 2), (lcx, merge_y), (CX, merge_y)])
line([(rcx, yr3 - BBH / 2), (rcx, merge_y), (CX, merge_y)])
arr(CX, merge_y, CX, ye + FBH / 2)

# ── E: Compute stochastic OF ──
box(CX, ye, FBW + 1.2, FBH + 0.06,
    "Compute stochastic objective function",
    r"$OF_{stoch} = OF_{det} + \alpha \cdot \mathbb{E}[\mathrm{cases\ in\ selected\ blocks}]$",
    fs=10)
arr(CX, ye - (FBH + 0.06) / 2, CX, yf + DH / 2)

# ── F: Diamond — improved? ──
diamond(CX, yf, DW + 0.8, DH, "Better than\nbest OF?", fs=10)

ucx = 11.3
label(CX + (DW + 0.8) / 2 + 0.35, yf + 0.35, "Yes", "#3D8B3D", fs=10)
arr(CX + (DW + 0.8) / 2, yf, ucx - 1.3, yf)
box(ucx, yf, 2.6, 0.72, "Update best\nsolution and\nElite Set (top-K)", None, fs=9)

label(CX + 0.35, yf - DH / 2 - 0.25, "No", "#CC4444", fs=10)
arr(CX, yf - DH / 2, CX, yg + DH / 2)

# ── G: Diamond — time limit? ──
diamond(CX, yg, DW, DH, "Time limit\nreached?", fs=10)

label(CX, yg - DH / 2 - 0.25, "Yes", "#3D8B3D", fs=10)
# arr(CX, yg - DH / 2, CX, g4_bot + 0.15)

loop_x = G4_X + 0.55
label(CX - DW / 2 - 0.35, yg + 0.35, "No", "#CC4444", fs=10)
line([(CX - DW / 2, yg), (loop_x, yg)],
     c=COLORS["purple"]["arrow"], lw=2.2, ls=(0, (5, 3)))
line([(loop_x, yg), (loop_x, ya)],
     c=COLORS["purple"]["arrow"], lw=2.2, ls=(0, (5, 3)))
arr(loop_x, ya, CX - FBW / 2, ya, c=COLORS["purple"]["arrow"], lw=2.2)

big_arr(CX, g4_bot, g4_bot - INTER, "purple", "4")

# ═══════════════════════════════════════════════════════════════════
# GROUP 5 — Risk Analysis
# ═══════════════════════════════════════════════════════════════════
g5_top = g4_bot - INTER
g5_h = LBL_H + 2 * BH + ROW_GAP + PAD_B
g5_bot = g5_top - g5_h
group_box(GRP_X, g5_bot, GRP_W, g5_h, "5. Risk Analysis", "salmon")

grid_2x2([
    ("Select top-K elite solutions", None),
    ("Simulate with nebulization", "Intervention on selected blocks"),
    ("Simulate baseline (no interv.)", "Compare effect of nebulization"),
    ("Generate comparative report", "Statistics, boxplots, risk metrics"),
], g5_top - LBL_H)

OUT = "/home/carlos/Documentos/dengue-cbrp-framework/simheuristic_flow_diagram"
plt.savefig(f"{OUT}.png", dpi=300, bbox_inches="tight", facecolor="white",
            pad_inches=0.2)
plt.savefig(f"{OUT}.pdf", format="pdf", bbox_inches="tight", facecolor="white",
            pad_inches=0.2)
print("Done — PNG + PDF saved")
