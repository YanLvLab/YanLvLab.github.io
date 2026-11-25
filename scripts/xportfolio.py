"""Shared helpers: normalise X API v2 responses into portfolio posts, classify, extract prompts, download images."""
import json, re, os, sys, urllib.request, time
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "images")
THUMB_DIR = os.path.join(IMG_DIR, "thumb")
DATA = os.path.join(ROOT, "data", "posts.json")
MODEL_MEDIA = os.path.join(ROOT, "data", "model_media.json")
HIDDEN = os.path.join(ROOT, "data", "hidden.json")
SHANGHAI = timezone(timedelta(hours=8))
USERNAME = "GenRyoma"

# ---- series rules: (label, keywords, exclude-phrases). See classify() for how they are scored.
SERIES = [
    ("韩书允", ["韩书允", "Han Seoyun", "Seoyun", "한서윤"], []),
    ("林知夏", ["林知夏", "Lin Zhixia", "Zhixia"], []),
    ("姜宥娜", ["姜宥娜", "Kang Yuna", "강유나"], []),
    ("新中式", ["新中式", "旗袍", "汉服", "中式", "古风"], []),
    ("夜拍", ["夜拍", "夜间", "夜色", "深夜", "闪光灯", "直闪", "夜景", "霓虹", "midnight", "Midnight", "午夜"], []),
    ("泳装", ["泳装", "泳衣", "泳池", "游泳", "比基尼", "bikini", "Bikini", "死库水", "海边", "沙滩", "Poolside"], []),
    ("职业装", ["职业装", "正装", "教室", "老师", "办公室", "Office", "秘书", "西装", "OL", "Professional", "助教"], ["舞蹈教室"]),
    ("舞蹈", ["舞蹈", "舞者", "练舞", "KPOP", "Kpop", "kpop", "Dance", "dance", "竖一字马", "芭蕾"], []),
    ("运动", ["网球", "瑜伽", "跑步", "健身房", "台球", "攀岩", "骑行", "冲浪", "球场", "哑铃", "gym", "Gym", "🎱"], []),
    ("Cosplay", ["Neko", "猫耳", "cosplay", "Cosplay", "呪術廻戦", "Henshin", "KDA", "FIRESTARTER"], []),
    ("微醺", ["微醺", "买醉", "啤酒", "红酒", "酒吧", "🍷", "🍺", "🍻"], []),
    ("户外", ["露营", "Camp", "爬山", "山顶", "公园", "花园", "郊外"], []),
    ("学院风", ["JK", "学院风", "校服", "百褶裙"], []),
    ("内衣私房", ["内衣", "私房", "lingerie", "Lingerie", "睡衣", "卧室", "大床", "真丝", "缎面", "吊带裙", "床上", "白床"], []),
    ("丝袜", ["丝袜", "黑丝", "白丝", "连裤袜", "stockings", "绝对领域", "袜口"], []),
    ("OOTD", ["OOTD", "ootd", "穿搭", "outfit", "Outfit"], []),
    ("POV", ["POV", "第一人称", "自拍视角", "男友视角"], []),
    ("城市日常", ["咖啡", "coffee", "Coffee", "café", "Café", "书店", "下午茶", "便利店", "街头", "record store", "温室",
              "早饭", "早餐", "蛋糕", "cake", "摩卡"], []),
    ("游戏", ["海克斯", "大乱斗", "电竞", "游戏"], []),
]
OTHER = "其他"
CHARACTERS = {"韩书允", "林知夏", "姜宥娜"}
# English names are the author's, from profile.bio and the keyword lists above. Not inferred from pictures.
CANON_MODELS = [
    {"zh": "韩书允", "en": "Han Seoyun"},
    {"zh": "林知夏", "en": "Lin Zhixia"},
    {"zh": "姜宥娜", "en": "Kang Yuna"},
]

USER_ID = "1802687195163299840"
TCO = re.compile(r"\s*https://t\.co/\w+")

