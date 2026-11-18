#!/usr/bin/env python3
"""Archive merge and author-reply prompt rules. Does not read or write data/posts.json."""
import os, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xportfolio as xp
import update

USER = xp.USER_ID
PROMPT = "提示词：\n9:16竖版，超写实摄影，机位平视，光线柔和，东亚女性，长发，服装黑色，场景室内，全身构图，质感真实"


def photo(pid, text, author=USER, reply_to=None, reply_parent=None):
    t = {"id": pid, "author_id": author, "text": text, "created_at": "2026-11-01T00:00:00.000Z",
         "attachments": {"media_keys": ["m" + pid]}, "public_metrics": {"like_count": 1}}
    if reply_parent:
        t["referenced_tweets"] = [{"type": "replied_to", "id": reply_parent}]
        t["in_reply_to_user_id"] = reply_to or USER
        t.pop("attachments")
    return t


def wrap(posts):
    media = [{"media_key": "m" + t["id"], "type": "photo", "url": "https://pbs.twimg.com/media/x.jpg", "width": 100, "height": 160}
             for t in posts if t.get("attachments")]
    return {"data": posts, "includes": {"media": media}}


def test_author_reply_prompt_only():
    root = photo("2122705849168834789", "今晚一张。")
    reply = photo("2122705852859904483", PROMPT, reply_parent="2122705849168834789")
    feed, rejected, model_only = xp.normalise([wrap([root]), wrap([reply])])
    assert "2122705849168834789" in feed, rejected
    assert feed["2122705849168834789"]["prompt_source"] == "thread"
    assert "竖版" in feed["2122705849168834789"]["prompt"]
    assert "2122705849168834789" not in model_only


def test_third_party_reply_ignored():
    root = photo("50", "只有一句问候")
    reply = photo("51", PROMPT + "\n林知夏", author="999", reply_to="999", reply_parent="50")
    feed, rejected, model_only = xp.normalise([wrap([root, reply])])
    assert "50" not in feed
    assert model_only == {} or "林知夏" not in (model_only.get("50") or {}).get("models", [])


def test_named_photo_without_prompt_is_model_only():
    root = photo("60", "林知夏，一张无提示词的图片")
    feed, rejected, model_only = xp.normalise([wrap([root])])
    assert "60" not in feed
    assert model_only["60"]["in_feed"] is False
    assert model_only["60"]["models"] == ["林知夏"]
    assert model_only["60"]["prompt"] == ""


def test_unnamed_photo_is_not_assigned():
    root = photo("70", "一张没有角色名字的图片")
    feed, rejected, model_only = xp.normalise([wrap([root])])
    assert "70" not in feed and "70" not in model_only


def test_all_three_names_are_not_assigned():
    post = {"id": "2117870734303531012", "text": "韩书允 Han Seoyun & 姜宥娜 Kang Yuna & 林知夏 Lin Zhixia",
            "caption": "", "prompt": "", "thread": []}
    assert xp.model_names(post) == []


def test_missing_source_does_not_drop():
    existing = {"2122359287666065800": {
        "id": "2122359287666065800", "images": ["images/2122359287666065800_1.jpg"],
        "thumbs": ["images/thumb/2122359287666065800_1.webp"],
        "prompt": "keep me", "caption": "old", "text": "old", "thread": [],
        "models": ["姜宥娜"], "in_feed": True, "series": ["姜宥娜"],
    }}
    merged, added, refreshed = xp.merge_archive(existing, {})
    assert "2122359287666065800" in merged
    kept = merged["2122359287666065800"]
    assert kept["prompt"] == "keep me"
    assert kept["in_feed"] is True
    assert kept["image_models"] == [None]
    assert kept["models"] == []
    assert added == []


