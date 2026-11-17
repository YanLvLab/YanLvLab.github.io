#!/usr/bin/env python3
"""Offline retention check. Does not delete or edit any live X post or the site's posts.json.

A stored work is absent from the current input and its image URL returns 404.
A second stored work is present in the input, fails the prompt rule, and its image URL
also returns 404. After sync, both records, their prompts, categories, model mapping,
and the local image/thumb bytes are still there. An unreferenced image file is kept too.

    python3 scripts/test_retention.py
"""
import hashlib, json, os, shutil, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xportfolio as xp
import update

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MISSING = "1000000000000000001"  # not in this fetch; image URL 404s
REJECTED = "1000000000000000002"  # in this fetch, no prompt; image URL 404s
PROMPT = "竖版 9:16 摄影 镜头 光线 服装 场景 成年东亚女性 抓拍 超写实写真"


def _fail(msg):
    print("FAIL", msg, file=sys.stderr)
    return 1


def check_published_contract():
    """The live allow-list and the three bilingual titles. Not a network call."""
    models = json.load(open(os.path.join(REPO, "data", "models.json"), encoding="utf-8"))
    labels = models["labels"]
    for zh, full in (
        ("韩书允", "韩书允 Han Seoyun"),
        ("林知夏", "林知夏 Lin Zhixia"),
        ("姜宥娜", "姜宥娜 Kang Yuna"),
    ):
        if labels.get(zh) != full:
            return _fail(f"label {zh} is {labels.get(zh)!r}")
    pending = "2117870734303531012"
    if pending not in [str(x) for x in models["pending_review"]]:
        return _fail("group post missing from pending_review")
    if pending in models["assignments"]:
        return _fail("pending-review post was assigned to a model")
    if models["assignments"].get("2117461257389498407") != ["林知夏"]:
        return _fail("Lin Zhixia allow-list")
    if models["assignments"].get("2113584396582412739") != ["韩书允"]:
        return _fail("Han Seoyun allow-list 2113584396582412739")
    if models["assignments"].get("2108388958526964003") != ["韩书允"]:
        return _fail("Han Seoyun allow-list 2108388958526964003")
    if any("姜宥娜" in names for names in models["assignments"].values()):
        return _fail("Kang Yuna must stay empty")
    js = open(os.path.join(REPO, "assets", "app.js"), encoding="utf-8").read()
    html = open(os.path.join(REPO, "index.html"), encoding="utf-8").read()
    for full in ("韩书允 Han Seoyun", "林知夏 Lin Zhixia", "姜宥娜 Kang Yuna"):
        if full not in js:
            return _fail("app.js missing " + full)
    if "images-only" not in js:
        return _fail("model viewer is not image-only")
    for name in ("韩书允", "林知夏", "姜宥娜"):
        if name not in js.split("NEVER_CAT")[1][:240]:
            return _fail("NEVER_CAT no longer excludes " + name)
    for needle in ("取消排序 · 回到大殿", "返回首页", 'id="modelNav"', 'id="modelHalls"', "HARA"):
        if needle not in html:
            return _fail("index.html missing " + needle)
    readme = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
    if "删除" in readme and "不收的帖子图片会从" in readme:
        return _fail("README still says dropped images are deleted")
    print("allow-list and bilingual titles ok")
    return 0


def _jpeg(rgb):
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), rgb).save(buf, "JPEG", quality=90)
    return buf.getvalue()


def _webp(rgb):
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), rgb).save(buf, "WEBP", quality=80)
    return buf.getvalue()


def _write(path, blob):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


class _Gone(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"missing")

    def log_message(self, fmt, *args):
        return