# ---- prompt detection --------------------------------------------------------------------------
# Rule (2026-11-12, 皇帝): only image posts that carry a generation prompt are published — in the post
# itself or in the author's own reply thread under it. A prompt = an explicit 提示词/prompt label, or a clear
# parameter-style generation description (aspect ratio, camera, lighting, outfit, scene ...).
PROMPT_LABEL = re.compile(r"(^|\n)[ \t]*(?:[#【\[*]*)\s*(?:修正版|正向|完整|英文|中文)?(?:提示词|Prompt|prompt|PROMPT|关键词)(?:[】\]*]*)\s*(?:[:：]|\n|$)")
DESCRIPTORS = [
    "竖版", "横版", "横屏", "竖屏", "画幅", "9:16", "4:5", "16:9", "3:4", "2:3", "1:1", "机位", "俯拍", "仰拍", "平视",
    "镜头", "构图", "景深", "光线", "光影", "补光", "侧光", "逆光", "写实", "摄影", "质感", "成年", "东亚女性", "东亚女",
    "身高", "cm", "发型", "长发", "马尾", "妆容", "五官", "服装", "穿着", "场景", "背景", "8K", "mm", "人物设定",
    "抓拍", "负面", "全身", "半身", "特写", "色调", "胶片", "颗粒", "闪光灯",
    "photorealistic", "ultra-realistic", "hyper-realistic", "aspect ratio", "camera", "lens", "lighting", "shot on",
    "composition", "depth of field", "vertical", "full body", "close-up", "wearing", "outfit", "background",
    "east asian", "theme:", "scene", "pose", "bodysuit", "neckline",
]


def to_shanghai(iso):
    iso = iso.replace("Z", "+00:00")
    return datetime.fromisoformat(iso).astimezone(SHANGHAI).isoformat()


def _hits(t):
    tl = t.lower()
    return {d for d in DESCRIPTORS if d.lower() in tl}


# A line that starts the prompt block even without a 提示词 label: section headers of a written prompt
HEADER = re.compile(r"^\s*(?:\*\*|#+\s*|【)?\s*(?:[一二三四五六七八九十]+、|\d{1,2}[｜|.、]|"
                    r"统一|.{0,6}设定|主题|时间基准|画幅|画面|人物|角色|服装|穿搭|造型|场景|镜头|机位|光线|灯光|摄影|拍摄|"
                    r"构图|动作|姿势|表情|妆容|发型|风格|色调|负面|Theme|THEME|Scene|Style|Subject|Outfit|Camera|Lighting)")
TITLE = re.compile(r"^[^\n]{1,40}[｜|][^\n]{1,40}$")  # "Hotel Vanity｜酒店浴室·肉色丝袜写真"


def _is_label(line):
    return bool(PROMPT_LABEL.match("\n" + line))


def _strip_label(line):
    m = PROMPT_LABEL.match("\n" + line)
    return ("\n" + line)[m.end():].strip() if m else line


def detect_prompt(text):
    """Return (caption, prompt, verdict) with verdict in yes / unsure / no.

    The caption is only the leading lines before the prompt block starts. The prompt block starts at the first
    line that is a 提示词/prompt label, a prompt section header (统一…/…设定/主题/时间基准/画幅/人物/服装…),
    a "标题｜副标题" title line, or a line dense with generation parameters. Everything from there to the end
    is the prompt, verbatim (only a leading bare label line is dropped)."""
    t = text.strip()
    lines = t.split("\n")
    k = None
    for i, ln in enumerate(lines):
        s_ = ln.strip()
        if not s_:
            continue
        if _is_label(s_) or HEADER.match(s_) or (TITLE.match(s_) and i > 0) or len(_hits(s_)) >= 2:
            k = i; break
    if k is not None:
        cap = "\n".join(lines[:k]).strip()
        body = lines[k:]
        if _is_label(body[0].strip()):
            rest0 = _strip_label(body[0].strip())
            body = ([rest0] if rest0 else []) + body[1:]
        prompt = "\n".join(body).strip()
        labelled = PROMPT_LABEL.search("\n" + "\n".join(lines[k:])) is not None
        h = _hits(prompt)
        if (labelled and (len(prompt) >= 25 or len(h) >= 2)) or (len(h) >= 4 and len(prompt) >= 50):
            return cap, prompt, "yes"
    h = _hits(t)
    if (PROMPT_LABEL.search(t) or len(h) >= 3) and len(t) >= 20:
        return t, "", "unsure"
    return t, "", "no"


def split_prompt(text):
    cap, prompt, _ = detect_prompt(text)
    return cap, prompt


NEG_BLOCK = re.compile(r"(?m)^\s*(?:\*\*)?\s*(?:负面|Negative|negative|避免|禁止)[^\n]*(?:\n(?!\s*\n)[^\n]*)*")
NEG_CLAUSE = re.compile(r"(?:不穿|避免|不要|禁止|不出现|无需|avoid|no )[^，。；;,.!！?？\n]*")


