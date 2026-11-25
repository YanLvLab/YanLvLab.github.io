#!/usr/bin/env python3
"""Apply site.config.json switches to the static files.

noindex      -> <meta name="robots" content="noindex, nofollow"> in index.html + robots.txt "Disallow: /"
adult_notice -> read at runtime by assets/app.js (NSFW entry gate); nothing to write here.
Both default to false."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START, END = "<!-- robots:start -->", "<!-- robots:end -->"


def apply():
    cfg = json.load(open(os.path.join(ROOT, "site.config.json"), encoding="utf-8"))
    idx = os.path.join(ROOT, "index.html")
    html = open(idx, encoding="utf-8").read()
    tag = '<meta name="robots" content="noindex, nofollow">' if cfg.get("noindex") else ""
    html = re.sub(re.escape(START) + ".*?" + re.escape(END), START + tag + END, html, flags=re.S)
    open(idx, "w", encoding="utf-8").write(html)
    robots = "User-agent: *\n" + ("Disallow: /\n" if cfg.get("noindex") else "Allow: /\n")
    open(os.path.join(ROOT, "robots.txt"), "w").write(robots)
    return cfg


if __name__ == "__main__":
    print(apply())
