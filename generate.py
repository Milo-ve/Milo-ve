#!/usr/bin/env python3
"""Generate neofetch-style profile cards (dark_mode.svg / light_mode.svg).

Stats come from the GitHub GraphQL API through the `gh` CLI. Locally this uses
your `gh auth login` session; in GitHub Actions set GH_TOKEN. Private
contribution counts only include private work if the token owner is the
profile owner and "Private contributions" is enabled on the profile.

Edit the PROFILE dict below for the static lines.
"""
from __future__ import annotations

import json
import subprocess
from html import escape
from pathlib import Path

USER = "Milo-ve"
WIDTH = 62  # characters per info line (monospace alignment)

# A list value is rendered on several lines (long values must fit in WIDTH).
PROFILE: dict[str, str | list[str]] = {
    "Building since": "Jul 2026",  # when real activity started, not account age
    "Host": "Vravura",
    "Kernel": "Relay Method (REF v1)",
    "IDE": "VS Code + Claude Code",
    "Languages.Computer": "HTML, CSS, JSON, YAML",
    "Languages.Real": "Spanish, English, Chinese (basic)",
    "Focus.Building": "AI-assisted workflows, web products",
    "Focus.Domains": ["Innovation, strategy, financial services,", "age-tech and health-tech"],
    "Email": "milo@vravura.com",
}

ART = {
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    "I": ["###", " # ", " # ", " # ", "###"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
}

THEMES = {
    "dark_mode": dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", val="#a5d6ff",
                      dot="#616e7c", art="#e6edf3", add="#3fb950"),
    "light_mode": dict(bg="#f6f8fa", fg="#24292f", key="#953800", val="#0550ae",
                       dot="#8c959f", art="#24292f", add="#1a7f37"),
}


def gh_graphql(query: str) -> dict:
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={query}"],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)["data"]["user"]


def fetch_stats() -> dict[str, str]:
    # Only aggregates are rendered: no repository names, no code.
    u = gh_graphql(
        'query{user(login:"%s"){'
        "contributionsCollection{contributionCalendar{totalContributions "
        "weeks{contributionDays{contributionCount}}}} "
        "repositories(ownerAffiliations:OWNER,first:100){nodes{isFork "
        "languages(first:8,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}" % USER
    )
    # `user` key is unwrapped by gh_graphql
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
    # Language mix over every non-fork repo you own, private ones included.
    sizes: dict[str, int] = {}
    for repo in u["repositories"]["nodes"]:
        if repo["isFork"]:
            continue
        for e in repo["languages"]["edges"]:
            sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]
    total = sum(sizes.values()) or 1
    top = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:3]
    return {
        "Contributions": f"{cal['totalContributions']} (12 mo)",
        "Recent": f"{sum(days[-90:])} (90 d)",
        "Languages": ", ".join(f"{n} {round(s * 100 / total)}%" for n, s in top),
    }


def art_lines(word: str = "MILO") -> list[str]:
    """Portrait from art.txt (see make_ascii.py); falls back to block letters."""
    f = Path(__file__).parent / "art.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").splitlines()
    rows = []
    for r in range(5):
        rows.append("  ".join(ART[c][r] for c in word).replace("#", "█"))
    return rows


def leader(key: str, value: str) -> tuple[str, str, str]:
    dots = max(WIDTH - len(key) - len(value) - 2, 2)
    return key, " " + "." * dots + " ", value


def build(theme: str, c: dict[str, str], stats: dict[str, str]) -> str:
    fs, lh = 15, 22  # font size, line height
    cw = fs * 0.602  # monospace char width
    art = art_lines()
    art_cols = max(len(r) for r in art)
    portrait = (Path(__file__).parent / "art.txt").exists()
    art_fs, art_lh = (7, 8) if portrait else (18, 20)
    x_art = 24
    x_txt = int(x_art + art_cols * art_fs * 0.602 + 30)
    lines: list[str] = []  # (kind, payload)
    lines.append(("title", "milo@github " + "-" * (WIDTH - len("milo@github "))))
    def add_kv(key: str) -> None:
        value = PROFILE[key]
        for i, part in enumerate([value] if isinstance(value, str) else value):
            lines.append(("kv", (key if i == 0 else "", part)))

    for k in ("Building since", "Host", "Kernel", "IDE"):
        add_kv(k)
    lines.append(("gap", ""))
    lines.append(("kv", ("Languages.Programming", stats["Languages"])))
    for k in ("Languages.Computer", "Languages.Real"):
        add_kv(k)
    lines.append(("gap", ""))
    for k in ("Focus.Building", "Focus.Domains"):
        add_kv(k)
    lines.append(("section", "Contact"))
    add_kv("Email")
    lines.append(("section", "GitHub Stats"))
    lines.append(("stats", stats))

    height = max(40 + lh * (len(lines) + 1), len(art) * art_lh + 36)
    width = int(x_txt + WIDTH * cw + 30)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" '
        f'font-size="{fs}">',
        f'<rect width="100%" height="100%" rx="14" fill="{c["bg"]}"/>',
    ]

    # ASCII art, vertically centred
    art_y0 = (height - len(art) * art_lh) / 2
    out.append(f'<g font-size="{art_fs}" font-weight="bold" fill="{c["art"]}" xml:space="preserve" style="white-space:pre">')
    for i, row in enumerate(art):
        out.append(f'<text x="{x_art}" y="{art_y0 + (i + 1) * art_lh:.0f}" xml:space="preserve" '
                   f'style="white-space:pre">{escape(row)}</text>')
    out.append("</g>")

    y = 36
    for kind, p in lines:
        if kind == "gap":
            y += lh // 2
            continue
        t = f'<text x="{x_txt}" y="{y}" xml:space="preserve" style="white-space:pre" fill="{c["fg"]}">'
        if kind == "title":
            out.append(f'{t}<tspan fill="{c["fg"]}" font-weight="bold">{escape(p)}</tspan></text>')
        elif kind == "section":
            pre = "- " + p + " "
            out.append(f'{t}<tspan fill="{c["fg"]}">{escape(pre)}{"-" * (WIDTH - len(pre))}</tspan></text>')
        elif kind == "kv":
            k, d, v = leader(*p)
            out.append(f'{t}<tspan fill="{c["key"]}">{escape(k)}</tspan>'
                       f'<tspan fill="{c["dot"]}">{d}</tspan><tspan fill="{c["val"]}">{escape(v)}</tspan></text>')
        elif kind == "stats":
            s = p
            segs = [("Contributions", s["Contributions"]), ("Recent", s["Recent"])]
            parts = []
            for i, (k, v) in enumerate(segs):
                sep = f'<tspan fill="{c["fg"]}"> | </tspan>' if i else ""
                parts.append(f'{sep}<tspan fill="{c["key"]}">{k}</tspan>'
                             f'<tspan fill="{c["dot"]}">: </tspan><tspan fill="{c["val"]}">{escape(v)}</tspan>')
            out.append(t + "".join(parts) + "</text>")
        y += lh
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    stats = fetch_stats()
    here = Path(__file__).parent
    for name, colors in THEMES.items():
        (here / f"{name}.svg").write_text(build(name, colors, stats), encoding="utf-8")
    print("wrote", ", ".join(f"{n}.svg" for n in THEMES), stats)


if __name__ == "__main__":
    main()