def _count(text, kw):
    if kw.isascii():
        return len(re.findall(r"(?<![A-Za-z])" + re.escape(kw) + r"(?![A-Za-z])", text))
    return text.count(kw)


def classify(caption, prompt=""):
    """Series tags, best score first.

    primary   = caption + title lines and 主题/Theme lines of the prompt  (each hit scores 3)
    secondary = prompt body without negative-prompt sections and 不穿/避免/不要… clauses (each hit scores 1)
    A series qualifies with >=1 primary hit or >=2 secondary hits. 丝袜 needs a primary hit or 丝袜 >=3 times.
    Character series (韩书允/林知夏/姜宥娜) qualify from one mention anywhere in caption or prompt.
    Exclude phrases (e.g. 舞蹈教室 for 职业装) are removed before matching."""
    plines = prompt.split("\n")
    titles = [l for l in plines if l.strip() and len(l.strip()) <= 60 and
              (TITLE.match(l.strip()) or re.match(r"\s*(?:\*\*)?\s*(主题|Theme|THEME|标题)", l))]
    primary = caption + "\n" + "\n".join(titles)
    secondary = NEG_CLAUSE.sub("", NEG_BLOCK.sub("", "\n".join(l for l in plines if l not in titles)))
    primary = NEG_CLAUSE.sub("", primary)
    scored = []
    for order, (label, kws, excl) in enumerate(SERIES):
        P, S = primary, secondary
        for e in excl:
            P, S = P.replace(e, ""), S.replace(e, "")
        ph = sum(_count(P, k) for k in kws)
        sh = sum(_count(S, k) for k in kws)
        if label in CHARACTERS:  # a named virtual idol counts from a single mention in caption or prompt
            ok = ph + sh >= 1
        else:
            ok = ph >= 1 or (S.count("丝袜") >= 3 if label == "丝袜" else sh >= 2)
        if ok:
            scored.append((-(ph * 3 + sh), order, label))
    return [l for _, _, l in sorted(scored)] or [OTHER]


# One picture that names every model at once is not a portrait of any of them.
AMBIGUOUS_MODEL_IDS = {"2117870734303531012"}
# Picture galleries restart here. Older author names and the visual role-card map are not gallery labels.
GALLERY_CUTOFF = datetime.fromisoformat("2026-11-18T10:37:00+08:00")


def at_or_after_gallery_cutoff(post):
    raw = post.get("created_at") or ""
    if not raw:
        return False
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SHANGHAI)
    return dt.astimezone(SHANGHAI) >= GALLERY_CUTOFF


# Official names only. A short alias such as Seoyun, Zhixia, or Yuna is not a gallery label.
GALLERY_PATTERNS = (
    ("韩书允", re.compile(r"韩书允|Han\s*Seoyun", re.I)),
    ("林知夏", re.compile(r"林知夏|Lin\s*Zhixia", re.I)),
    ("姜宥娜", re.compile(r"姜宥娜|Kang\s*Yuna", re.I)),
)


def model_names(post):
    """Gallery label from the author's own words, and only at or after GALLERY_CUTOFF.

    A stored label is not kept and a picture is not inspected. Official Chinese, spaced English,
    and no-space English names count. Zero names, or more than one name, stay unassigned."""
    if str(post.get("id") or "") in AMBIGUOUS_MODEL_IDS:
        return []
    if not at_or_after_gallery_cutoff(post):
        return []
    blob = "\n".join([post.get("caption") or "", post.get("text") or "", post.get("prompt") or ""]
                     + list(post.get("thread") or []))
    detected = [zh for zh, pat in GALLERY_PATTERNS if pat.search(blob)]
    if len(detected) != 1:
        return []
    return detected


_manual_cache = {"key": None, "map": {}}


