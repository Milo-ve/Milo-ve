#!/usr/bin/env python3
"""Generate neofetch-style profile cards (dark_mode.svg / light_mode.svg).

Stats come from the GitHub GraphQL API through the `gh` CLI. Locally this uses
your `gh auth login` session; in GitHub Actions set GH_TOKEN. Private
contribution counts only include private work if the token owner is the
profile owner and "Private contributions" is enabled on the profile.

Edit the PROFILE dict below for the static lines.
"""
from __future__ import annotations

import calendar
import json
import subprocess
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = "Milo-ve"
WIDTH = 62  # characters per info line (monospace alignment)

# A list value is rendered on several lines (long values must fit in WIDTH).
PROFILE: dict[str, str | list[str]] = {
    "Host": "Vravura",
    "Kernel": "Relay Method (REF v1)",
    "IDE": "VS Code + Claude Code",
    "Languages.Programming": "TypeScript, Python, Astro",
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
    u = gh_graphql(
        'query{user(login:"%s"){createdAt repositories(ownerAffiliations:OWNER)'
        "{totalCount} contributionsCollection{totalCommitContributions "
        "restrictedContributionsCount totalPullRequestContributions}}}" % USER
    )
    # `user` key is unwrapped by gh_graphql
    created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    months = (now.year - created.year) * 12 + now.month - created.month
    day = now.day - created.day
    if day < 0:
        months -= 1
        prev_year, prev_month = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
        day += calendar.monthrange(prev_year, prev_month)[1]
    cc = u["contributionsCollection"]
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    return {
        "Uptime": f"{months // 12} years, {months % 12} months, {day} days",
        "Repos": str(u["repositories"]["totalCount"]),
        "Commits": f"{commits} (12 mo)",
        "PRs": str(cc["totalPullRequestContributions"]),
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

    lines.append(("kv", ("Uptime", stats["Uptime"])))
    for k in ("Host", "Kernel", "IDE"):
        add_kv(k)
    lines.append(("gap", ""))
    for k in ("Languages.Programming", "Languages.Computer", "Languages.Real"):
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
            segs = [("Repos", s["Repos"]), ("Commits", s["Commits"]), ("PRs", s["PRs"])]
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
