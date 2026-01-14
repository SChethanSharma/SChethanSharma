#!/usr/bin/env python3
"""Generate repository cards and inject into README.md between markers.

Usage: set environment variable GITHUB_TOKEN (optional for public repos but recommended)
"""
import os
import requests
from datetime import datetime

USER = "SChethanSharma"
README = "README.md"
START_MARKER = "<!-- REPO-CARDS:START -->"
END_MARKER = "<!-- REPO-CARDS:END -->"


def github_repos(user):
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"https://api.github.com/users/{user}/repos?per_page=200"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def build_card(repo):
    name = repo["name"]
    url = repo["html_url"]
    desc = repo.get("description") or ""
    lang = repo.get("language") or ""
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    updated = repo.get("updated_at")
    if updated:
        updated = datetime.strptime(updated, "%Y-%m-%dT%H:%M:%SZ").date().isoformat()

    # Shields for stars and forks
    stars_badge = f"https://img.shields.io/github/stars/{USER}/{name}?style=social"
    forks_badge = f"https://img.shields.io/github/forks/{USER}/{name}?style=social"
    lang_badge = f"https://img.shields.io/badge/language-{lang.replace(' ', '%20')}-gray" if lang else ""

    card = f"""
<div style=\"width:320px;margin:10px;padding:16px;border-radius:12px;box-shadow:0 4px 10px rgba(2,6,23,0.2);background:#0d1117;color:#c9d1d9;display:inline-block;vertical-align:top;\">
  <a href=\"{url}\" style=\"text-decoration:none;color:inherit;\"><h3 style=\"margin:0 0 8px 0;\">{name}</h3></a>
  <p style=\"margin:0 0 8px 0;font-size:13px;color:#9ea7b3;min-height:40px;\">{desc}</p>
  <div style=\"margin-top:8px;display:flex;gap:8px;align-items:center;\">
    {f'<img src=\"{lang_badge}\" alt=\"lang\"/>' if lang_badge else ''}
    <img src=\"{stars_badge}\" alt=\"stars\" />
    <img src=\"{forks_badge}\" alt=\"forks\" />
    <span style=\"margin-left:auto;font-size:12px;color:#8b949e;\">Updated {updated}</span>
  </div>
</div>
"""
    return card


def generate_markdown(repos):
    # Filter out forks, archived and empty repos, sort by stars desc then updated
    items = [r for r in repos if not r.get("fork") and not r.get("archived")]
    items.sort(key=lambda r: (r.get("stargazers_count", 0), r.get("updated_at") or ""), reverse=True)
    cards = [build_card(r) for r in items[:24]]

    gallery = "\n".join(cards)
    markdown = f"\n<div style=\"display:flex;flex-wrap:wrap;justify-content:flex-start;\">\n{gallery}\n</div>\n"
    return markdown


def inject_into_readme(content):
    with open(README, "r", encoding="utf-8") as f:
        text = f.read()
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start == -1 or end == -1:
        raise RuntimeError("Markers not found in README.md")
    new_text = text[: start + len(START_MARKER)] + "\n" + content + text[end:]
    with open(README, "w", encoding="utf-8") as f:
        f.write(new_text)


def main():
    repos = github_repos(USER)
    md = generate_markdown(repos)
    inject_into_readme(md)


if __name__ == "__main__":
    main()