def manual_label_map(path=None):
    """Owner-assigned per-image labels. These waive the 2026-11-18 10:37 cutoff.

    Only rows with manual:true are read. A replace:true file with no rows is ignored,
    so an empty gallery file cannot be applied as a wipe."""
    path = path or MODEL_MEDIA
    try:
        st = os.stat(path)
        key = (path, st.st_mtime_ns, st.st_size)
    except OSError:
        return {}
    if _manual_cache["key"] == key:
        return _manual_cache["map"]
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = data.get("media") if isinstance(data.get("media"), list) else list(data.get("confirmed") or [])
    if data.get("replace") and not rows:
        _manual_cache.update(key=key, map={})
        return {}
    out = {}
    for row in rows:
        if not row.get("manual"):
            continue
        if row.get("status") not in (None, "", "confirmed"):
            continue
        zh = row.get("model_zh")
        if zh not in CHARACTERS:
            continue
        pid = str(row.get("post_id") or "")
        if not pid or row.get("index") is None:
            continue
        out.setdefault(pid, {})[int(row["index"])] = zh
    _manual_cache.update(key=key, map=out)
    return out


def stamp_gallery(post, manual_path=None):
    """Write image_models. A manual row wins for that picture, including before the cutoff.

    Does not change prompt, category, series, files, or membership. One manual picture
    does not label its siblings."""
    images = post.get("images") or []
    manual = manual_label_map(manual_path).get(str(post.get("id") or ""))
    if manual is not None:
        labels = []
        for i in range(1, len(images) + 1):
            zh = manual.get(i)
            labels.append(zh if zh in CHARACTERS else None)
        post["image_models"] = labels
        seen = []
        for m in labels:
            if m and m not in seen:
                seen.append(m)
        post["models"] = seen
        return seen
    if post.get("category") == "灵感回响":
        post["models"] = []
        if images:
            post["image_models"] = [None] * len(images)
        return []
    labels = model_names(post)
    post["models"] = labels
    if images:
        post["image_models"] = [labels[0]] * len(images) if len(labels) == 1 else [None] * len(images)
    return labels


def _media_key(row):
    return (str(row.get("post_id")), int(row.get("index")))


def apply_model_media(posts, path=None):
    """Replace per-image labels from a model_media file. One confirmed picture does not label its siblings.

    A confirmed row sets that picture only. A pending, unassigned, or removed row clears it, including a label
    stored earlier. With replace/mode "replace", a picture the file does not confirm is cleared too, so an old
    label cannot stick by being omitted. Posts, prompts, categories, membership, and image files are not changed.
    Returns the number of confirmed labels applied."""
    path = path or MODEL_MEDIA
    if not os.path.exists(path):
        return 0
    data = json.load(open(path, encoding="utf-8"))
    replace = bool(data.get("replace") or data.get("mode") == "replace")
    media = data.get("media")
    has_rows = (isinstance(media, list) and len(media) > 0) or any(data.get(k) for k in ("confirmed", "pending", "unassigned", "removed"))
    if replace and not has_rows:
        print("model_media: refusing empty replace; galleries left untouched", file=sys.stderr)
        return 0
    confirmed, clear, src_of = {}, set(), {}

    def remember_src(key, row):
        if row.get("src"):
            src_of[key] = row["src"]

    def one_label(row):
        found = []
        raw = row.get("models")
        items = raw if isinstance(raw, list) else [row.get("model_zh")]
        for item in items:
            zh = item.get("zh") if isinstance(item, dict) else item
            if zh in CHARACTERS and zh not in found:
                found.append(zh)
        if len(found) == 1 and (row.get("status") in (None, "", "confirmed")):
            return found[0]
        return None

    media = data.get("media")
    if isinstance(media, list):
        for row in media:
            if row.get("post_id") is None or row.get("index") is None:
                continue
            key = _media_key(row)
            remember_src(key, row)
            label = one_label(row) if row.get("status") == "confirmed" else None
            if label:
                confirmed[key] = label
            else:
                clear.add(key)
    else:
        for row in data.get("confirmed") or []:
            if row.get("post_id") is None or row.get("index") is None:
                continue
            key = _media_key(row)
            label = one_label(dict(row, status="confirmed"))
            if not label:
                continue
            confirmed[key] = label
            remember_src(key, row)
        for bucket in ("pending", "unassigned", "removed"):
            for row in data.get(bucket) or []:
                if row.get("post_id") is None or row.get("index") is None:
                    continue
                key = _media_key(row)
                confirmed.pop(key, None)
                clear.add(key)
                remember_src(key, row)
    applied = 0
    for p in posts.values():
        images = list(p.get("images") or [])
        if not images:
            continue
        keys = [(str(p.get("id")), i) for i in range(1, len(images) + 1)]
        if not replace and not any(k in confirmed or k in clear for k in keys):
            continue
        prev = list(p.get("image_models") or [])
        labels = []
        for n, key in enumerate(keys):
            named = key in confirmed and src_of.get(key, images[n]) == images[n]
            if named:
                labels.append(confirmed[key]); applied += 1
            elif key in clear or replace or (key in confirmed and src_of.get(key) not in (None, images[n])):
                labels.append(None)
            elif n < len(prev) and prev[n] in CHARACTERS:
                labels.append(prev[n])
            else:
                labels.append(None)
        p["image_models"] = labels
        seen = []
        for m in labels:
            if m and m not in seen:
                seen.append(m)
        p["models"] = seen
    return applied


