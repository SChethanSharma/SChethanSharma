#!/usr/bin/env python3
"""Aggregate languages across all user repos and inject an SVG tech-stack into README.md.

Requirements: set GITHUB_TOKEN env var for higher rate limits (optional).
"""
import os
import requests
from collections import defaultdict

USER = "SChethanSharma"
README = "README.md"
START_MARKER = "<!-- TECHSTACK:START -->"
END_MARKER = "<!-- TECHSTACK:END -->"


def github_repos(user):
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"https://api.github.com/users/{user}/repos?per_page=200"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def repo_languages(owner, repo_name, headers):
    url = f"https://api.github.com/repos/{owner}/{repo_name}/languages"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def aggregate_languages(repos):
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    totals = defaultdict(int)
    for r in repos:
        if r.get("fork") or r.get("archived"):
            continue
        name = r["name"]
        try:
            langs = repo_languages(USER, name, headers)
        except Exception:
            continue
        for lang, bytes_count in langs.items():
            totals[lang] += bytes_count
    # normalize/merge similar languages: CSS+SCSS -> SCSS, Jupyter Notebook+Python -> Python
    mapping = {
        'CSS': 'SCSS',
        'SCSS': 'SCSS',
        'Jupyter Notebook': 'Python',
        'Jupyter': 'Python',
        'Python': 'Python',
    }
    normalized = defaultdict(int)
    for lang, val in totals.items():
        mapped = mapping.get(lang, lang)
        normalized[mapped] += val
    return normalized


def build_svg(lang_totals, top_n=12, width=900, item_size=120, gap=24):
    if not lang_totals:
        return "<p>No language data available.</p>"

    items = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
    total = sum(v for _, v in items)
    if total == 0:
        return "<p>No language bytes recorded.</p>"

    # remove languages that would display as 0.0% (too small to be meaningful)
    visible = []
    for lang, value in items:
        pct = (value / total) * 100
        if round(pct, 1) == 0.0:
            continue
        visible.append((lang, value))
    items = visible
    if not items:
        return "<p>No significant language data to display.</p>"

    # grid layout
    cols = 4
    rows = (len(items) + cols - 1) // cols
    height = rows * (item_size + gap) + 80
    svg_parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">']
    svg_parts.append('<style>text{font-family:Inter,Segoe UI,Roboto,Arial,sans-serif;fill:#c9d1d9}</style>')

    # color palette (fallbacks)
    colors = {
        'JavaScript': '#f1e05a',
        'TypeScript': '#2b7489',
        'Python': '#3572A5',
        'HTML': '#e34c26',
        'CSS': '#563d7c',
        'SCSS': '#c6538c',
        'Jupyter Notebook': '#DA5B0B',
        'PHP': '#4F5D95',
        'Shell': '#89e051',
        'Java': '#b07219',
        'Go': '#00ADD8',
    }

    def fmt_percent(v):
        return f"{v:.1f}%"

    def fmt_bytes(n):
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if n < 1024.0:
                return f"{n:.0f} {unit}"
            n /= 1024.0
        return f"{n:.1f} TB"

    pad_x = 40
    pad_y = 40
    start_x = pad_x
    start_y = pad_y
    for idx, (lang, value) in enumerate(items):
        col = idx % cols
        row = idx // cols
        x = start_x + col * (item_size + gap)
        y = start_y + row * (item_size + gap)

        pct = (value / total) * 100
        color = colors.get(lang, '#238636')

        # circular icon with initials
        radius = 34
        cx = x + radius
        cy = y + radius
        initials = ''.join([p[0] for p in lang.split()][:2]).upper()
        svg_parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{color}" />')
        svg_parts.append(f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" style="font-size:18px;font-weight:700;fill:#07101a">{initials}</text>')

        # language name
        svg_parts.append(f'<text x="{x}" y="{y + radius*2 + 22}" style="font-size:13px;font-weight:600">{lang}</text>')

        # percent badge
        badge_w = 56
        badge_h = 20
        bx = x + item_size - badge_w
        by = y
        svg_parts.append(f'<rect x="{bx}" y="{by}" rx="10" width="{badge_w}" height="{badge_h}" fill="#0b1220" stroke="#30363d"/>')
        svg_parts.append(f'<text x="{bx + badge_w/2}" y="{by + 14}" text-anchor="middle" style="font-size:12px;fill:#c9d1d9">{fmt_percent(pct)}</text>')

        # bytes below
        svg_parts.append(f'<text x="{x}" y="{y + radius*2 + 40}" style="font-size:11px;fill:#8b949e">{fmt_bytes(value)}</text>')

    svg_parts.append(f'<text x="{pad_x}" y="{height - 18}" style="font-size:11px;fill:#8b949e">Generated by scripts/generate_techstack.py — icon grid</text>')
    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def inject_svg(svg):
    with open(README, "r", encoding="utf-8") as f:
        text = f.read()
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start == -1 or end == -1:
        raise RuntimeError("TECHSTACK markers not found in README.md")
    new_text = text[: start + len(START_MARKER)] + "\n" + svg + "\n" + text[end:]
    with open(README, "w", encoding="utf-8") as f:
        f.write(new_text)


def main():
    repos = github_repos(USER)
    totals = aggregate_languages(repos)
    svg = build_svg(totals)
    inject_svg(svg)


if __name__ == "__main__":
    main()
