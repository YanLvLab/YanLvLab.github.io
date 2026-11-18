#!/usr/bin/env python3
"""Focused check: v2 media labels replace the previous map and nothing else moves.

Compares the working tree with main 8201d8c. Theme, category, prompt, ids, and
image paths must match. Model tags may change. Image files must be untouched.
"""
import json, subprocess, sys
from collections import Counter

BASE = "8201d8c16c7565bba67866cd07787a446fa4041e"
KEEP = ("image_models", "models")


def git_json(path):
    raw = subprocess.check_output(["git", "show", f"{BASE}:{path}"])
    return json.loads(raw.decode())


def main():
    old = git_json("data/posts.json")
    new = json.load(open("data/posts.json", encoding="utf-8"))
    media = json.load(open("data/model_media.json", encoding="utf-8"))
    assert media.get("replace") is True
    rows = media["media"]
    assert len(rows) == 170
    assert len({(r["post_id"], r["index"]) for r in rows}) == 170
    blob = json.dumps(media, ensure_ascii=False)
    for bad in ("/workspace", "/home/", "sand-data", "x-fashion", "reference_files", ".png", "ChatGPT 图像"):
        assert bad not in blob, bad

    old_posts = {p["id"]: p for p in old["posts"]}
    new_posts = {p["id"]: p for p in new["posts"]}
    assert list(old_posts) == list(new_posts)
    changed = Counter()
    for pid, prev in old_posts.items():
        cur = new_posts[pid]
        assert set(prev) == set(cur)
        for key in prev:
            if prev[key] != cur[key]:
                assert key in KEEP, (pid, key)
                changed[key] += 1
        assert prev.get("images") == cur.get("images")
        assert prev.get("prompt") == cur.get("prompt")
        assert prev.get("category") == cur.get("category")
        assert prev.get("in_feed") == cur.get("in_feed")
        assert prev.get("series") == cur.get("series")
        assert (prev.get("image_models") is None) or len(prev.get("image_models") or []) == len(cur.get("image_models") or [])
        assert len(cur.get("image_models") or []) == len(cur.get("images") or [])

    by_key = {(str(r["post_id"]), int(r["index"])): r for r in rows}
    counts = Counter()
    pending = 0
    for p in new["posts"]:
        for n, src in enumerate(p.get("images") or [], 1):
            row = by_key[(p["id"], n)]
            assert row["src"] == src
            label = (p.get("image_models") or [None])[n - 1]
            if row["status"] == "pending":
                assert label is None
                assert not row.get("models")
                pending += 1
            else:
                assert row["status"] == "confirmed"
                zh = row["models"][0]["zh"]
                assert label == zh
                counts[zh] += 1
    assert counts["韩书允"] == 11
    assert counts["林知夏"] == 82
    assert counts["姜宥娜"] == 0
    assert pending == 77
    feed = [p for p in new["posts"] if p.get("in_feed") is not False and not p.get("suppressed")]
    assert len(new["posts"]) == 152
    assert len(feed) == 150
    names = subprocess.check_output(["git", "diff", "--name-only", BASE], text=True).split()
    assert not any(n.startswith("images/") for n in names), names
    print(json.dumps({
        "archive": 152, "feed": 150, "images": 170,
        "韩书允": 11, "林知夏": 82, "姜宥娜": 0, "pending": 77,
        "posts_with_model_field_changes": changed["models"],
        "files": names,
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL", e, file=sys.stderr)
        sys.exit(1)