def _author_reply(t):
    """True only for @GenRyoma's own reply. A present foreign author_id is never treated as ours."""
    aid = t.get("author_id")
    if aid and str(aid) != USER_ID:
        return False
    reply_to = t.get("in_reply_to_user_id")
    if reply_to and str(reply_to) != USER_ID:
        return False
    return True


def _thread_texts(responses):
    """Author self-replies: map root post id -> list of reply texts (follows reply chains)."""
    parent, texts = {}, {}
    for d in responses:
        for t in d.get("data", []) or []:
            rep = [r["id"] for r in t.get("referenced_tweets", []) if r["type"] == "replied_to"]
            if rep and _author_reply(t):
                parent[t["id"]] = rep[0]
                texts[t["id"]] = TCO.sub("", (t.get("note_tweet") or {}).get("text") or t.get("text", "")).strip()
    out = {}
    for rid, txt in sorted(texts.items(), key=lambda kv: int(kv[0])):
        root, seen = parent[rid], set()
        while root in parent and root not in seen:
            seen.add(root); root = parent[root]
        if txt:
            out.setdefault(root, []).append(txt)
    return out


def evaluate(text, thread):
    """Apply the prompt rule to a post text + its self-reply thread. Returns caption, prompt, verdict, source."""
    cap, prompt, v = detect_prompt(text)
    if v == "yes":
        return cap, prompt, v, "post"
    for r in thread or []:
        _, rp, rv = detect_prompt(r)
        if rv == "yes":
            prompts = [p2 for p2 in (detect_prompt(x)[1] for x in thread) if p2]
            return text, "\n\n".join(prompts) or rp, "yes", "thread"
        if rv == "unsure":
            v = "unsure"
    return text, "", v, None


def _photo_post(t, media):
    refs = {r["type"] for r in t.get("referenced_tweets", [])}
    if refs & {"retweeted", "replied_to"}:
        return None
    keys = (t.get("attachments") or {}).get("media_keys", [])
    photos = [media[k] for k in keys if k in media and media[k].get("type") == "photo"]
    if not photos:
        return None
    foreign = [u for u in (t.get("entities") or {}).get("urls", [])
               if "/photo/" in u.get("expanded_url", "") and f"/{USERNAME}/" not in u.get("expanded_url", "")]
    if foreign and len(foreign) >= len(photos):
        return None
    return photos


def _base_post(t, text, thread, photos, caption, prompt, src, series, models, in_feed):
    pm = t.get("public_metrics") or {}
    return {
        "id": t["id"],
        "created_at": to_shanghai(t["created_at"]),
        "text": text,
        "thread": thread,
        "caption": caption,
        "prompt": prompt,
        "prompt_source": src,
        "url": f"https://x.com/{USERNAME}/status/{t['id']}",
        "quote": "quoted" in {r["type"] for r in t.get("referenced_tweets", [])},
        "media": [{"src": m["url"], "w": m.get("width"), "h": m.get("height")} for m in photos],
        "images": [], "thumbs": [],
        "metrics": {"impressions": pm.get("impression_count"), "likes": pm.get("like_count"),
                    "bookmarks": pm.get("bookmark_count"), "reposts": pm.get("retweet_count"),
                    "replies": pm.get("reply_count")},
        "series": series,
        "models": models,
        "in_feed": in_feed,
    }


