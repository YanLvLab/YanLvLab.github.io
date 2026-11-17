#!/usr/bin/env python3
"""Daily portfolio sync for @GenRyoma.

X data can only be fetched through the X MCP tools (no API keys live in this repo), so the caller
prepares raw X API v2 responses as JSON files and this script merges them.

  python3 scripts/update.py --print-since-id
  python3 scripts/update.py --input new1.json new2.json
  python3 scripts/update.py --input ... --profile user.json
  python3 scripts/update.py --reclassify
  python3 scripts/update.py --print-since-time
  python3 scripts/test_retention.py          # offline: a stored work missing from input, image URL 404

RETENTION: merge by stable post id. Never delete a stored post, its images, prompt, category, or model
mapping because the id is missing from this fetch, the image URL 404s, the prompt rule fails, or the id
is listed in hidden.json. hidden.json only hides a work from the main halls. Main halls still only GAIN
posts that carry an author prompt. Model halls gain only the data/models.json allow-list (published
photos whose author text names one model). Pending-review ids are stored if seeded, and never assigned.

The first write of a run copies data/posts.json and the mapping files to ../backups/<date>/ (or
backups/ inside the repo, which is gitignored) and does not overwrite that day's first copy.
"""
import argparse, json, os, re, shutil, sys
from datetime import datetime
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


def backup_data():
    """Copy the live data files before the first mutation. Keep the day's first copy."""
    day = datetime.now(xp.SHANGHAI).strftime("%Y-%m-%d")
    candidates = [
        os.path.join(os.path.dirname(xp.ROOT), "backups", day),
        os.path.join(xp.ROOT, "backups", day),
    ]
    errors = []
    for dest in candidates:
        try:
            os.makedirs(dest, exist_ok=True)
            probe = os.path.join(dest, ".write-test")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("")
            os.remove(probe)
        except OSError as e:
            errors.append(f"{dest}: {e}")
            continue
        for name in ("posts.json", "models.json", "image_overrides.json", "category_overrides.json", "hidden.json"):
            src = os.path.join(xp.ROOT, "data", name)
            if not os.path.isfile(src):
                continue
            out = os.path.join(dest, name)
            if not os.path.exists(out):
                shutil.copy2(src, out)
        print("backup", dest, file=sys.stderr)
        return dest
    raise SystemExit("refusing to modify data; backup failed: " + "; ".join(errors))


def _fill_images(post):
    """Download only when local files are missing. A 404 leaves whatever is already stored."""
    if post.get("images") and all(os.path.isfile(os.path.join(xp.ROOT, rel)) for rel in post["images"]):
        return post
    return xp.download(post)


