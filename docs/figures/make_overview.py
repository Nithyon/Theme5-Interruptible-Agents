"""Draw docs/figures/commit_harness_overview.svg (the README's overview figure).

Layout follows Figure 1 of the Full-Duplex-Bench v3 paper (arXiv 2604.04847): user speech at
the bottom, the agent in the middle, agent speech on top, the tool pool on the left. The
middle layer is ours: Gemini 3.8 Live proposes a call, the Commit Harness holds it until the
user has finished, a correction replaces it, and only then does it run once.

The timings match fdb_agent/gate.py (0.9 s quiet, 1.8 s after a hesitation, 8 s cap). The
utterance is an illustration, not one of the benchmark recordings.

    python docs/figures/make_overview.py
"""
import math
import os
import random

W, H = 1200, 790
T0_X, PX_PER_S = 250, 90          # timeline: t = 0 s at x = 250, 10 s at x = 1150


def X(t):
    return T0_X + PX_PER_S * t


FONT = "Helvetica, Arial, sans-serif"
MONO = "SFMono-Regular, Consolas, Menlo, monospace"
INK, MUTED, WAVE = "#1f2933", "#52606d", "#3d6fa8"
FILLER, FILLER_BG = "#2f855a", "#d9f2e3"
CORR, CORR_BG = "#7b3f8c", "#eedcf2"
HELD, COMMIT, BAND = "#dd6b20", "#2f855a", "#cfe3fb"

out = []


def add(s):
    out.append(s)


def text(x, y, s, size=13, color=INK, anchor="start", weight="normal", family=FONT, style="normal"):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{color}" '
        f'text-anchor="{anchor}" font-weight="{weight}" font-style="{style}">{s}</text>')


def rect(x, y, w, h, fill="none", stroke="none", rx=6, dash=None, sw=1.2, opacity=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}"{d} opacity="{opacity}"/>')


def arrow(x1, y1, x2, y2, color=INK, sw=1.6, marker="ink"):
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
        f'stroke-width="{sw}" marker-end="url(#{marker})"/>')


def waveform(cy, amp, segments, seed, quiet=0.06):
    """Vertical-bar waveform. segments: [(t_start, t_end, loudness)]; elsewhere near-silent."""
    rnd = random.Random(seed)
    d = []
    x = X(0)
    while x <= X(10):
        t = (x - T0_X) / PX_PER_S
        a = quiet * (0.5 + rnd.random())
        for s, e, loud in segments:
            if s <= t <= e:
                edge = min(1.0, (t - s) / 0.08, (e - t) / 0.08)           # soft onset/offset
                syll = 0.45 + 0.55 * abs(math.sin(t * 11.0 + seed))       # syllable rhythm
                a = max(a, loud * edge * syll * (0.55 + 0.45 * rnd.random()))
        h = max(0.8, amp * a)
        d.append(f"M{x:.1f} {cy - h:.1f}V{cy + h:.1f}")
        x += 2.6
    add(f'<path d="{"".join(d)}" stroke="{WAVE}" stroke-width="1.5" fill="none"/>')


def pill(x, y, w, label, color, bg, size=12, strike=False):
    rect(x, y, w, 24, fill=bg, stroke=color, rx=12, sw=1.3)
    text(x + w / 2, y + 16.5, label, size=size, color=color, anchor="middle", family=MONO)
    if strike:
        add(f'<line x1="{x + 30:.1f}" y1="{y + 12:.1f}" x2="{x + w - 12:.1f}" y2="{y + 12:.1f}" '
            f'stroke="{color}" stroke-width="1.3"/>')


def badge(x, n, color):
    add(f'<circle cx="{x:.1f}" cy="{TRACK}" r="9" fill="{color}"/>')
    text(x, TRACK + 4.5, n, size=12, color="#ffffff", anchor="middle", weight="bold")


# --- canvas -------------------------------------------------------------------------
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'role="img" aria-label="Commit Harness overview: the user corrects New York to Boston; the '
    f'harness holds the first proposed call, replaces it with the corrected one, and runs it once '
    f'after 0.9 seconds of quiet.">')
