# YLL·Hara 作品集（yanlvlab.github.io）

@GenRyoma（YLL·Hara）的 AI 生图作品展示站。纯静态 HTML/CSS/JS，无构建步骤，直接作为 GitHub Pages 根目录发布
（计划仓库 `YanLvLab/YanLvLab.github.io`，网址 https://yanlvlab.github.io）。

## 收录规则

1. 只收 @GenRyoma 本人的**原创带图帖**：不收纯文字帖、回复、转帖，也不收没有自己图片的引用帖；GIF／视频不收。
2. **只收附带生图提示词的作品**（2026-11-12 起的规则）。提示词可以在帖子正文里，也可以在本人在该帖下自回的串帖里。
   判定标准（`scripts/xportfolio.py` 的 `detect_prompt`）：
   - 正文出现「提示词／prompt／关键词」标签，且后面跟着实际内容 → 收；
   - 或有一段明显的参数式生图描述（画幅、机位、镜头、光线、服装、场景、人物设定等，中英文都算，命中 ≥4 个特征词且足够长）→ 收；
   - 只命中少量特征词或标签后几乎没内容 → 判为「不确定」，**默认不收**，记入 `review/excluded.json`（verdict = `unsure`）供人工复核；
   - 其余 → 不收。不收的帖子图片会从 `images/` 删除。
3. 人工覆盖：`data/hidden.json`
   - `ids`：永不展示（截图、生活照、随笔等）；
   - `include_ids`：人工确认有提示词但没被自动识别的帖子，强制收录。
   改完运行 `python3 scripts/update.py --reclassify`。
4. 只用公开帖子内容，不放私信或任何私人数据。

### 文案与提示词的切分

帖子开头的短文案才算「文案」（`caption`）。从第一行出现下列任一情况起，到结尾全部原样算作「提示词」（`prompt`）：
「提示词／prompt／关键词」标签行；提示词小节标题（统一…、…设定、主题、时间基准、画幅、人物、服装、场景、镜头、动作、表情、负面等）；
「标题｜副标题」式标题行；或一行里含 2 个以上生图参数词。只有打头的单独标签行（如「提示词：」）会被去掉，其余一字不改。
提示词在本人自回串帖里时，取串帖里所有含提示词的回复，原文全收。

### 系列标签

- 主要依据：文案 + 提示词里的标题行（含「｜」的短行）和「主题：/Theme」行，每命中一次记 3 分；
- 次要依据：提示词正文，先去掉负面提示词段，以及「不穿／避免／不要／禁止」后面的从句，每命中一次记 1 分，且要命中 2 次以上才算；
- 角色系列（韩书允、林知夏、姜宥娜）：文案或提示词里出现一次即归入，不受「至少两次」限制；
- 丝袜：文案或标题提到，或正文里「丝袜」出现 3 次以上，才归入；
- 职业装：先排除「舞蹈教室」再匹配「教室」；运动只认网球、瑜伽、跑步、健身房、台球、攀岩、骑行、冲浪等场景词；
- 一条作品可有多个系列，按分数从高到低排列，第一个为主系列；都不命中标「其他」；
- `series_order` 只列当前有作品的系列（韩书允、姜宥娜等角色有了带提示词的作品后会自动出现）。

### 角色廊（2026-11-18 10:37 +08 起）

2026-11-22 增量之后，站内最新作品是 `2124089689304953020`（2026-11-21T18:37:00+08:00）。此前的水位是 `2122716282751754684`（2026-11-17T23:39:34+08:00）。
这个时间之后、2026-11-18T10:37:00+08:00 之前的带提示词作品仍进入主题展厅，不进入角色廊。
截止时间及之后，只有作者正文或本人自回里点名恰好一位角色的图片进入韩书允、林知夏、姜宥娜廊；点到两位或三位则不入廊。
无提示词但有这一位角色名的图片只出现在角色廊。2026-11-18 以前的视觉对照和旧名字标签不再回填。
增量用一份 JSON：`posts`、`replies`、`full` 为 X API 页，可选 `profile`。原始页不写入网站。
`python3 scripts/update.py --dataset <file>`。

### 站点开关（`site.config.json`，由皇帝决定；当前 adult_notice=true、noindex=false）

- `noindex`：true 时在 `index.html` 写入 `<meta name="robots" content="noindex, nofollow">`，`robots.txt` 改为 `Disallow: /`；
- `adult_notice`：true 时首次访问显示年满 18 岁确认层（文案见 `adult_notice_text` 等字段，确认后记在浏览器本地）。
改完运行 `python3 scripts/apply_config.py`（`update.py` 每次运行也会自动套用）。

### 分享卡片

`og.jpg` 是固定的文字卡（深色底，YLL·Hara、@GenRyoma、「AI 时尚影像 · AI Fashion Portrait」），由 `scripts/make_og.py` 生成，
不使用任何作品图，日常更新不会改动它。

## 目录

