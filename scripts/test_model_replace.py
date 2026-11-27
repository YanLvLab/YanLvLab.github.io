#!/usr/bin/env python3
"""Retention check for posts already on the site before this batch.

Posts on b873f7d keep their images, prompts, categories, and membership.
Gallery labels already on that commit stay as they were. Later manual labels
are not cleared, and an empty replace of model_media.json is not applied.
"""
import json, os, subprocess, sys
from collections import Counter

BASE = "c9777f148a8742e1d510cc539f63f614596245e5"
PRE = "b873f7de179db72b2afbcee288ba867922872870"
KEEP_SAME = ("images", "thumbs", "prompt", "caption", "text", "thread", "category", "series", "in_feed", "prompt_source")
LABELED = {
    "2123056954772005040": ["韩书允"],
    "2123443682967748917": ["林知夏"],
    "2123266263506178057": ["姜宥娜", "姜宥娜", "姜宥娜", "姜宥娜"],
    "2124692595398136229": ["韩书允", "韩书允", "韩书允", "韩书允"],
    "2124763163321393279": ["林知夏"],
    "2124701323652403611": ["姜宥娜", "姜宥娜", "姜宥娜", "姜宥娜"],
}


def git_json(path, rev=BASE):
    raw = subprocess.check_output(["git", "show", f"{rev}:{path}"])
    return json.loads(raw.decode())


def main():
    old = git_json("data/posts.json")
    pre = git_json("data/posts.json", PRE)
    new = json.load(open("data/posts.json", encoding="utf-8"))
    old_posts = {p["id"]: p for p in old["posts"]}
    pre_posts = {p["id"]: p for p in pre["posts"]}
    new_posts = {p["id"]: p for p in new["posts"]}
    assert set(old_posts) <= set(pre_posts) <= set(new_posts)
    for pid, prev in pre_posts.items():
        cur = new_posts[pid]
        for key in KEEP_SAME:
            assert prev.get(key) == cur.get(key), (pid, key)
        if pid not in LABELED:
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
    you = "姜宥娜"
    assert [ord(c) for c in you] == [0x59DC, 0x5BA5, 0x5A1C]
    assert counts["韩书允"] == 5 and counts["林知夏"] == 2 and counts[you] == 8
    feed = [p for p in new["posts"] if p.get("in_feed") is not False and not p.get("suppressed")]
    assert len(old["posts"]) == 152
    assert len(pre["posts"]) == 192
    assert len(new["posts"]) == 377
    assert len(feed) == 294
    assert sum(len(p["images"]) for p in new["posts"]) == 504
    echoes = [p for p in new["posts"] if p.get("category") == "灵感回响"]
    assert len(echoes) == 62 and sum(len(p["images"]) for p in echoes) == 79
    assert all(p.get("in_feed") is True and not p.get("prompt") for p in echoes)
    assert "2121985063353237859" not in new_posts
    violet = new_posts["2121647597672669387"]
    assert violet["media"][0]["src"].endswith("HXLOH6CaUAAhqJE.jpg")
    assert violet["prompt"] and violet["in_feed"] is True
    thread = new_posts["2124719959389691906"]
    assert thread["in_feed"] is True and thread["prompt_source"] == "thread" and "连体衣" in thread["prompt"]
    assert "2124718331466862876" not in new_posts
    assert "2125573275057344808" not in new_posts
    mirror = new_posts["2124868239339753937"]
    assert mirror["in_feed"] is True and mirror["category"] == "内衣私房" and mirror["category"] not in ("其他", "偏殿")
    gallery = Counter(lab for p in new["posts"] for lab in (p.get("image_models") or []) if lab)
    assert gallery["韩书允"] == 119 and gallery["林知夏"] == 27 and gallery["姜宥娜"] == 19
    assert new["profile"]["followers"] == 5710
    assert new["profile"]["bio"] == (
        "Law · History · Philosophy · Faith · AI · Catholic✝️\n"
        "AIart: https://t.co/YGd1b9oRUk\n"
        "ASMR: https://t.co/KcaNBKvhw0"
    )
    assert new["profile"]["name"] == pre["profile"]["name"]
    assert "灵感回响" in new["category_order"]
    media = json.load(open("data/model_media.json", encoding="utf-8"))
    assert media.get("replace") is False and media.get("media")
    assert not (media.get("replace") and media.get("media") == [])
    blob = open("data/posts.json", encoding="utf-8").read()
    for bad in ("/workspace", "/home/", "sand-data", "x-fashion", "dataset_raw_pages"):
        assert bad not in blob
    print(json.dumps({"archive": len(new["posts"]), "feed": len(feed), "images": sum(len(p["images"]) for p in new["posts"]), "echoes": len(echoes), "galleries": dict(gallery)}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL", e, file=sys.stderr)
        sys.exit(1)
