#!/usr/bin/env python3
"""Retention check for the catalogue after the 2026-11-23 daily increment.

Posts already on c9777f1 keep their images, prompts, categories, and membership.
Gallery labels on those posts stay cleared. Author-text labels are only the
original six pictures plus the nine pictures added on 2026-11-23.
"""
import json, os, subprocess, sys
from collections import Counter

BASE = "c9777f148a8742e1d510cc539f63f614596245e5"
KEEP_SAME = ("images", "thumbs", "prompt", "caption", "text", "thread", "category", "series", "in_feed", "prompt_source")
LABELED = {
    "2123056954772005040": ["韩书允"],
    "2123443682967748917": ["林知夏"],
    "2123266263506178057": ["姜宥娜", "姜宥娜", "姜宥娜", "姜宥娜"],
    "2124692595398136229": ["韩书允", "韩书允", "韩书允", "韩书允"],
    "2124763163321393279": ["林知夏"],
    "2124701323652403611": ["姜宥娜", "姜宥娜", "姜宥娜", "姜宥娜"],
}


def git_json(path):
    raw = subprocess.check_output(["git", "show", f"{BASE}:{path}"])
    return json.loads(raw.decode())


def main():
    old = git_json("data/posts.json")
    new = json.load(open("data/posts.json", encoding="utf-8"))
    old_posts = {p["id"]: p for p in old["posts"]}
    new_posts = {p["id"]: p for p in new["posts"]}
    assert set(old_posts) <= set(new_posts)
    for pid, prev in old_posts.items():
        cur = new_posts[pid]
        for key in KEEP_SAME:
            assert prev.get(key) == cur.get(key), (pid, key)
        assert cur.get("image_models") == [None] * len(cur.get("images") or [])
        assert cur.get("models") == []
        for rel in (cur.get("images") or []) + (cur.get("thumbs") or []):
            assert os.path.isfile(rel) and os.path.getsize(rel) > 800, rel
    counts = Counter()
    for pid, labels in LABELED.items():
        assert new_posts[pid]["image_models"] == labels
        assert new_posts[pid]["in_feed"] is False
        assert not new_posts[pid].get("prompt")
        for lab in labels:
            counts[lab] += 1
    for p in new["posts"]:
        if p["id"] in LABELED or p["id"] in old_posts:
            continue
        assert p.get("image_models") == [None] * len(p.get("images") or [])
    assert counts["韩书允"] == 5 and counts["林知夏"] == 2 and counts["姜宥娜"] == 8
    feed = [p for p in new["posts"] if p.get("in_feed") is not False and not p.get("suppressed")]
    assert len(old["posts"]) == 152
    assert len(new["posts"]) == 192
    assert len(feed) == 184
    assert sum(len(p["images"]) for p in new["posts"]) == 220
    thread = new_posts["2124719959389691906"]
    assert thread["in_feed"] is True and thread["prompt_source"] == "thread" and "连体衣" in thread["prompt"]
    assert "2124718331466862876" not in new_posts
    mirror = new_posts["2124868239339753937"]
    assert mirror["in_feed"] is True and mirror["category"] == "内衣私房" and mirror["category"] not in ("其他", "偏殿")
    assert new["profile"]["followers"] == 5645
    assert new["profile"]["bio"] == old["profile"]["bio"]
    assert new["profile"]["name"] == old["profile"]["name"]
    blob = open("data/posts.json", encoding="utf-8").read()
    for bad in ("/workspace", "/home/", "sand-data", "x-fashion", "dataset_raw_pages"):
        assert bad not in blob
    print(json.dumps({"archive": 192, "feed": 184, "images": 220, "韩书允": 5, "林知夏": 2, "姜宥娜": 8}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL", e, file=sys.stderr)
        sys.exit(1)
