#!/usr/bin/env python3
"""Assign every portfolio post exactly one primary `category`.

Called by scripts/update.py after each merge, and by scripts/publish.sh before
commit, so newly ingested posts are classified automatically. Manual fixes live
in data/category_overrides.json (id -> category, or id -> {category, note}).

A post may keep many `series` tags; `category` is the hall it belongs to.
Characters, 「其他」 and 「偏殿」 are never categories. Tiny halls (< MIN_HALL)
are merged into a close strong fallback, but only for works that were not
manually overridden. A manual override always stands, even if that leaves a
hall with fewer than MIN_HALL works (e.g. POV with two imperial rulings).
If a fallback category later grows to MIN_HALL on its own (new posts), it is
kept as a hall and not merged.
"""
from __future__ import annotations
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "posts.json")
OVERRIDES = os.path.join(ROOT, "data", "category_overrides.json")
REVIEW_MD = os.path.join(ROOT, "review", "categories.md")

MIN_HALL = 3
CHARACTERS = {"韩书允", "林知夏", "姜宥娜"}
NEVER = CHARACTERS | {"其他", "偏殿"}


class CategorizeError(Exception):
    """Fatal classifier/override error; main() exits non-zero."""

# Display / merge-priority order (distinctive theme first, camera/time later).
ORDER = [
    "新中式", "泳装", "学院风", "舞蹈", "职业装", "运动", "微醺",
    "内衣私房", "OOTD", "丝袜", "夜拍", "城市日常",
    "户外", "POV", "Cosplay", "游戏",
]

# When a raw category ends up with fewer than MIN_HALL works, merge it here.
FALLBACK = {
    "户外": "城市日常",
    "游戏": "夜拍",
    "Cosplay": "丝袜",
    "POV": "城市日常",
}

# Keyword rules for posts whose series tags are empty, only 其他, or only weak tags.
# (label, keywords, exclude-phrases)
RULES = [
    ("新中式", ["新中式", "旗袍", "汉服", "中式", "古风"], []),
    ("泳装", ["泳装", "泳衣", "泳池", "游泳", "比基尼", "bikini", "Bikini", "死库水", "海边", "沙滩", "Poolside"], []),
    ("学院风", ["JK", "学院风", "校服", "百褶裙", "水手服", "水手领"], []),
    ("舞蹈", ["舞蹈", "舞者", "练舞", "KPOP", "Kpop", "kpop", "竖一字马", "芭蕾"], []),
    ("职业装", ["职业装", "正装", "办公室", "Office", "秘书", "西装", "OL", "助教", "办公楼"], ["舞蹈教室"]),
    ("运动", ["网球", "瑜伽", "跑步", "健身房", "台球", "攀岩", "骑行", "冲浪", "球场", "哑铃", "gym", "Gym"], []),
    ("微醺", ["微醺", "买醉", "啤酒", "红酒", "酒吧", "🍷", "🍺", "🍻"], []),
    ("内衣私房", ["内衣", "私房", "lingerie", "Lingerie", "睡衣", "睡裙", "卧室", "大床", "真丝", "缎面", "吊带裙", "吊带", "白床", "床上", "赖床", "居家", "私人公寓"], []),
    ("丝袜", ["丝袜", "黑丝", "白丝", "连裤袜", "stockings", "绝对领域", "袜口", "腰丝"], []),
    ("夜拍", ["夜拍", "夜间", "夜色", "深夜", "闪光灯", "直闪", "夜景", "霓虹", "midnight", "Midnight", "午夜"], []),
    ("OOTD", ["OOTD", "ootd", "穿搭", "outfit", "Outfit", "Y2K", "辣妹"], []),
    ("城市日常", ["咖啡", "coffee", "Coffee", "café", "Café", "书店", "下午茶", "便利店", "街头", "街拍", "record store",
              "早饭", "早餐", "蛋糕", "cake", "摩卡", "滨水", "扶梯", "商场"], []),
    ("户外", ["露营", "Camp", "爬山", "山顶", "公园", "花园", "郊外", "帐篷"], []),
    ("POV", ["POV", "第一人称", "自拍视角", "男友视角"], []),
    ("Cosplay", ["Neko", "猫耳", "cosplay", "Cosplay", "漫展", "Henshin", "KDA"], []),
    ("游戏", ["海克斯", "大乱斗", "电竞", "游戏", "夜之城", "赛博朋克"], []),
]