def run_fixture():
    """Copy of a stored work, not the live posts.json. Image URL is a local 404."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Gone)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    missing_url = f"http://127.0.0.1:{port}/missing.jpg"
    root = tempfile.mkdtemp(prefix="retention-")
    try:
        os.makedirs(os.path.join(root, "data"))
        blobs = {}
        posts = []
        for pid, rgb, models in (
            (MISSING, (12, 24, 36), ["林知夏"]),
            (REJECTED, (48, 12, 12), ["韩书允"]),
        ):
            img_rel = f"images/{pid}_1.jpg"
            thumb_rel = f"images/thumb/{pid}_1.webp"
            img = _jpeg(rgb)
            thumb = _webp(rgb)
            _write(os.path.join(root, img_rel), img)
            _write(os.path.join(root, thumb_rel), thumb)
            blobs[img_rel] = _sha(os.path.join(root, img_rel))
            blobs[thumb_rel] = _sha(os.path.join(root, thumb_rel))
            posts.append({
                "id": pid,
                "created_at": "2026-01-01T00:00:00+08:00",
                "text": "保留测试\n" + PROMPT,
                "thread": [],
                "caption": "保留测试",
                "prompt": PROMPT,
                "prompt_source": "post",
                "url": f"https://x.com/GenRyoma/status/{pid}",
                "quote": False,
                "media": [{"src": missing_url, "w": 8, "h": 8}],
                "images": [img_rel],
                "thumbs": [thumb_rel],
                "metrics": {"impressions": 3, "likes": 2, "bookmarks": 1, "reposts": 0, "replies": 0},
                "series": ["丝袜"],
                "category": "丝袜",
                "models": models,
                "main_hall": True,
            })
        orphan = os.path.join(root, "images", "orphan_keep.jpg")
        _write(orphan, _jpeg((1, 2, 3)))
        orphan_sha = _sha(orphan)
        doc = {
            "profile": {"name": "Fixture", "username": "GenRyoma", "bio": "", "followers": 1},
            "last_updated": "2026-01-01T00:00:00+08:00",
            "series_order": ["丝袜"],
            "category_order": ["丝袜"],
            "posts": posts,
        }
        json.dump(doc, open(os.path.join(root, "data", "posts.json"), "w", encoding="utf-8"), ensure_ascii=False)
        models = {
            "order": ["韩书允", "林知夏", "姜宥娜"],
            "labels": {
                "韩书允": "韩书允 Han Seoyun",
                "林知夏": "林知夏 Lin Zhixia",
                "姜宥娜": "姜宥娜 Kang Yuna",
            },
            "assignments": {MISSING: ["林知夏"], REJECTED: ["韩书允"]},
            "pending_review": [],
            "seeds": [],
        }
        models_path = os.path.join(root, "data", "models.json")
        json.dump(models, open(models_path, "w", encoding="utf-8"), ensure_ascii=False)
        models_sha = _sha(models_path)
        json.dump({"ids": [MISSING], "include_ids": []}, open(os.path.join(root, "data", "hidden.json"), "w", encoding="utf-8"))
        json.dump({
            MISSING: {"category": "丝袜", "note": "fixture"},
            REJECTED: {"category": "丝袜", "note": "fixture"},
        }, open(os.path.join(root, "data", "category_overrides.json"), "w", encoding="utf-8"))
        incoming = {
            "data": [{
                "id": REJECTED,
                "created_at": "2026-01-02T00:00:00.000Z",
                "text": "just a caption",
                "author_id": "1802687195163299840",
                "public_metrics": {"impression_count": 9, "like_count": 1, "bookmark_count": 0, "retweet_count": 0, "reply_count": 0},
                "attachments": {"media_keys": ["3_missing"]},
            }],
            "includes": {"media": [{
                "media_key": "3_missing", "type": "photo", "url": missing_url, "width": 8, "height": 8,
            }]},
            "meta": {},
        }
        incoming_path = os.path.join(root, "incoming.json")
        json.dump(incoming, open(incoming_path, "w", encoding="utf-8"))

        xp.configure(root)
        xp.DOWNLOAD_TRIES = 1
        xp.DOWNLOAD_BACKOFF = 0
        summary = update.sync([incoming_path], apply_site=False)
        if summary.get("removed") != 0 or summary.get("images_deleted") != 0:
            return _fail(f"sync reported a deletion: {summary}")
        got = json.load(open(os.path.join(root, "data", "posts.json"), encoding="utf-8"))
        by_id = {p["id"]: p for p in got["posts"]}
        if MISSING not in by_id or REJECTED not in by_id:
            return _fail("stored post disappeared: " + ",".join(by_id))
        for pid in (MISSING, REJECTED):
            p = by_id[pid]
            if p.get("prompt") != PROMPT:
                return _fail(f"{pid} prompt changed: {p.get('prompt')!r}")
            if p.get("category") != "丝袜":
                return _fail(f"{pid} category changed: {p.get('category')!r}")
            if not p.get("models"):
                return _fail(f"{pid} model mapping removed")
            for rel in (f"images/{pid}_1.jpg", f"images/thumb/{pid}_1.webp"):
                path = os.path.join(root, rel)
                if not os.path.isfile(path):
                    return _fail("missing file " + rel)
                if _sha(path) != blobs[rel]:
                    return _fail("file bytes changed " + rel)
        if _sha(models_path) != models_sha:
            return _fail("models.json assignments were rewritten")
        if not os.path.isfile(orphan) or _sha(orphan) != orphan_sha:
            return _fail("unreferenced image was deleted")
        if by_id[MISSING]["models"] != ["林知夏"] or by_id[REJECTED]["models"] != ["韩书允"]:
            return _fail("model mapping changed on the stored posts")
        print("retention fixture ok", json.dumps({
            "kept": summary.get("kept"),
            "removed": summary.get("removed"),
            "images_deleted": summary.get("images_deleted"),
            "posts": summary.get("posts"),
        }, ensure_ascii=False))
        return 0
    finally:
        srv.shutdown()
        shutil.rmtree(root, ignore_errors=True)


def main():
    code = check_published_contract()
    if code:
        return code
    return run_fixture()


if __name__ == "__main__":
    sys.exit(main() or 0)
