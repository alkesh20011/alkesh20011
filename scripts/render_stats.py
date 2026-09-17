#!/usr/bin/env python3
"""Render a stats card SVG from the GitHub GraphQL API.

Runs in GitHub Actions with GITHUB_TOKEN, so it uses your own API quota and
never depends on a third-party service. Writes assets/stats.svg.
"""

import json
import os
import sys
import urllib.error
import urllib.request

USER = os.environ.get("GH_USER", "alkesh20011")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "stats.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

PALETTE = ["#8b7fc7", "#a79bdb", "#6f63ab", "#c3b9f2", "#544a80", "#9d93cc"]


def fetch():
    if not TOKEN:
        sys.exit("GITHUB_TOKEN is not set")
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": f"{USER}-profile-stats",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"GitHub API returned {e.code}: {e.read().decode()[:400]}")

    if "errors" in payload:
        sys.exit(f"GraphQL errors: {payload['errors']}")
    user = payload.get("data", {}).get("user")
    if not user:
        sys.exit(f"No such user: {USER}")
    return user


def summarise(user):
    repos = user["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)

    sizes = {}
    for r in repos:
        for edge in r["languages"]["edges"]:
            sizes[edge["node"]["name"]] = sizes.get(edge["node"]["name"], 0) + edge["size"]
    total = sum(sizes.values()) or 1
    top = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:5]

    return {
        "repos": user["repositories"]["totalCount"],
        "stars": stars,
        "followers": user["followers"]["totalCount"],
        "commits": user["contributionsCollection"]["totalCommitContributions"],
        "prs": user["contributionsCollection"]["totalPullRequestContributions"],
        "languages": [(name, size / total) for name, size in top],
    }


def esc(s):
    return (
        str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def render(s):
    W, H = 1200, 260
    font = "-apple-system,Segoe UI,Helvetica,Arial,sans-serif"

    tiles = [
        (s["commits"], "COMMITS THIS YEAR"),
        (s["repos"], "REPOSITORIES"),
        (s["prs"], "PULL REQUESTS"),
        (s["stars"], "STARS EARNED"),
    ]

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="GitHub statistics for {esc(USER)}">',
        '  <defs>',
        '    <linearGradient id="card" x1="0" y1="0" x2="1" y2="1">',
        '      <stop offset="0%" stop-color="#0b0918"/>',
        '      <stop offset="50%" stop-color="#15122b"/>',
        '      <stop offset="100%" stop-color="#0b0918"/>',
        '    </linearGradient>',
        '  </defs>',
        f'  <rect width="{W}" height="{H}" fill="url(#card)"/>',
    ]

    # stat tiles
    step = W // len(tiles)
    for i, (value, label) in enumerate(tiles):
        cx = step * i + step // 2
        out.append(
            f'  <text x="{cx}" y="92" text-anchor="middle" font-family="{font}" '
            f'font-size="46" font-weight="300" fill="#c3b9f2">{esc(value)}</text>'
        )
        out.append(
            f'  <text x="{cx}" y="118" text-anchor="middle" font-family="{font}" '
            f'font-size="9.5" letter-spacing="2.2" fill="#5f558f">{esc(label)}</text>'
        )
        if i:
            out.append(
                f'  <line x1="{step*i}" y1="58" x2="{step*i}" y2="120" '
                f'stroke="#2a2547" stroke-width="1"/>'
            )

    # language bar
    bar_x, bar_y, bar_w, bar_h = 80, 168, W - 160, 6
    out.append(
        f'  <text x="{bar_x}" y="152" font-family="{font}" font-size="9.5" '
        f'letter-spacing="2.2" fill="#5f558f">LANGUAGE MIX</text>'
    )
    out.append(
        f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="3" fill="#1d1935"/>'
    )

    cursor = bar_x
    legend = []
    for i, (name, share) in enumerate(s["languages"]):
        seg = max(share * bar_w, 2)
        colour = PALETTE[i % len(PALETTE)]
        out.append(
            f'  <rect x="{cursor:.1f}" y="{bar_y}" width="{seg:.1f}" height="{bar_h}" fill="{colour}" opacity="0.85"/>'
        )
        cursor += seg
        legend.append((name, share, colour))

    lx = bar_x
    for name, share, colour in legend:
        out.append(f'  <circle cx="{lx+3}" cy="205" r="3" fill="{colour}" opacity="0.9"/>')
        out.append(
            f'  <text x="{lx+13}" y="209" font-family="{font}" font-size="11" fill="#a49ad4">'
            f'{esc(name)} <tspan fill="#5f558f">{share*100:.0f}%</tspan></text>'
        )
        lx += 30 + len(name) * 7.4 + 34

    out.append('</svg>')
    return "\n".join(out)


def main():
    stats = summarise(fetch())
    svg = render(stats)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {OUT}")
    print(json.dumps({k: v for k, v in stats.items() if k != "languages"}, indent=2))


if __name__ == "__main__":
    main()