def test_one_confirmed_image_does_not_label_siblings():
    posts = {"9": {
        "id": "9",
        "images": ["images/9_1.jpg", "images/9_2.jpg"],
        "models": ["韩书允"],
        "image_models": ["韩书允", "韩书允"],
    }, "8": {
        "id": "8",
        "images": ["images/8_1.jpg"],
        "models": ["姜宥娜"],
        "image_models": ["姜宥娜"],
    }}
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "map.json")
        json.dump({
            "confirmed": [{"post_id": "9", "index": 1, "src": "images/9_1.jpg", "model_zh": "林知夏"}],
            "pending": [{"post_id": "9", "index": 2, "src": "images/9_2.jpg", "status": "uncertain", "reason": "待审"}],
        }, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        xp.apply_model_media(posts, path)
    assert posts["9"]["image_models"] == ["林知夏", None]
    assert posts["9"]["models"] == ["林知夏"]
    assert posts["8"]["image_models"] == ["姜宥娜"]
    assert posts["8"]["models"] == ["姜宥娜"]


def test_replace_clears_omitted_and_explicit_unassign():
    posts = {"9": {
        "id": "9",
        "images": ["images/9_1.jpg", "images/9_2.jpg", "images/9_3.jpg"],
        "thumbs": ["images/thumb/9_1.webp", "images/thumb/9_2.webp", "images/thumb/9_3.webp"],
        "image_models": ["韩书允", "林知夏", "姜宥娜"],
        "models": ["韩书允", "林知夏", "姜宥娜"],
        "in_feed": True,
        "category": "丝袜",
        "series": ["丝袜"],
        "prompt": "keep me",
        "caption": "keep",
    }}
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "map.json")
        json.dump({
            "replace": True,
            "confirmed": [
                {"post_id": "9", "index": 2, "src": "images/9_2.jpg", "model_zh": "姜宥娜"},
                {"post_id": "9", "index": 3, "src": "images/WRONG.jpg", "model_zh": "韩书允"},
            ],
            "unassigned": [{"post_id": "9", "index": 1, "src": "images/9_1.jpg", "status": "unassigned"}],
        }, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        xp.apply_model_media(posts, path)
    assert posts["9"]["image_models"] == [None, "姜宥娜", None]
    assert posts["9"]["models"] == ["姜宥娜"]
    assert posts["9"]["images"] == ["images/9_1.jpg", "images/9_2.jpg", "images/9_3.jpg"]
    assert posts["9"]["prompt"] == "keep me"
    assert posts["9"]["category"] == "丝袜"
    assert posts["9"]["series"] == ["丝袜"]
    assert posts["9"]["in_feed"] is True


def test_media_rows_replace_previous_labels():
    posts = {"9": {
        "id": "9",
        "images": ["images/9_1.jpg", "images/9_2.jpg"],
        "image_models": ["林知夏", "韩书允"],
        "models": ["林知夏", "韩书允"],
        "category": "夜拍",
        "series": ["夜拍"],
        "prompt": "keep",
        "in_feed": True,
    }}
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "map.json")
        json.dump({
            "replace": True,
            "media": [
                {"post_id": "9", "index": 1, "src": "images/9_1.jpg", "status": "pending", "models": []},
                {"post_id": "9", "index": 2, "src": "images/9_2.jpg", "status": "confirmed",
                 "models": [{"zh": "林知夏", "en": "Lin Zhixia"}]},
            ],
        }, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        xp.apply_model_media(posts, path)
    assert posts["9"]["image_models"] == [None, "林知夏"]
    assert posts["9"]["models"] == ["林知夏"]
    assert posts["9"]["category"] == "夜拍"
    assert posts["9"]["prompt"] == "keep"
    assert posts["9"]["in_feed"] is True


def test_cleanup_keeps_manifest(tmp=None):
    with tempfile.TemporaryDirectory() as tmp:
        img = os.path.join(tmp, "images"); thumb = os.path.join(tmp, "thumb"); os.makedirs(img); os.makedirs(thumb)
        open(os.path.join(img, "keep.jpg"), "w").close()
        open(os.path.join(img, "orphan.jpg"), "w").close()
        manifest = os.path.join(tmp, "manifest.json")
        json.dump(["images/keep.jpg"], open(manifest, "w"))
        removed = update.cleanup_images({"1": {"images": [], "thumbs": []}}, img, thumb, manifest)
        assert removed == 1
        assert os.path.exists(os.path.join(img, "keep.jpg"))
        assert not os.path.exists(os.path.join(img, "orphan.jpg"))


if __name__ == "__main__":
    test_author_reply_prompt_only()
    test_third_party_reply_ignored()
    test_named_photo_without_prompt_is_model_only()
    test_unnamed_photo_is_not_assigned()
    test_all_three_names_are_not_assigned()
    test_missing_source_does_not_drop()
    test_one_confirmed_image_does_not_label_siblings()
    test_replace_clears_omitted_and_explicit_unassign()
    test_media_rows_replace_previous_labels()
    test_cleanup_keeps_manifest()
    print("archive tests ok")