add('<defs>')
for name, color in (("ink", INK), ("held", HELD), ("commit", COMMIT), ("muted", MUTED), ("corr", CORR), ("result", "#c53030")):
    add(f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{color}"/></marker>')
add('</defs>')
rect(0, 0, W, H, fill="#ffffff", stroke="#d9e2ec", rx=14)

# quiet window before the commit, drawn first so it sits behind every lane (as in the paper)
rect(X(5.0), 96, X(5.9) - X(5.0), 606, fill=BAND, rx=0, opacity=0.55)

# --- header -------------------------------------------------------------------------
add(f'<text x="{W / 2}" y="38" font-family="{FONT}" font-size="21" font-weight="bold" '
    f'text-anchor="middle" fill="{INK}">Commit Harness: '
    f'<tspan fill="#2b6cb0">(1) Propose</tspan>  →  '
    f'<tspan fill="{HELD}">(2) Settle</tspan>  →  '
    f'<tspan fill="{COMMIT}">(3) Commit</tspan></text>')
text(W / 2, 64, "Scored by Full-Duplex-Bench v3 on 100 real recordings: tool use (Pass@1), "
     "turn-taking, latency", size=13, color=MUTED, anchor="middle")

# --- agent speech lane (top) ----------------------------------------------------------
text(40, 168, "Agent speech", size=15, weight="bold")
rect(X(0) - 6, 92, X(10) - X(0) + 12, 128, stroke="#52606d", dash="5 4", rx=4)
text(X(2.6), 140, "[Listening]", size=13, weight="bold", anchor="middle")
rect(X(5.95), 100, 190, 52, fill="#ffffff", stroke=INK, rx=3)
text(X(5.95) + 95, 118, "[Tool use]", size=12.5, weight="bold", anchor="middle")
text(X(5.95) + 95, 139, "search_flights(“Boston”)", size=11.5, anchor="middle", family=MONO)
rect(X(8.2) - 8, 100, 170, 52, fill="#ffffff", stroke=INK, rx=3)
text(X(8.2) + 77, 118, "[Speaking]", size=12.5, weight="bold", anchor="middle")
text(X(8.2) + 77, 139, "“I found flights to Boston…”", size=11.5, anchor="middle")
waveform(186, 26, [(6.55, 9.75, 1.0)], seed=3, quiet=0.09)

# --- arrows between lanes -------------------------------------------------------------
for i in range(15):
    x = X(0.25 + i * 0.68)
    arrow(x, 244, x, 225)
    arrow(x, 540, x, 511)

# --- the agent (middle) -----------------------------------------------------------------
rect(X(0) - 6, 247, X(10) - X(0) + 12, 258, fill="#f5f7fa", stroke="#9aa5b1", rx=12, sw=1.5)
rect(X(0) + 8, 259, X(10) - X(0) - 16, 38, fill="#e3ecf8", stroke="#9fb6d6", rx=8)
add(f'<text x="{(X(0) + X(10)) / 2}" y="283" font-family="{FONT}" font-size="15" fill="{INK}" '
    f'text-anchor="middle"><tspan font-weight="bold">Gemini 3.8 Live</tspan> · the talker: hears the '
    f'user, speaks, and <tspan fill="#2b6cb0" font-weight="bold">proposes</tspan> tool calls</text>')

TRACK = 372
text(X(0) + 14, TRACK - 8, "Commit Harness", size=14, weight="bold")
text(X(0) + 14, TRACK + 20, "fdb_agent/gate.py", size=11.5, color=MUTED, family=MONO)
add(f'<line x1="{X(0) + 140:.1f}" y1="{TRACK}" x2="{X(10) - 10:.1f}" y2="{TRACK}" stroke="#9aa5b1" '
    f'stroke-width="1.5"/>')

# settle: 0.9 s of quiet after the user's last word (drawn under the badges)
add(f'<line x1="{X(5.05):.1f}" y1="{TRACK}" x2="{X(5.9):.1f}" y2="{TRACK}" stroke="{HELD}" '
    f'stroke-width="4"/>')
# (1) first proposal: held, then replaced when the user says "wait…"
pill(X(3.4) - 150, TRACK - 44, 300, "search_flights(“New York”) · held", HELD, "#fdebd9", strike=True)
text(X(3.4) + 156, TRACK - 27, "replaced", size=11.5, color=MUTED, style="italic")
badge(X(3.4), "1", HELD)
# (2) corrected proposal
pill(X(5.05) - 150, TRACK + 14, 262, "search_flights(“Boston”) · held", HELD, "#fdebd9")
badge(X(5.05), "2", HELD)
text(X(5.47), TRACK - 10, "0.9 s quiet", size=11.5, color=HELD, anchor="middle", weight="bold")
# (3) commit
badge(X(5.9), "3", COMMIT)
pill(X(5.9) + 14, TRACK - 44, 176, "commit: runs once", COMMIT, "#dcf2e5")
arrow(X(5.9), TRACK - 10, X(5.95) + 40, 158, color=COMMIT, sw=1.6, marker="commit")

# deciders: who says whether the user has finished
CH = 420
for x, w, label in ((X(0) + 14, 200, "<tspan font-weight='bold'>Reflex</tspan> · word patterns"),
                    (X(0) + 224, 256, "<tspan font-weight='bold'>Reasoner</tspan> · TypeSafe Jev, optional"),
                    (X(0) + 490, 214, "<tspan font-weight='bold'>Listener</tspan> · Smart Turn, off")):
    rect(x, CH, w, 28, fill="#ffffff", stroke="#9aa5b1", rx=6)
    add(f'<text x="{x + w / 2:.1f}" y="{CH + 19}" font-family="{FONT}" font-size="12.5" fill="{INK}" '
        f'text-anchor="middle">{label}</text>')
text(X(0) + 714, CH + 19, "← has the user finished?", size=12.5, color=MUTED)
text((X(0) + X(10)) / 2, 490,
     "Waits for 0.9 s of quiet (1.8 s after “um”, “wait”), at most 8 s  ·  a newer call to the same "
     "tool replaces a held one  ·  “never mind” withdraws it  ·  no call runs twice", size=12, color=MUTED, anchor="middle")

# --- tool pool (left) -----------------------------------------------------------------
rect(22, 280, 158, 162, fill="#eef3fa", stroke="#52606d", rx=8, sw=1.4)
for i, (name, color) in enumerate((("Travel", "#2b6cb0"), ("Finance", "#b7791f"),
                                   ("Housing", "#c53030"), ("E-comm", "#6b46c1"))):
    tx, ty = 32 + (i % 2) * 72, 290 + (i // 2) * 72
    rect(tx, ty, 66, 62, fill="#ffffff", stroke=color, rx=6, sw=1.6)
    text(tx + 33, ty + 36, name, size=12.5, color=color, anchor="middle", weight="bold")
text(101, 462, "Tool pool", size=14, weight="bold", anchor="middle")
text(101, 479, "12 tools, 4 domains", size=11.5, color=MUTED, anchor="middle")
arrow(X(0) - 8, 340, 184, 340, color=COMMIT, sw=3, marker="commit")
text(215, 331, "commit", size=11, color=COMMIT, anchor="middle", weight="bold")
arrow(184, 384, X(0) - 8, 384, color="#c53030", sw=3, marker="result")
text(215, 402, "result", size=11, color="#c53030", anchor="middle", weight="bold")

# --- user speech lane (bottom) ----------------------------------------------------------
text(40, 580, "User speech", size=15, weight="bold")
add(f'<circle cx="84" cy="620" r="17" fill="#e4e7eb" stroke="{MUTED}" stroke-width="1.5"/>')
add(f'<path d="M50 688 Q52 646 84 644 Q116 646 118 688 Z" fill="#e4e7eb" stroke="{MUTED}" stroke-width="1.5"/>')
rect(146, 612, 16, 30, fill="#52606d", rx=8)
add(f'<path d="M140 632 Q140 652 154 652 Q168 652 168 632" stroke="#52606d" stroke-width="2" fill="none"/>')
add(f'<line x1="154" y1="652" x2="154" y2="666" stroke="#52606d" stroke-width="2"/>')
arrow(176, 640, X(0) - 10, 640, color=MUTED, sw=1.5, marker="muted")

rect(X(1.05), 544, X(2.55) - X(1.05), 26, fill=FILLER_BG, stroke=FILLER, rx=5)
text((X(1.05) + X(2.55)) / 2, 562, "Filler: “um…”", size=12.5, color=FILLER, anchor="middle", weight="bold")
rect(X(3.45), 544, X(5.1) - X(3.45), 26, fill=CORR_BG, stroke=CORR, rx=5)
text((X(3.45) + X(5.1)) / 2, 562, "Self-correction", size=12.5, color=CORR, anchor="middle", weight="bold")
rect(X(1.4), 578, X(2.2) - X(1.4), 110, fill=FILLER_BG, stroke=FILLER, rx=4, dash="5 4", sw=1.5, opacity=0.9)
rect(X(3.5), 578, X(5.05) - X(3.5), 110, fill=CORR_BG, stroke=CORR, rx=4, dash="5 4", sw=1.5, opacity=0.9)
waveform(633, 46, [(0.0, 1.3, 1.0), (1.5, 2.1, 0.55), (2.3, 3.3, 1.0), (3.6, 4.2, 0.8), (4.4, 5.0, 1.0)],
         seed=11, quiet=0.07)
text(X(7.6), 612, "[the user has finished]", size=12.5, color=MUTED, anchor="middle", weight="bold")

WY = 716
for t, word, color, weight in ((0.65, "Book me a flight", INK, "normal"), (1.8, "um…", FILLER, "bold"),
                               (2.8, "to New York", INK, "normal"), (3.9, "wait…", CORR, "bold"),
                               (4.72, "Boston.", INK, "bold")):
    text(X(t), WY, word, size=14, color=color, anchor="middle", weight=weight)
arrow(X(4.15), WY - 5, X(4.4), WY - 5, color=CORR, sw=1.5, marker="corr")

# --- caption ------------------------------------------------------------------------
text(W / 2, 752, "An illustration of the mechanism, not a benchmark recording. On the benchmark the "
     "harness changed what ran in 2 of 100 recordings:", size=12, color=MUTED, anchor="middle", style="italic")
text(W / 2, 770, "Gemini 3.8 Live usually proposes a call only after the user has finished.", size=12, color=MUTED, anchor="middle", style="italic")

add('</svg>')

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commit_harness_overview.svg")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print("wrote", path)
