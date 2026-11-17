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

RULE: the theme feed keeps image posts that carry the author's own generation prompt (post text or the
author's own replies). Author images that name 韩书允 / 林知夏 / 姜宥娜 without a prompt are archived for
the picture-only model galleries. Already archived ids, local image files, prompts, and model labels are
never deleted because a later fetch omits them or the source post is gone. hidden.json suppresses display
only. Uncertain cases go to review/excluded.json.

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


MANIFEST = os.path.join(xp.ROOT, "data", "archive_manifest.json")
SNAPSHOT = os.path.join(xp.ROOT, "data", "snapshots", "posts-ef9ccd3.json")


def snapshot_posts():
    """One copy of the pre-migration catalogue. Later syncs do not overwrite it."""
    if os.path.exists(xp.DATA) and not os.path.exists(SNAPSHOT):
        os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
        import shutil
        shutil.copyfile(xp.DATA, SNAPSHOT)


def remember_files(posts, manifest_path=None):
    path = manifest_path or MANIFEST
    kept = set()
    if os.path.exists(path):
        kept.update(json.load(open(path, encoding="utf-8")))
    for p in posts.values():
        for rel in (p.get("images") or []) + (p.get("thumbs") or []):
            kept.add(rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(sorted(kept), open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return kept


def cleanup_images(posts, img_dir=None, thumb_dir=None, manifest_path=None):
    """Delete only files that were never archived. Manifest entries stay on disk."""
    img_dir = img_dir or xp.IMG_DIR
    thumb_dir = thumb_dir or xp.THUMB_DIR
    keep_rel = remember_files(posts, manifest_path)
    keep = {os.path.basename(x) for x in keep_rel} | {"avatar.jpg", "banner.jpg"}
    removed = 0
    for d in (img_dir, thumb_dir):
        if not os.path.isdir(d):
            continue
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

    snapshot_posts()
    existing, profile = load_existing()
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
    incoming, rejected, model_only = xp.normalise(raws, hidden, force)
    xp.apply_image_overrides(incoming, raws, download_now=False)
    fresh = dict(model_only)
    fresh.update(incoming)  # a prompted post wins over a picture-only copy of the same id
    for pid, p in list(fresh.items()):
        if (pid not in existing or not existing[pid].get("images")) and not p.get("images"):
            fresh[pid] = xp.download(p)
            print("added", pid, p["created_at"][:16], p.get("series"), "feed:", p.get("in_feed"))
    existing, added_ids, refreshed = xp.merge_archive(existing, fresh)
    dropped = []  # archive ids are not pruned; kept in the summary for older logs
    for pid in hidden:
        if pid in existing:
            existing[pid]["suppressed"] = True  # display off; files and the record stay
    xp.apply_image_overrides(existing, raws, download_now=True)
    if a.reclassify:
        for pid, p in list(existing.items()):
            cap, prompt, v, src = xp.evaluate(p.get("text") or "", p.get("thread", []))
            if v == "yes" or pid in force:
                if v == "yes":
                    p["caption"], p["prompt"], p["prompt_source"] = cap, prompt, src
                elif pid in force and not p.get("prompt"):
                    p["prompt"] = "\n\n".join([p.get("text") or ""] + list(p.get("thread") or []))
                    p["prompt_source"] = p.get("prompt_source") or "manual"
                if p.get("prompt"):
                    p["in_feed"] = True
                    p["series"] = xp.classify(p.get("caption") or "", p.get("prompt") or "")
            p["models"] = xp.model_names(p)
            if pid in hidden:
                p["suppressed"] = True
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
    print(json.dumps({"added": len(added_ids), "dropped": len(dropped), "metrics_refreshed": refreshed,
                      "posts": len(out["posts"]), "categories": cat_stats["counts"],
                      "images": sum(len(p["images"]) for p in out["posts"]),
                      "uncertain": sum(1 for r in old.values() if r["verdict"] == "unsure"),
                      "images_deleted": removed, "last_updated": out["last_updated"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