```
index.html            页面（头像/简介/筛选/排序/瀑布流/灯箱，og 分享卡片）
assets/style.css      样式（深色、响应式）
assets/app.js         渲染、筛选、排序、灯箱、复制提示词
data/posts.json       作品数据（profile、last_updated、series_order、posts[]）
data/hidden.json      人工覆盖清单
images/<id>_<n>.jpg   原图（pbs.twimg.com ?name=orig）
images/thumb/<id>_<n>.webp  720px 缩略图（网格用，灯箱用原图）
images/avatar.jpg, images/banner.jpg
og.jpg                1200×630 固定文字分享卡片（scripts/make_og.py 生成）
site.config.json      站点开关：noindex / adult_notice（默认关）
robots.txt            由 apply_config.py 生成
preview.png           首页截图
scripts/xportfolio.py 共享逻辑：规范化 X API 响应、提示词判定、系列归类、下载
scripts/update.py     每日合并脚本
scripts/apply_config.py  套用 site.config.json
scripts/make_og.py    生成固定文字 og.jpg
review/excluded.json  被排除/不确定的帖子清单（本地复核用，git 忽略，不发布）
raw/, inbox/          原始 X API 响应（git 忽略，不发布）
```

`posts.json` 每条：`id`、`created_at`（上海时间 ISO）、`text`、`thread`（本人自回串帖）、`caption`（提示词前的文案）、
`prompt`、`prompt_source`（post / thread / manual）、`url`、`images`、`thumbs`、`media`（原始地址与宽高）、
`metrics`（impressions 曝光 / likes 赞 / bookmarks 收藏 / reposts / replies）、`series`（系列标签，第一个为主系列）。

系列标签按正文 + 提示词关键词自动判断（规则表在 `xportfolio.py` 的 `SERIES`，可增删），归不了的标「其他」。

## 每日更新流程（供例行调用）

X 数据只能通过 Grok Bot 的 X MCP 工具读取（仓库里不存任何 API key）。完整流程：

1. 取起点：`python3 scripts/update.py --print-since-time` → UTC 时间 `START`
   （站内最新作品时间往前 48 小时，可补上后来才在串帖里补发提示词的帖子，并刷新近两天的互动数）。
2. 用 X 工具抓取，原始响应逐页存入 `inbox/`（`<D>` = 上海日期 `YYYYMMDD`）：
   - 新帖：`search_posts_all`，query `from:GenRyoma has:images -is:retweet -is:reply`，`start_time=START`，
     `expansions=["attachments.media_keys","referenced_posts"]`，`media.fields=["media_key","type","url","width","height"]`，
     `post.fields=["created_at","public_metrics","attachments","entities","referenced_tweets","text","note_post","author_id","in_reply_to_user_id"]`；
     每页最多 25 条，按 `next_token` 翻到底 → `inbox/<D>-1posts-<n>.json`
   - 本人自回串帖：query `from:GenRyoma to:GenRyoma is:reply`，同样参数 → `inbox/<D>-2replies-<n>.json`
   - 补全长文：把上面拿到的全部 id 用 `get_posts_by_ids`（每次 ≤100 个，同样字段）再取一次 → `inbox/<D>-3full-<n>.json`
     （搜索结果里的长帖常只有截断的 `text`；文件名排序保证它最后合并）
   - （可选）`get_users_by_username` username=GenRyoma → `inbox/<D>-profile.json`
3. 合并：`python3 scripts/update.py --input inbox/<D>-*posts*.json inbox/<D>-*replies*.json inbox/<D>-*full*.json [--profile inbox/<D>-profile.json]`
   - 只追加尚未收录、且通过提示词规则的帖子（下载原图 + 缩略图）；已收录的刷新互动数；不再合规或被 hidden 的移除并删图；
   - 更新 `last_updated`，套用 `site.config.json`，不改 `og.jpg`；打印一行 JSON 摘要（added / dropped / posts / images / uncertain …）。
4. 发布：`scripts/publish.sh --no-update`
   （或直接 `scripts/publish.sh`：它会自己按当天日期找 `inbox/<D>-*.json` 跑第 3 步，再发布）。
   - 有变化才 `git commit` 并 `git push` 到 `YanLvLab/YanLvLab.github.io` 的 `main`；没变化什么都不做；
   - 令牌：优先用环境变量 `GITHUB_TOKEN`，缺失或无效（`/user` 不返回 200）时回退读取 `~/.secrets/github_token`
     （仓库之外，权限 600；可用 `GITHUB_TOKEN_FILE` 指定别的路径）。只在运行时通过一次性 credential helper 使用，
     不打印、不写入任何文件或 remote URL；
   - 若没有新改动但本地 `main` 还没推上 GitHub，也会补推一次；
   - 推送前会检查 `raw/`、`review/`、`inbox/` 都被 `.gitignore` 排除，否则拒绝发布。
5. 汇报：把 update.py 的摘要和 publish.sh 输出的提交 sha 报给主人；`uncertain` 不为 0 时附上 `review/excluded.json` 里的待复核条目。

发布**只走 git**（GitHub Pages 从 `main` 分支根目录发布），不要用网页上传或 API 逐个写文件。`raw/`、`review/`、`inbox/`
以及缓存、密钥文件必须留在 `.gitignore` 里，推送前可用 `git status --ignored` 和 `git ls-files` 核对。

本地自测：`python3 -m http.server 8765`，打开 http://localhost:8765 。

其他命令：

```
python3 scripts/update.py --print-since-id     # 站内最新作品 id
python3 scripts/update.py --reclassify         # 只按现有数据重跑提示词规则、系列归类、hidden/include 覆盖
python3 scripts/update.py --rebuild --input raw/*.json --profile raw/profile.json   # 从原始响应整站重建
```

依赖：Python 3.9+、Pillow（生成缩略图和 og 图）。