def sync(input_paths, profile_path=None, reclassify=False, apply_site=True):
    """Incremental retention merge. Returns the JSON summary dict. Never removes stored works."""
    backup_data()
    existing, profile = load_existing()
    before = set(existing)
    hidden, force = xp.load_overrides()
    doc = xp.load_models()
    raws = [read_json_loose(f) for f in input_paths]
    incoming, archive, rejected = xp.normalise(raws, hidden, force, doc)
    xp.apply_image_overrides(incoming, raws, download_now=False, quiet_missing=True)
    xp.apply_image_overrides(archive, raws, download_now=False, quiet_missing=True)

    added, refreshed = [], 0
    for pid, p in incoming.items():
        if pid in existing:
            old = existing[pid]
            old["metrics"] = p["metrics"]
            for k in ("text", "thread", "caption", "prompt", "prompt_source", "series"):
                old[k] = p[k]
            if p.get("models"):
                old["models"] = list(p["models"])
            # A later prompt admits a previously archive-only post to the main halls.
            if old.get("main_hall") is False:
                old.pop("main_hall", None)
            _fill_images(old)
            refreshed += 1
        else:
            existing[pid] = xp.download(p)
            added.append(pid)
            print("added", pid, p["created_at"][:16], p.get("series"), len(p["images"]), "img", "prompt:", p.get("prompt_source"))
    for pid, p in archive.items():
        if pid in incoming:
            continue
        if pid in existing:
            existing[pid]["metrics"] = p["metrics"]
            _fill_images(existing[pid])
            refreshed += 1
        else:
            existing[pid] = xp.download(p)
            added.append(pid)
            print("archived", pid, "models", p.get("models") or "pending-review", len(p["images"]), "img")
    # Seen this fetch but not admitted: refresh numbers only. Do not clear prompts or delete files.
    for pid, info in rejected.items():
        if pid in existing and pid not in incoming and pid not in archive and info.get("metrics"):
            existing[pid]["metrics"] = info["metrics"]
    for pid in xp.merge_model_seeds(existing, doc):
        if pid not in added:
            added.append(pid)
    xp.apply_model_assignments(existing, doc)
    if reclassify:
        for pid, p in existing.items():
            if p.get("main_hall") is False:
                continue
            cap, prompt, v, src = xp.evaluate(p.get("text") or "", p.get("thread") or [])
            if v == "yes" or pid in force:
                if v != "yes" and pid in force:
                    cap, prompt, src = p.get("text") or "", prompt or p.get("prompt") or "", src or "manual"
                p["caption"], p["prompt"], p["prompt_source"] = cap, prompt, src
                p["series"] = xp.classify(p.get("caption") or "", p.get("prompt") or "")
                xp.apply_series_override(p)
            # A failed re-check keeps the stored prompt, series, category, and images.
    xp.apply_image_overrides(existing, raws, download_now=True)
    if profile_path:
        profile = build_profile(read_json_loose(profile_path))
    out = xp.save(existing, profile)
    import categorize
    overrides = os.path.join(xp.ROOT, "data", "category_overrides.json")
    _, cat_stats, _ = categorize.attach(path=xp.DATA, overrides_path=overrides)
    out["category_order"] = cat_stats["order"]
    # Image files are not deleted. A missing fetch or a 404 is not a cleanup signal.
    review_path = os.path.join(xp.ROOT, "review", "excluded.json")
    os.makedirs(os.path.dirname(review_path), exist_ok=True)
    old_review = {}
    if os.path.exists(review_path):
        old_review = {r["id"]: r for r in json.load(open(review_path, encoding="utf-8"))}
    pending = set(doc["pending_review"])
    for pid in existing:
        if pid in pending:
            continue
        old_review.pop(pid, None)
    for pid, info in rejected.items():
        if pid in existing and pid not in pending:
            continue
        old_review[pid] = {k: v for k, v in info.items() if k != "metrics"}
    for pid in pending:
        if pid in old_review:
            old_review[pid]["verdict"] = "review"
            continue
        seed = next((s for s in doc["seeds"] if str(s.get("id")) == pid), {})
        old_review[pid] = {
            "id": pid,
            "verdict": "review",
            "text": (seed.get("text") or "")[:200],
            "url": seed.get("url") or f"https://x.com/GenRyoma/status/{pid}",
            "note": seed.get("note") or "pending review; do not assign a model",
        }
    json.dump(sorted(old_review.values(), key=lambda r: int(r["id"]), reverse=True),
              open(review_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if apply_site:
        import apply_config
        apply_config.apply()
    model_counts = {}
    for name in xp.MODEL_IDS:
        ids = [i for i, names in doc["assignments"].items() if name in names and i not in pending and i in existing]
        model_counts[name] = {
            "posts": len(ids),
            "images": sum(len(existing[i].get("images") or []) for i in ids),
        }
    main_ids = [i for i, p in existing.items() if p.get("main_hall") is not False]
    summary = {
        "added": len(added),
        "kept": len(before & set(existing)),
        "removed": 0,
        "images_deleted": 0,
        "metrics_refreshed": refreshed,
        "posts": len(existing),
        "main_hall": len(main_ids),
        "categories": cat_stats["counts"],
        "model_halls": model_counts,
        "images": sum(len(p.get("images") or []) for p in existing.values()),
        "uncertain": sum(1 for r in old_review.values() if r.get("verdict") == "unsure"),
        "pending_review": sorted(pending),
        "last_updated": out["last_updated"],
    }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", nargs="*", default=[], help="raw X API JSON files: image posts AND self-reply searches")
    ap.add_argument("--profile")
    ap.add_argument("--rebuild", action="store_true", help="kept for compatibility; stored posts are still retained")
    ap.add_argument("--reclassify", action="store_true", help="re-apply prompt/series on stored main-hall posts; never deletes")
    ap.add_argument("--print-since-id", action="store_true")
    ap.add_argument("--print-since-time", action="store_true", help="UTC start_time to fetch from (newest main-hall post - 48h)")
    ap.add_argument("--root", help="data root (tests only)")
    a = ap.parse_args()
    if a.root:
        xp.configure(a.root)
    if a.rebuild:
        print("rebuild keeps every stored post; this run will not delete records or images", file=sys.stderr)

    existing, _profile = load_existing()
    if a.print_since_id or a.print_since_time:
        main_posts = [p for p in existing.values() if p.get("main_hall") is not False]
        if not main_posts:
            print(""); return
        newest = max(main_posts, key=lambda p: int(p["id"]))
        if a.print_since_id:
            print(newest["id"])
        else:
            from datetime import timedelta, timezone
            t = datetime.fromisoformat(newest["created_at"]).astimezone(timezone.utc) - timedelta(hours=48)
            print(t.strftime("%Y-%m-%dT%H:%M:%SZ"))
        return
    summary = sync(a.input, profile_path=a.profile, reclassify=a.reclassify, apply_site=True)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
