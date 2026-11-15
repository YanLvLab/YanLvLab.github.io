#!/usr/bin/env python3
"""Daily portfolio sync for @GenRyoma.

X data can only be fetched through the X MCP tools (no API keys live in this repo), so the caller
(Grok Bot routine) prepares raw X API v2 responses as JSON files and this script merges them.

  python3 scripts/update.py --print-since-id            # newest post id already on the site
  python3 scripts/update.py --input new1.json new2.json # merge posts newer than that id, download images
  python3 scripts/update.py --input ... --profile user.json   # also refresh avatar/name/bio
  python3 scripts/update.py --rebuild --input raw/*.json      # full rebuild from scratch
  python3 scripts/update.py --reclassify                      # re-run prompt rule / series / overrides only
  python3 scripts/update.py --print-since-time                # UTC start_time for the daily search (newest - 48h)

RULE: only image posts that carry a generation prompt (in the post text, or in the author's own reply
thread under it) are kept. Posts without a prompt are dropped and their image files deleted. Uncertain
cases go to review/excluded.json (verdict "unsure"); force-include by id via data/hidden.json "include_ids".

Input files: the JSON body returned by get_users_posts or search_posts_all (keys data/includes/meta),
requested with expansions=attachments.media_keys,referenced_posts and
media.fields=media_key,type,url,width,height; post.fields=created_at,public_metrics,attachments,
entities,referenced_tweets,text,note_post. Wrapper text around the JSON is tolerated.
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xportfolio as xp


def read_json_loose(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r'\{\s*"(data|meta|includes)"', s)
    if not m:
        raise SystemExit(f"no X API JSON found in {path}")
    obj, _ = json.JSONDecoder().raw_decode(s[m.start():])
    return obj


def load_existing():
    if not os.path.exists(xp.DATA):
        return {}, {}
    d = json.load(open(xp.DATA, encoding="utf-8"))
    return {p["id"]: p for p in d["posts"]}, d.get("profile", {})


def build_profile(raw):
    u = raw.get("data", raw)
    prof = {"name": u.get("name"), "username": u.get("username"), "bio": u.get("description", ""),
            "url": f"https://x.com/{u.get('username')}",
            "followers": (u.get("public_metrics") or {}).get("followers_count")}
    av = (u.get("profile_image_url") or "").replace("_normal", "_400x400")
    if av and xp._get(av, os.path.join(xp.IMG_DIR, "avatar.jpg")):
        prof["avatar"] = "images/avatar.jpg"
    bn = u.get("profile_banner_url")
    if bn and xp._get(bn + "/1500x500", os.path.join(xp.IMG_DIR, "banner.jpg")):
        prof["banner"] = "images/banner.jpg"
    return prof


REVIEW = os.path.join(xp.ROOT, "review", "excluded.json")


def cleanup_images(posts):
    keep = {os.path.basename(x) for p in posts.values() for x in p["images"] + p["thumbs"]} | {"avatar.jpg", "banner.jpg"}
    removed = 0
    for d in (xp.IMG_DIR, xp.THUMB_DIR):
        for f in os.listdir(d):
            fp = os.path.join(d, f)
            if os.path.isfile(fp) and f not in keep:
                os.remove(fp); removed += 1
    return removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", nargs="*", default=[], help="raw X API JSON files: image posts AND self-reply searches")
    ap.add_argument("--profile")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--reclassify", action="store_true", help="re-apply prompt rule / series / overrides to stored posts")
    ap.add_argument("--print-since-id", action="store_true")
    ap.add_argument("--print-since-time", action="store_true", help="UTC start_time to fetch from (newest post - 48h)")
    a = ap.parse_args()

    existing, profile = ({}, {}) if a.rebuild else load_existing()
    if a.print_since_id or a.print_since_time:
        if not existing:
            print(""); return
        newest = max(existing.values(), key=lambda p: int(p["id"]))
        if a.print_since_id:
            print(newest["id"])
        else:
            from datetime import datetime, timedelta, timezone
            t = datetime.fromisoformat(newest["created_at"]).astimezone(timezone.utc) - timedelta(hours=48)
            print(t.strftime("%Y-%m-%dT%H:%M:%SZ"))
        return
    hidden, force = xp.load_overrides()
    raws = [read_json_loose(f) for f in a.input]
    incoming, rejected = xp.normalise(raws, hidden, force)
    xp.apply_image_overrides(incoming, raws, download_now=False)

    added, refreshed, dropped = [], 0, []
    for pid, p in incoming.items():
        if pid in existing:  # keep files, refresh live numbers + thread/prompt
            for k in ("metrics", "thread", "caption", "prompt", "prompt_source", "series"):
                existing[pid][k] = p[k]
            refreshed += 1
        else:
            existing[pid] = xp.download(p); added.append(pid)
            print("added", pid, p["created_at"][:16], p["series"], len(p["images"]), "img", "prompt:", p["prompt_source"])
    xp.apply_image_overrides(existing, raws, download_now=True)
    for pid in list(existing):
        if pid in rejected:  # previously shown, now fails the rule / hidden
            dropped.append(pid); existing.pop(pid)
    if a.reclassify:
        for pid, p in list(existing.items()):
            cap, prompt, v, src = xp.evaluate(p["text"], p.get("thread", []))
            if pid in hidden or (v != "yes" and pid not in force):
                dropped.append(pid); rejected[pid] = {"id": pid, "verdict": "hidden" if pid in hidden else v,
                                                      "created_at": p["created_at"], "text": p["text"][:200], "url": p["url"]}
                existing.pop(pid); continue
            if v == "yes":
                p["caption"], p["prompt"], p["prompt_source"] = cap, prompt, src
            p["series"] = xp.classify(p["caption"], p["prompt"])
    if a.profile:
        profile = build_profile(read_json_loose(a.profile))
    out = xp.save(existing, profile)
    import categorize
    _, cat_stats, _ = categorize.attach()
    out["category_order"] = cat_stats["order"]
    removed = cleanup_images(existing)
    # audit list of rejected / uncertain candidates (not published: review/ is git-ignored)
    os.makedirs(os.path.dirname(REVIEW), exist_ok=True)
    old = {} if a.rebuild or not os.path.exists(REVIEW) else {r["id"]: r for r in json.load(open(REVIEW, encoding="utf-8"))}
    for pid in existing:
        old.pop(pid, None)
    old.update(rejected)
    json.dump(sorted(old.values(), key=lambda r: int(r["id"]), reverse=True), open(REVIEW, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # og.jpg is a fixed text card (scripts/make_og.py) and is never rebuilt from post images.
    import apply_config
    apply_config.apply()
    print(json.dumps({"added": len(added), "dropped": len(dropped), "metrics_refreshed": refreshed,
                      "posts": len(out["posts"]), "categories": cat_stats["counts"],
                      "images": sum(len(p["images"]) for p in out["posts"]),
                      "uncertain": sum(1 for r in old.values() if r["verdict"] == "unsure"),
                      "images_deleted": removed, "last_updated": out["last_updated"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