def normalise(responses, hidden=(), force=()):
    """responses: raw X API v2 JSON dicts (get_users_posts / search_posts_all, incl. self-reply searches).
    Returns (feed posts, rejected info, model-only posts).

    Feed posts carry the author's own prompt (post body or own replies). Model-only posts are the
    author's images that name 韩书允 / 林知夏 / 姜宥娜 in that text but have no prompt. They are
    archived for the picture galleries and are not part of the theme feed. Third-party replies are ignored."""
    media, posts, rejected, model_only = {}, {}, {}, {}
    for d in responses:
        for m in (d.get("includes") or {}).get("media", []):
            media[m["media_key"]] = m
    threads = _thread_texts(responses)
    for d in responses:
        for t in d.get("data", []) or []:
            photos = _photo_post(t, media)
            if not photos:
                continue
            raw = ((t.get("note_tweet") or {}).get("text") or t.get("text", ""))
            text = TCO.sub("", raw).strip()
            thread = threads.get(t["id"], [])
            caption, prompt, verdict, src = evaluate(text, thread)
            if t["id"] in force and verdict != "yes":
                verdict, src = "yes", src or "manual"
                prompt = prompt or "\n\n".join([text] + thread)
            draft = {"id": t["id"], "created_at": to_shanghai(t["created_at"]),
                     "caption": caption if verdict == "yes" else "", "prompt": prompt if verdict == "yes" else "",
                     "text": text, "thread": thread}
            models = model_names(draft)
            if t["id"] in hidden or verdict != "yes":
                posts.pop(t["id"], None)
                rejected[t["id"]] = {"id": t["id"], "verdict": "hidden" if t["id"] in hidden else verdict,
                                     "created_at": to_shanghai(t["created_at"]), "text": text[:200],
                                     "url": f"https://x.com/{USERNAME}/status/{t['id']}"}
                if models and t["id"] not in hidden:
                    model_only[t["id"]] = _base_post(t, text, thread, photos, "", "", None, list(models), models, False)
                else:
                    model_only.pop(t["id"], None)
                continue
            rejected.pop(t["id"], None)
            model_only.pop(t["id"], None)
            series = classify(caption, prompt)
            posts[t["id"]] = _base_post(t, text, thread, photos, caption, prompt, src, series, models, True)
    return posts, rejected, model_only


def merge_archive(existing, incoming):
    """Stable-id merge. Keys already archived are never deleted because a later fetch omitted them.

    A post that already has a prompt stays in the theme feed. Gallery labels are recomputed from the
    author's words at or after the cutoff; a label stored earlier is not put back. Rows marked manual
    in model_media.json are the exception: they are reapplied even before the cutoff, and an empty
    replace:true file is not a wipe list."""
    added, refreshed = [], 0
    for pid, p in incoming.items():
        if pid in existing:
            old = existing[pid]
            if p.get("metrics"):
                old["metrics"] = p["metrics"]
            if not old.get("prompt") and p.get("in_feed", True) and p.get("prompt"):
                for k in ("thread", "caption", "prompt", "prompt_source", "series", "text", "url"):
                    if k in p:
                        old[k] = p[k]
                old["in_feed"] = True
            elif old.get("in_feed") is None and old.get("prompt"):
                old["in_feed"] = True
            if p.get("images") and not old.get("images"):
                old["images"] = p["images"]
                old["thumbs"] = p.get("thumbs") or []
                old["media"] = p.get("media") or old.get("media")
            refreshed += 1
        else:
            existing[pid] = p
            added.append(pid)
    for old in existing.values():
        if old.get("prompt") and old.get("in_feed") is None:
            old["in_feed"] = True
        stamp_gallery(old)
    return existing, added, refreshed