WEAK = {"户外", "POV", "Cosplay", "游戏"}

NEG_BLOCK = re.compile(r"(?m)^\s*(?:\*\*)?\s*(?:负面|Negative|negative|避免|禁止)[^\n]*(?:\n(?!\s*\n)[^\n]*)*")
NEG_CLAUSE = re.compile(r"(?:不穿|避免|不要|禁止|不出现|无需|avoid|no )[^，。；;,.!！?？\n]*")


def _count(text, kw):
    if kw.isascii():
        return len(re.findall(r"(?<![A-Za-z])" + re.escape(kw) + r"(?![A-Za-z])", text))
    return text.count(kw)


def _hits(text, kws, excl):
    t = text
    for e in excl:
        t = t.replace(e, "")
    return sum(_count(t, k) for k in kws)


def text_scores(caption, prompt):
    raw = (caption or "") + "\n" + (prompt or "")
    raw = NEG_CLAUSE.sub("", NEG_BLOCK.sub("", raw))
    cap = NEG_CLAUSE.sub("", caption or "")
    out = {}
    for label, kws, excl in RULES:
        ph = _hits(cap, kws, excl)
        sh = _hits(raw, kws, excl)
        out[label] = ph * 3 + sh
    return out


def load_overrides(path=OVERRIDES):
    if not os.path.exists(path):
        return {}
    raw = json.load(open(path, encoding="utf-8"))
    out = {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        if isinstance(v, str):
            out[str(k)] = {"category": v, "note": ""}
        elif isinstance(v, dict) and v.get("category"):
            out[str(k)] = {"category": v["category"], "note": v.get("note") or ""}
    return out


def validate_overrides(overrides):
    """Reject unknown / forbidden override categories instead of falling back."""
    bad = []
    for pid, info in overrides.items():
        cat = (info or {}).get("category")
        if not cat or cat in NEVER or cat not in ORDER:
            bad.append((str(pid), cat))
    if bad:
        details = "; ".join(f"{pid} → {cat!r}" for pid, cat in bad)
        raise CategorizeError(
            "unknown category in data/category_overrides.json: " + details
        )


def title_of(p):
    cap = (p.get("caption") or "").strip()
    if cap:
        first = cap.split("\n")[0].strip()
        if first and not first.startswith("主题") and len(first) <= 40:
            return first
        if first:
            return first[:36] + ("…" if len(first) > 36 else "")
    pr = p.get("prompt") or ""
    m = re.search(r"主题\s*[：:]\s*(.+)", pr)
    if m:
        t = m.group(1).split("\n")[0].strip().strip("*").strip()
        t = re.split(r"[｜|]", t)[0].strip()
        if t:
            return t[:36]
    return "无题"


def raw_category(p):
    """Return (category, reason, candidates) before the undersize merge."""
    scores = text_scores(p.get("caption") or "", p.get("prompt") or "")
    tags = [s for s in (p.get("series") or []) if s not in NEVER]
    strong = [s for s in tags if s not in WEAK]
    candidates = []

    def by_order(pool):
        return [c for c in ORDER if c in pool]

    # Prefer a strong series tag, ranked by DISTINCTIVENESS (ORDER), not tag order.
    if strong:
        ranked = by_order(strong)
        # also mention close text scores
        text_top = [c for c, n in sorted(scores.items(), key=lambda kv: -kv[1]) if n >= 2][:3]
        for c in text_top:
            if c not in candidates:
                candidates.append(c)
        for c in ranked:
            if c not in candidates:
                candidates.append(c)
        return ranked[0], "series:" + "+".join(strong), candidates or ranked[:3]

    # No strong tag: use text, then weak tags.
    ranked_text = [c for c, n in sorted(
        ((c, n) for c, n in scores.items() if n > 0), key=lambda kv: (-kv[1], ORDER.index(kv[0]) if kv[0] in ORDER else 99)
    )]
    nonweak_text = [c for c in ranked_text if c not in WEAK]
    if nonweak_text:
        return nonweak_text[0], "text", nonweak_text[:3] + [c for c in ranked_text if c in WEAK]
    # only weak signals remain (POV / 户外 / …)
    weak = by_order(tags)
    if ranked_text:
        return ranked_text[0], "text-weak", ranked_text[:3] + weak
    if weak:
        return weak[0], "weak-tag:" + weak[0], weak
    return "城市日常", "default", ["城市日常"]


def annotate(posts, overrides=None):
    """Mutate a list or id->post dict. Returns (stats, uncertain)."""
    if isinstance(posts, dict):
        items = list(posts.values())
    else:
        items = list(posts)
    overrides = overrides if overrides is not None else load_overrides()
    uncertain = []
    raw = {}
    # Model-hall-only and pending-review records stay in posts.json but are not theme halls.
    items = [p for p in items if p.get("main_hall") is not False]
    for p in items:
        pid = str(p["id"])
        if pid in overrides:
            cat = overrides[pid]["category"]
            if cat in NEVER or cat not in ORDER:
                raise CategorizeError(
                    f"unknown category in data/category_overrides.json: {pid} → {cat!r}"
                )
            reason = "override"
            cands = [cat]
            if overrides[pid]["note"]:
                reason += ": " + overrides[pid]["note"]
            p["_override"] = True
        else:
            cat, reason, cands = raw_category(p)
            if cat in NEVER or cat not in ORDER:
                cat, reason, cands = "城市日常", "invalid-fallback", ["城市日常"]
        p["_raw_category"] = cat
        p["_cat_reason"] = reason
        p["_cat_candidates"] = cands
        raw.setdefault(cat, []).append(p)

    def apply_merge(p, src, dest):
        p["_raw_category"] = dest
        p["_cat_reason"] += f" → merge {src}→{dest} (<{MIN_HALL})"
        cands = p.get("_cat_candidates") or []
        if dest not in cands:
            cands.append(dest)
        if src not in cands:
            cands.insert(0, src)
        p["_cat_candidates"] = cands

    # Merge undersized halls into a close strong category (may cascade once).
    # Manual overrides are never moved, even when the remaining hall is tiny.
    for cat in list(ORDER):
        group = [p for p in items if p["_raw_category"] == cat]
        dest = FALLBACK.get(cat)
        if dest and 0 < len(group) < MIN_HALL:
            for p in group:
                if p.get("_override"):
                    continue
                apply_merge(p, cat, dest)
    # Last resort: leftover tiny *auto* groups (not held by an override) go to fallback/城市日常
    counts = {}
    for p in items:
        counts[p["_raw_category"]] = counts.get(p["_raw_category"], 0) + 1
    for p in items:
        if p.get("_override"):
            continue
        cat = p["_raw_category"]
        if counts.get(cat, 0) < MIN_HALL and cat != "城市日常":
            dest = FALLBACK.get(cat, "城市日常")
            apply_merge(p, cat, dest)

    for p in items:
        p["category"] = p["_raw_category"]

    # Uncertain: only genuine judgment calls, not every multi-tag work.
    #  - manual override, merge of a tiny hall, or default/fallback
    #  - was untagged/其他 (text-classified)
    #  - two or more *strong* series tags (a real fork, e.g. 学院风 vs 舞蹈)
    for p in items:
        reason = p.get("_cat_reason") or ""
        series = [s for s in (p.get("series") or []) if s not in NEVER]
        # 丝袜 is often a material layered on a stronger theme; a real fork is two *themes*
        themes = [s for s in series if s not in WEAK and s != "丝袜"]
        flag = False
        why = reason
        cands = [p["category"]]
        if reason.startswith("override") or "merge" in reason or reason.startswith("default") or reason.startswith("invalid"):
            flag = True
        if reason.startswith("text") or reason.startswith("weak-tag"):
            flag = True  # no strong series tag; classifier read the prompt
        if len(themes) >= 2:
            flag = True
            why = reason + " · 主题交叉 " + "+".join(themes)
        # 丝袜被选为主键，但又有场景/穿搭主题，值得一看
        if p["category"] == "丝袜" and themes:
            flag = True
            why = reason + " · 丝袜 vs " + "+".join(themes)
        for c in (p.get("_cat_candidates") or []) + series + themes:
            if c not in cands and c in ORDER:
                cands.append(c)
        if flag:
            uncertain.append({
                "id": str(p["id"]),
                "title": title_of(p),
                "category": p["category"],
                "candidates": cands,
                "why": why,
                "series": p.get("series") or [],
            })

    for p in items:
        for k in ("_raw_category", "_cat_reason", "_cat_candidates", "_override"):
            p.pop(k, None)

    counts = {}
    for p in items:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    # Any category that still has works is a hall, including override-held halls under MIN_HALL.
    order = [c for c in ORDER if counts.get(c, 0) > 0]
    stats = {"counts": {c: counts[c] for c in order}, "order": order, "total": len(items)}
    assert len(items) == sum(counts.values())
    assert all(p.get("category") not in NEVER for p in items)
    assert all(counts[c] >= 1 for c in order)
    return stats, uncertain


def attach(path=DATA, overrides_path=OVERRIDES, write=True):
    data = json.load(open(path, encoding="utf-8"))
    overrides = load_overrides(overrides_path)
    validate_overrides(overrides)
    stats, uncertain = annotate(data["posts"], overrides)
    data["category_order"] = stats["order"]
    if write:
        tmp = path + ".tmp"
        json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    return data, stats, uncertain


def write_review(stats, uncertain, path=REVIEW_MD):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# 作品主键分类 · 呈皇帝审阅",
        "",
        "每件作品恰好一个主键 `category`（可保留多个 series 标签）。已取消「偏殿」「其他」。",
        "不足 3 件的自动分类并入最接近的大类；若日后该类别攒满 3 件，会自动重新独立成殿。",
        "写入 `data/category_overrides.json` 的人工修正始终保留，即使该殿不足 3 件。",
        "",
        f"合计 **{stats['total']}** 件。",
        "",
        "## 分类一览",
        "",
        "| 分类 | 件数 |",
        "| --- | ---: |",
    ]
    for c, n in stats["counts"].items():
        lines.append(f"| {c} | {n} |")
    def row(u):
        cands = "、".join(u["candidates"])
        why = u["why"].replace("|", "\\|")
        title = u["title"].replace("|", "\\|")
        return f"| `{u['id']}` | {title} | {u['category']} | {cands} | {why} |"
    header = ["| id | 标题 | 当前分类 | 候选 | 原因 |", "| --- | --- | --- | --- | --- |"]
    priority, cross = [], []
    for u in uncertain:
        is_cross = "主题交叉" in u["why"] or "丝袜 vs" in u["why"]
        is_pri = u["why"].startswith("text") or "merge" in u["why"] or u["why"].startswith("default") or u["why"].startswith("override") or u["why"].startswith("weak-tag") or u["why"].startswith("invalid")
        if is_pri:
            priority.append(u)
        elif is_cross:
            cross.append(u)
        else:
            priority.append(u)
    lines += [
        "",
        "## 请优先审阅",
        "",
        "原「其他」或无强标签、由正文判定、由不足 3 件的小类并入，或已由人工覆盖指定。改判请写入 `data/category_overrides.json`。",
        "",
        *header,
    ]
    lines += [row(u) for u in priority] or ["| — | — | — | — | 无 |"]
    lines += [
        "",
        "## 主题交叉（备查）",
        "",
        "作品带有多个主题标签，分类器按「更特殊的主题优先」（例如 新中式优于丝袜）选定主键。一般可维持原判，有异议再改。",
        "",
        *header,
    ]
    lines += [row(u) for u in cross] or ["| — | — | — | — | 无 |"]
    lines.append("")

    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path


def main():
    try:
        data, stats, uncertain = attach()
    except CategorizeError as e:
        print(str(e), file=sys.stderr)
        return 1
    path = write_review(stats, uncertain)
    print(json.dumps({"posts": stats["total"], "categories": stats["counts"],
                      "uncertain": len(uncertain), "review": path}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main() or 0)