def _get(url, path, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 portfolio-sync"})
            with urllib.request.urlopen(req, timeout=60) as r, open(path + ".part", "wb") as f:
                f.write(r.read())
            os.replace(path + ".part", path)
            return True
        except Exception as e:
            print("  retry", url, e, file=sys.stderr); time.sleep(2 * (i + 1))
    return False


def download(post):
    """Fetch original-quality images + a 720px webp thumbnail. Fills post['images'] / post['thumbs']."""
    from PIL import Image
    os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(THUMB_DIR, exist_ok=True)
    imgs, thumbs = [], []
    for n, m in enumerate(post["media"], 1):
        base, ext = os.path.splitext(m["src"].split("?")[0])
        ext = ext.lstrip(".") or "jpg"
        name = f"{post['id']}_{n}.{ext}"
        path = os.path.join(IMG_DIR, name)
        if not os.path.exists(path):
            ok = _get(f"{base}?format={ext}&name=orig", path) or _get(f"{base}?format={ext}&name=large", path)
            if not ok:
                print("FAILED", m["src"], file=sys.stderr); continue
        tpath = os.path.join(THUMB_DIR, f"{post['id']}_{n}.webp")
        if not os.path.exists(tpath):
            with Image.open(path) as im:
                im = im.convert("RGB"); m["w"], m["h"] = im.size
                im.thumbnail((720, 720 * 4))
                im.save(tpath, "WEBP", quality=82, method=6)
        imgs.append(f"images/{name}"); thumbs.append(f"images/thumb/{post['id']}_{n}.webp")
    post["images"], post["thumbs"] = imgs, thumbs
    return post



def load_image_overrides():
    """data/image_overrides.json: {work_id: {from_post_id, src?, w?, h?}} — keep prompt, swap photos."""
    path = os.path.join(ROOT, "data", "image_overrides.json")
    try:
        d = json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        return {}
    return {k: v for k, v in d.items() if not str(k).startswith("_") and isinstance(v, dict)}


def _photos_from_responses(responses):
    media = {}
    for d in responses or []:
        for m in (d.get("includes") or {}).get("media", []):
            media[m["media_key"]] = m
    out = {}
    for d in responses or []:
        for t in d.get("data", []) or []:
            keys = (t.get("attachments") or {}).get("media_keys", [])
            photos = [media[k] for k in keys if k in media and media[k].get("type") == "photo"]
            if photos:
                out[str(t["id"])] = [{"src": m["url"], "w": m.get("width"), "h": m.get("height")} for m in photos]
    return out


def _clear_downloaded(post):
    for rel in list(post.get("images") or []) + list(post.get("thumbs") or []):
        fp = os.path.join(ROOT, rel)
        if os.path.isfile(fp):
            os.remove(fp)
    pid = post["id"]
    for n in range(1, 8):
        for ext in ("jpg", "jpeg", "png", "webp"):
            p = os.path.join(IMG_DIR, f"{pid}_{n}.{ext}")
            if os.path.isfile(p):
                os.remove(p)
        t = os.path.join(THUMB_DIR, f"{pid}_{n}.webp")
        if os.path.isfile(t):
            os.remove(t)
    post["images"], post["thumbs"] = [], []


def apply_image_overrides(posts, responses=None, download_now=False):
    """Replace a work's photos with another of the author's posts (or a fixed src). Returns count applied."""
    ov = load_image_overrides()
    if not ov:
        return 0
    photos_by_id = _photos_from_responses(responses)
    applied = 0
    for pid, spec in ov.items():
        if pid not in posts:
            print(f"image override: work {pid} not in set yet", file=sys.stderr)
            continue
        src_id = str(spec.get("from_post_id") or "")
        media = photos_by_id.get(src_id)
        if not media and spec.get("src"):
            media = [{"src": spec["src"], "w": spec.get("w"), "h": spec.get("h")}]
        if not media:
            print(f"image override FAILED: no media for {pid} <- {src_id}", file=sys.stderr)
            continue
        already = posts[pid].get("media") == media and posts[pid].get("images")
        posts[pid]["media"] = media
        if download_now and not already:
            _clear_downloaded(posts[pid])
            download(posts[pid])
            print("image override applied", pid, "<-", src_id or spec.get("src"))
        elif not download_now:
            print("image override media swapped", pid, "<-", src_id or spec.get("src"))
        applied += 1
    return applied


def load_overrides():
    """data/hidden.json: {"ids": [...never show...], "include_ids": [...force-include despite no detected prompt...]}"""
    try:
        d = json.load(open(HIDDEN, encoding="utf-8"))
        return set(d.get("ids", [])), set(d.get("include_ids", []))
    except FileNotFoundError:
        return set(), set()


def save(posts, profile=None):
    old = {}
    if os.path.exists(DATA):
        old = json.load(open(DATA, encoding="utf-8"))
    out = {
        "profile": profile or old.get("profile", {}),
        "last_updated": datetime.now(SHANGHAI).isoformat(timespec="seconds"),
        # only series that currently have works (e.g. 韩书允/姜宥娜 appear once they have a post with a prompt)
        "series_order": [s for s in [x[0] for x in SERIES] + [OTHER] if any(s in p.get("series") or [] for p in posts.values())],
        "models_index": CANON_MODELS,
        "posts": sorted(posts.values(), key=lambda p: int(p["id"]), reverse=True),
    }
    tmp = DATA + ".tmp"
    json.dump(out, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, DATA)
    return out
