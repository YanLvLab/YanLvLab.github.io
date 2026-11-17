/* HARA · 作品集 — vanilla JS, reads data/posts.json (already filtered by update.py / hidden.json). */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n) => n == null ? "—" : n >= 10000 ? (n / 10000).toFixed(n >= 100000 ? 0 : 1) + "万" : n.toLocaleString("zh-CN");
  const pad3 = (n) => String(n).padStart(3, "0");
  const ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fmtDate = (iso, withTime) => {
    const d = new Date(iso); const p = (x) => String(x).padStart(2, "0");
    const s = new Date(d.getTime() + (d.getTimezoneOffset() + 480) * 60000); // Asia/Shanghai
    const day = `${s.getFullYear()}.${p(s.getMonth() + 1)}.${p(s.getDate())}`;
    return withTime ? `${day} ${p(s.getHours())}:${p(s.getMinutes())}` : day;
  };
  /* title:start */
  const HEAD_WORDS = /^(统一|统一设定|设定|主题|时间基准|画幅|画幅与摄影风格|人物|人物设定|服装|服饰|服饰搭配|服装造型|造型|动作|姿势|姿势与动作|表情|负面|负面提示词|场景|光线|光线与风格|风格|构图|镜头|拍摄机位与构图|核心动作|核心动作固定|核心动作严格锁定|妆容|发型|背景|画面|氛围|色调|细节|要求|参数|核心道具)$/;
  const PUNCT = /[，。,.;；!！?？：:、（）()「」“”"]/;
  const FRAMING = /\d+\s*[:：∶]\s*\d+|竖版|横版|竖屏|横屏|画幅|机位|镜头|构图|摄影风格|相机|拍摄|抓拍|自拍视角|分辨率|\b[48]K\b|超写实|写实|真人|摄影棚|质感|光线|打光|景深|焦段|\d+mm|POV|第一人称|视角|仰拍|俯拍|平视/i;
  const PERSON = /成年|\d+\s*岁|身高|体重|身材|模特|五官|面部|脸|皮肤|肤色|肤质|毛孔|发型|长发|短发|湿发|发丝|马尾|腰线|腰部|腰身|腰臀|臀部|臀大肌|臀腿|双腿|腿部|长腿|胸部|肩颈|肩膀|肩头|气质|妆|骨骼|比例|神情|眼神|表情|盘发|刘海|头发|磨皮/;
  const INSTRUCT = /^(保持|参考|基于|沿用|延续|不要|避免|禁止|请|严格|强调|重点|确保|注意|必须)/;
  const MAX_TITLE = 28;
  const cleanLine = (s) => s.replace(/\*\*/g, "").replace(/^#+\s*/, "").replace(/[【】]/g, "").replace(/^[-*·•\s]+/, "").trim();
  const isHeading = (s) => {
    const h = s.replace(/[：:]\s*$/, "").replace(/^([一二三四五六七八九十]+|\d+)[、，,.．)）]\s*/, "").trim();
    if (!h) return true;
    if (/[：:]\s*$/.test(s) && h.length <= 16) return true;
    if (HEAD_WORDS.test(h)) return true;
    if (h.length <= 12 && !PUNCT.test(h)) return true;
    if (/^([一二三四五六七八九十]+|\d+)[、，,.．)）]/.test(s) && h.length <= 16) return true;
    return /^(画幅|场景|设定|风格)/.test(h);
  };
  const clip = (s) => { const a = [...s]; return a.length > MAX_TITLE ? a.slice(0, MAX_TITLE).join("").replace(/[，、,\s]+$/, "") + "…" : s; };
  const tidy = (c) => c.trim().replace(/^(人物|她|模特)?(穿着|身穿|穿上|穿一条|穿)/, "").replace(/^(延续|沿用|参考)[^的，,]{0,12}的/, "").trim();
  function titleFromPrompt(prompt) {
    const lines = String(prompt || "").replace(/\r/g, "").split("\n").map(cleanLine).filter(Boolean);
    const pick = (strict) => {
      for (let line of lines) {
        const theme = line.match(/^主题\s*[：:]\s*(.+)$/);
        if (theme) return theme[1].trim().replace(/[。.]$/, "");
        if (/[｜|]/.test(line) && line.length <= 40 && !/[。；;]/.test(line)) return line.replace(/[。.]$/, ""); // 「标题｜副标题」 line
        const kv = line.match(/^([^，。,.：:]{1,10})[：:]\s*(.*)$/);
        if (kv) {
          const k = kv[1].trim();
          if (/^(服装|服饰|穿搭|造型)/.test(k) && kv[2] && !FRAMING.test(kv[2])) return kv[2].split(/[。；;]/)[0].trim();
          else if (HEAD_WORDS.test(k) || /^(画幅|场景|设定|风格)/.test(k)) continue; // a setting line, not a subject
        }
        if (isHeading(line)) continue;
        line = line.replace(/(\d)\s*[:：]\s*(\d)/g, "$1∶$2"); // keep ratios / clock times in one clause
        for (const sent of line.split(/[。！？!?；;]/)) {
          const FILLER = /^(整体|她拥有|拥有|具有|呈现)/;
          let raw = sent.split(/[，,、：:]/).map(tidy).filter(Boolean);
          if (!raw.length) continue;
          if (strict && (INSTRUCT.test(raw[0]) || FILLER.test(raw[0]))) continue; // instruction / filler sentence
          if (strict) { const f = raw.findIndex((c) => FILLER.test(c)); if (f > 0) raw = raw.slice(0, f); } // drop trailing 「整体呈现…」 adjective lists
          const cl = raw.filter((c) => !FRAMING.test(c));
          if (!cl.length) continue;
          const keep = strict ? cl.filter((c) => !PERSON.test(c) && !INSTRUCT.test(c)) : cl;
          let t = "";
          for (const c of keep) { t = t ? t + "，" + c : c; if ([...t].length >= 8) break; }
          if ([...t].length >= 4) return t;
        }
      }
      return "";
    };
    return pick(true) || pick(false);
  }
  const captionText = (p) => (p.caption || "").replace(/#\S+/g, "").replace(/\*\*/g, "").replace(/[ \t]+/g, " ").replace(/\n{2,}/g, "\n").trim();
  const titleOf = (p) => {
    const c = captionText(p).split("\n").map((s) => s.trim()).find(Boolean) || "";
    if (c) {
      if ([...c].length <= 40) return c;
      const s = c.match(/^.{6,60}?[.!?。！？](?=\s|$)/u); if (s) return s[0].trim();
      let t = [...c].slice(0, 40).join(""); if (/[A-Za-z]$/.test(t) && t.includes(" ")) t = t.replace(/\s+\S*$/, "");
      return t.trim() + "…";
    }
    const t = titleFromPrompt(p.prompt);
    return t ? clip(t) : "无题";
  };
  /* title:end */
  const thumbOf = (p, k = 0) => (p.thumbs && p.thumbs[k]) || p.images[k];
  const newest = (a, b) => b.id.localeCompare(a.id, "en", { numeric: true });
  const dims = (p, k = 0) => {
    const m = (p.media && p.media[k]) || {};
    const w = +m.w || 0, h = +m.h || 0;
    return w > 0 && h > 0 ? ` width="${w}" height="${h}"` : "";
  };
  /* Ornamental frame sits in the relic's padding. Ordinal plaque and count are siblings of the image, never inside it. */
  function relic(img, { plaque = "", tab = "", cls = "" } = {}) {
    return `<span class="relic${cls ? " " + cls : ""}"><span class="edge n" aria-hidden="true"></span><span class="edge e" aria-hidden="true"></span><span class="edge s" aria-hidden="true"></span><span class="edge w" aria-hidden="true"></span><span class="well">${img}</span>${tab}${plaque}</span>`;
  }
  function framePad(el) {
    if (!el) return 48;
    const s = getComputedStyle(el);
    const band = parseFloat(s.getPropertyValue("--band")) || 14;
    const recess = parseFloat(s.getPropertyValue("--recess")) || 9;
    return (band + recess) * 2 + 2;
  }
  function viewportFit(img, maxW, maxH) {
    const nw = img.naturalWidth || +img.getAttribute("width") || 0;
    const nh = img.naturalHeight || +img.getAttribute("height") || 0;
    if (nw < 2 || nh < 2 || maxW < 8 || maxH < 8) return;
    const s = Math.min(maxW / nw, maxH / nh);
    img.style.width = Math.max(1, Math.round(nw * s)) + "px";
    img.style.height = Math.max(1, Math.round(nh * s)) + "px";
  }
  function fitCover() {
    const img = $("#coverImg"), stage = document.querySelector(".cover-stage");
    if (!img || !stage) return;
    const r = stage.getBoundingClientRect();
    const pad = framePad(img.closest(".relic"));
    viewportFit(img, Math.max(64, r.width - pad - 8), Math.max(64, r.height - pad - 4));
  }
  function fitLb() {
    const img = $("#lbImg"), stage = $("#lbStage");
    if (!img || !stage || lb.hidden) return;
    const r = stage.getBoundingClientRect();
    const prev = $("#lbPrev").getBoundingClientRect();
    const next = $("#lbNext").getBoundingClientRect();
    const dots = $("#lbDots");
    const dotsH = dots && dots.children.length ? Math.max(44, dots.getBoundingClientRect().height) : 0;
    const pad = framePad(img.closest(".relic"));
    const gutter = Math.max(44, prev.width) + Math.max(44, next.width) + 20;
    viewportFit(img, Math.max(64, r.width - gutter - pad), Math.max(64, r.height - dotsH - pad - 12));
  }

  // hall vocabulary
  const CHARACTERS = ["韩书允", "林知夏", "姜宥娜"];
  const EN = { "韩书允": "Han Seoyun", "林知夏": "Lin Zhixia", "姜宥娜": "Kang Yuna", "新中式": "Neo-Chinoiserie", "夜拍": "Nocturne", "泳装": "The Swim", "职业装": "Office Couture",
    "舞蹈": "The Dance", "运动": "Sport Club", "Cosplay": "Masquerade", "微醺": "Tipsy Hour", "户外": "Wilderness", "学院风": "Academia", "内衣私房": "Boudoir",
    "丝袜": "Silk & Sheer", "OOTD": "Outfit of the Day", "POV": "Point of View", "城市日常": "City Days", "游戏": "Play", "其他": "Miscellany", "偏殿": "Side Chambers" };
  const GLOW = ["rgba(216,184,120,.09)", "rgba(185,227,220,.07)", "rgba(200,184,255,.08)", "rgba(243,196,166,.08)"];
  // editorial rows: counts cycle 2-3-4-3; never leave a lonely single at the end
  function rowsOf(list) {
    const CYCLE = [2, 3, 4, 3]; const rows = []; let i = 0, c = 0;
    while (i < list.length) {
      let n = CYCLE[c++ % CYCLE.length]; const left = list.length - i;
      if (left - n === 1) n = left <= 4 ? left : n - 1;
      if (n > left) n = left;
      rows.push(list.slice(i, i + n)); i += n;
    }
    return rows;
  }

  let CFG = null, DATA = null, ALL = [], NO = new Map(), HALLS = [];
  const SORTS = { new: "最新发布", hot: "最高曝光", likes: "最多点赞", bookmarks: "最多收藏", old: "最早发布" };
  const FEATURED = { new: "最新之作", hot: "镇殿之作", likes: "最多点赞", bookmarks: "最多收藏", old: "最早之作" };
  const NEVER_CAT = new Set(["其他", "偏殿", "韩书允", "林知夏", "姜宥娜"]);
  // hall mode: archiveSort is unused; halls themselves stay ordered by impressions (hot)
  let siteSort = null, flatFilter = null, flatView = [];
  let archiveSort = "hot"; // comparator used inside halls (镇殿之作) and when a sort is chosen
  let ctx = { list: [], label: "" }, cur = -1, img = 0, lastFocus = null, navToken = 0;
  let locks = 0;
  let refreshSorter = () => {};
  const lock = () => { if (++locks === 1) document.body.classList.add("lock"); refreshSorter(); };
  const unlock = () => { locks = Math.max(0, locks - 1); if (!locks) document.body.classList.remove("lock"); refreshSorter(); };

  // ---------- build halls
  const categoryOf = (p) => {
    const c = p.category;
    if (c && !NEVER_CAT.has(c)) return c;
    const ser = (p.series || []).find((s) => !NEVER_CAT.has(s));
    return ser || "城市日常";
  };
  function buildHalls() {
    const order = DATA.category_order || [];
    const groups = new Map();
    ALL.forEach((p) => {
      const prim = categoryOf(p);
      p.category = prim;
      if (!groups.has(prim)) groups.set(prim, []);
      groups.get(prim).push(p);
    });
    // Keep any hall listed in category_order (overrides may hold a hall under 3 works).
    // Defensive: leftover tiny groups *not* in the official order still fold into 城市日常.
    const halls = [];
    const spill = [];
    for (const [name, posts] of groups) {
      if (order.includes(name) || posts.length >= 3) halls.push({ name, posts });
      else spill.push(...posts);
    }
    if (spill.length) {
      const daily = halls.find((h) => h.name === "城市日常");
      if (daily) daily.posts.push(...spill);
      else if (spill.length >= 3) halls.push({ name: "城市日常", posts: spill });
      else if (halls[0]) halls[0].posts.push(...spill);
    }
    const rank = (n) => { const i = order.indexOf(n); return i < 0 ? 500 : i; };
    halls.sort((a, b) => rank(a.name) - rank(b.name));
    const keep = archiveSort;
    archiveSort = "hot"; // halls always open with 镇殿之作 = 最高曝光
    halls.forEach((h, i) => {
      h.posts = sortPosts(h.posts);
      h.id = "hall-" + (i + 1); h.roman = ROMAN[i + 1] || String(i + 1); h.en = EN[h.name] || h.name;
      h.label = "系列殿 · Series";
    });
    archiveSort = keep;
    HALLS = halls;
  }

  const workHTML = (p, i, cls = "") => {
    const t = esc(titleOf(p)); const n = p.images.length; const no = pad3(NO.get(p.id));
    const img = `<img src="${esc(thumbOf(p))}" alt="${t}" loading="lazy" decoding="async"${dims(p)}>`;
    const tab = n > 1 ? `<span class="tab-count">${n} 张</span>` : "";
    const plaque = `<span class="plaque"><span class="work-no">Nº ${no}</span></span>`;
    return `<button type="button" class="work rv ${cls}" data-id="${p.id}" data-i="${i}" aria-label="Nº ${no} ${t}">
      ${relic(img, { tab, plaque })}
      <span class="work-title">${t}</span></button>`;
  };

  function renderCover() {
    // site.config.json "cover_id" pins the cover; otherwise the most-viewed recent portrait, preferring a less revealing one
    const REVEALING = ["丝袜", "内衣私房", "泳装"];
    const byViews = (a, b) => (b.metrics.impressions || 0) - (a.metrics.impressions || 0);
    const recent = ALL.slice(0, 12).filter((p) => { const m = p.media[0] || {}; return !m.w || m.h / m.w >= 1.2; });
    const modest = recent.filter((p) => !p.series.some((s) => REVEALING.includes(s)));
    const pinned = CFG && CFG.cover_id ? ALL.find((p) => p.id === String(CFG.cover_id)) : null;
    const hero = pinned || (modest.length ? modest : recent.length ? recent : ALL).slice().sort(byViews)[0];
    document.documentElement.dataset.cover = hero ? hero.id : "";
    if (!hero) return;
    const im = $("#coverImg");
    const m = (hero.media && hero.media[0]) || {};
    if (m.w && m.h) { im.width = m.w; im.height = m.h; }
    im.onload = fitCover;
    im.src = hero.images[0]; im.alt = titleOf(hero);
    if (im.complete) fitCover();
    requestAnimationFrame(() => requestAnimationFrame(fitCover));
    $("#coverBtn").onclick = () => {
      const hall = HALLS.find((h) => h.posts.some((q) => q.id === hero.id));
      const list = hall ? hall.posts : ALL;
      openViewer(list, list.findIndex((q) => q.id === hero.id), 0, hall ? `Hall ${hall.roman} · ${hall.name}` : "封面", $("#coverBtn"));
    };
  }

  function renderProfile() {
    const P = DATA.profile || {};
    if (P.name) { $("#name").textContent = P.name; const ln = $("#letterName"); if (ln) ln.textContent = P.name; }
    if (P.bio) { const b = $("#bio"); if (b) b.textContent = P.bio; }
    if (P.avatar) { $("#avatar").src = P.avatar; const la = $("#letterAvatar"); if (la) la.src = P.avatar; }
    if (P.username) {
      const href = P.url || "https://x.com/" + P.username;
      $("#handle").textContent = "@" + P.username; $("#handle").href = href;
      const lh = $("#letterHandle"); if (lh) { lh.textContent = "@" + P.username; lh.href = href; }
    }
    const imgs = ALL.reduce((s, p) => s + p.images.length, 0);
    $("#stats").innerHTML = [["作品", ALL.length], ["图片", imgs], ["关注者", P.followers]]
      .filter(([, v]) => v != null).map(([l, v]) => `<div><b>${fmt(v)}</b>${l}</div>`).join("");
    $("#updated").textContent = fmtDate(DATA.last_updated, true);
    $("#updated").dateTime = DATA.last_updated;
  }

  function renderAtrium() {
    $("#arches").innerHTML = HALLS.map((h) => {
      const img = `<img src="${esc(thumbOf(h.posts[0]))}" alt="" loading="lazy" decoding="async"${dims(h.posts[0])}>`;
      const plaque = `<span class="plaque"><span class="arch-r">${h.roman}</span></span>`;
      return `<a class="arch rv" href="#${h.id}">
        ${relic(img, { plaque, cls: "relic-arch" })}
        <span class="arch-name">${esc(h.name)}</span><span class="arch-en">${esc(h.en)}</span><span class="arch-c">${h.posts.length} 件</span></a>`;
    }).join("");
    renderRail();
  }

  function renderHalls() {
    $("#halls").innerHTML = HALLS.map((h, hi) => {
      const top = h.posts[0]; const rest = h.posts.slice(1);
      const likes = h.posts.reduce((s, p) => s + (p.metrics.likes || 0), 0);
      const imps = h.posts.reduce((s, p) => s + (p.metrics.impressions || 0), 0);
      return `<section class="hall" id="${h.id}" data-h="${hi}" style="--glow:${GLOW[hi % GLOW.length]}" aria-labelledby="${h.id}-t">
        <header class="hall-head">
          <span class="hall-num" aria-hidden="true">${h.roman}</span>
          <p class="hall-kicker">Hall ${h.roman} · ${h.label}</p>
          <h2 class="hall-title" id="${h.id}-t">${esc(h.name)}</h2>
          <p class="hall-en iris">${esc(h.en)}</p>
          <p class="hall-count">${h.posts.length} 件作品 · ${h.posts.reduce((s, p) => s + p.images.length, 0)} 张图</p>
        </header>
        <div class="colossus">
          <p class="side-note l rv"><b>${fmt(imps)}</b>本殿累计曝光</p>
          <div class="colossus-core">
            <button type="button" class="colossus-frame" data-id="${top.id}" data-i="0" aria-label="Nº ${pad3(NO.get(top.id))} ${esc(titleOf(top))}">
              ${relic(`<img src="${esc(top.images[0])}" alt="${esc(titleOf(top))}" loading="lazy" decoding="async"${dims(top)}>`, {
                cls: "relic-hero",
                tab: top.images.length > 1 ? `<span class="tab-count">${top.images.length} 张</span>` : "",
                plaque: `<span class="plaque"><span class="work-no">Nº ${pad3(NO.get(top.id))}</span></span>`
              })}
              <span class="hero-cap">
                <span class="hero-kicker">${esc(FEATURED[archiveSort] || "镇殿之作")}</span>
                <span class="hero-title">${esc(titleOf(top))}</span>
                <span class="hero-meta">${fmtDate(top.created_at)} · 曝光 ${fmt(top.metrics.impressions)}</span>
              </span>
            </button>
          </div>
          <p class="side-note r rv"><b>${fmt(likes)}</b>本殿累计点赞</p>
        </div>
        ${rest.length ? `<div class="gallery">${(() => { let k = 0; return rowsOf(rest).map((row) => `<div class="g-row r${row.length}">${row.map((p) => workHTML(p, ++k)).join("")}</div>`).join(""); })()}</div>` : ""}
      </section>`;
    }).join("");
  }

  // ---------- archive (all works, filter + sort; guarantees every work is reachable)
  function sortPosts(list) {
    const k = { hot: "impressions", likes: "likes", bookmarks: "bookmarks" }[archiveSort];
    return list.slice().sort((a, b) => archiveSort === "old" ? -newest(a, b) : k ? (b.metrics[k] || 0) - (a.metrics[k] || 0) || newest(a, b) : newest(a, b));
  }
  function isFlat() { return !!siteSort; }
  function renderRail() {
    const nav = $("#railNav"); if (!nav) return;
    const allOn = isFlat() && !flatFilter;
    nav.innerHTML = (isFlat() ? `<a href="#flat" class="rail-all${allOn ? " on" : ""}" data-rail="*">全部<span>${ALL.length}</span></a>` : "")
      + HALLS.map((h) => `<a href="#${h.id}" data-rail="${esc(h.name)}" class="${isFlat() && flatFilter === h.name ? "on" : ""}"><em>${h.roman}</em><b>${esc(h.name)}</b><i>${esc(h.en)}</i><span>${h.posts.length}</span></a>`).join("");
  }
  function setRailCurrent(id) {
    document.querySelectorAll("#railNav a[href^='#hall']").forEach((a) => a.classList.toggle("current", a.getAttribute("href") === "#" + id));
  }
  function renderFlat() {
    const list = sortPosts(ALL.filter((p) => !flatFilter || p.category === flatFilter));
    flatView = list;
    const el = $("#flat"), empty = $("#empty"), grid = $("#grid"), title = $("#flatTitle");
    if (!el) return;
    const sortLabel = SORTS[siteSort] || "";
    const filterLabel = flatFilter || "全部作品";
    if (title) title.textContent = flatFilter ? `${flatFilter} · ${sortLabel}` : `全部作品 · ${sortLabel}`;
    empty.hidden = list.length > 0;
    grid.innerHTML = list.map((p, i) => workHTML(p, i)).join("");
    observe(grid);
  }
  function enterFlat(id) {
    if (!SORTS[id]) return;
    siteSort = id;
    archiveSort = id;
    document.body.classList.add("flat-mode");
    const atrium = $("#atrium"), halls = $("#halls"), flat = $("#flat"), cancel = $("#sortCancel");
    if (atrium) atrium.hidden = true;
    if (halls) halls.hidden = true;
    if (flat) flat.hidden = false;
    if (cancel) cancel.hidden = false;
    renderFlat();
    renderRail();
    syncSortUI();
    closeSorter();
    const target = $("#flat");
    if (target) target.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
  }
  function leaveFlat() {
    siteSort = null;
    flatFilter = null;
    archiveSort = "hot";
    document.body.classList.remove("flat-mode");
    const atrium = $("#atrium"), halls = $("#halls"), flat = $("#flat"), cancel = $("#sortCancel");
    if (atrium) atrium.hidden = false;
    if (halls) halls.hidden = false;
    if (flat) flat.hidden = true;
    if (cancel) cancel.hidden = true;
    syncSortUI();
    closeSorter();
    renderRail();
    // halls still in 最高曝光 order from build; just re-observe
    observe($("#halls"));
    observe($("#arches"));
    const t = $("#atrium");
    if (t) t.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
  }
  function syncSortUI() {
    const now = $("#sorterNow");
    if (now) now.textContent = siteSort ? SORTS[siteSort] : "殿堂";
    document.querySelectorAll("#sorterMenu [data-sort]").forEach((b) => b.setAttribute("aria-selected", b.dataset.sort === siteSort ? "true" : "false"));
  }
  function closeSorter() {
    const menu = $("#sorterMenu"), btn = $("#sorterBtn");
    if (!menu || menu.hidden) return;
    menu.hidden = true;
    if (btn) btn.setAttribute("aria-expanded", "false");
    requestAnimationFrame(syncDock);
  }
  function applySort(id) { enterFlat(id); }

  // ---------- prompt typography (display only; copy uses the raw prompt)
  function promptHTML(t) {
    const out = [];
    const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\*\*/g, "");
    t.replace(/\r/g, "").split("\n").forEach((raw) => {
      const line = raw.trim(); if (!line) return;
      const md = line.replace(/^#+\s*/, "").replace(/\*\*/g, "").replace(/^【(.+)】$/, "$1").trim();
      const pure = md.match(/^([^，。,.!！?？]{1,16})[：:]$/);
      if (pure || (/^#+\s|^【.+】$|^\*\*.+\*\*$/.test(line) && md.length <= 24)) { out.push(`<h4>${esc(pure ? pure[1] : md)}</h4>`); return; }
      const kv = md.match(/^([^，。,.：:]{1,8})[：:]\s*(.+)$/);
      if (kv && HEAD_WORDS.test(kv[1].trim())) { out.push(`<h4>${esc(kv[1].trim())}</h4><p>${esc(kv[2])}</p>`); return; }
      out.push(`<p>${inline(line.replace(/^#+\s*/, ""))}</p>`);
    });
    // drop cap only for a CJK first character (never split a Latin word or number)
    if (out[0] && out[0].startsWith("<p>") && /^<p>[\u3400-\u9fff]/.test(out[0])) out[0] = out[0].replace("<p>", '<p class="dc">');
    return out.join("");
  }

  // ---------- viewer
  const lb = $("#lb");
  function openViewer(list, i, k = 0, label = "", from = null) {
    if (!list[i]) return;
    ctx = { list, label }; lastFocus = from || document.activeElement;
    const wasOpen = !lb.hidden;
    lb.hidden = false; if (!wasOpen) { lock(); lb.classList.remove("opening"); void lb.offsetWidth; if (!reduced) lb.classList.add("opening"); }
    show(i, k, 0);
    if (!wasOpen) setTimeout(() => $("#lbClose").focus({ preventScroll: true }), 30);
  }
  function show(i, k, dir) {
    cur = i; img = k; const p = ctx.list[i];
    $("#vNo").textContent = "Nº " + pad3(NO.get(p.id));
    $("#vPos").textContent = `${i + 1} / ${ctx.list.length}`;
    $("#vHall").textContent = ctx.label;
    $("#lbDate").textContent = fmtDate(p.created_at, true) + "（上海时间）";
    $("#lbCaption").textContent = titleOf(p);
    const fullCap = captionText(p); const vc = $("#vCaption");
    vc.textContent = fullCap; vc.hidden = !fullCap || fullCap.replace(/\s+/g, "") === titleOf(p).replace(/\s+/g, "");
    $("#lbTags").innerHTML = p.series.map((s) => `<span>${esc(s)}</span>`).join("");
    const M = p.metrics;
    $("#lbMetrics").innerHTML = [["曝光", M.impressions], ["点赞", M.likes], ["收藏", M.bookmarks]].map(([l, v]) => `<div><b>${fmt(v)}</b>${l}</div>`).join("");
    $("#lbPrompt").innerHTML = promptHTML(p.prompt || ""); $("#lbPrompt").classList.remove("sel");
    $("#lbPromptWrap").hidden = !p.prompt;
    resetCopy();
    $("#lbLink").href = p.url;
    history.replaceState(null, "", "#p=" + p.id);
    const panel = $("#vPanel"); panel.scrollTop = 0;
    if (!reduced && dir) [...panel.children].forEach((c) => { c.style.animation = "none"; void c.offsetWidth; c.style.animation = ""; });
    showImg(dir);
  }
  function showImg(dir) {
    const p = ctx.list[cur]; const el = $("#lbImg"); const tok = ++navToken; const src = p.images[img];
    $("#vAmbient").style.backgroundImage = `url("${thumbOf(p, img)}")`;
    $("#lbDots").innerHTML = p.images.length > 1 ? p.images.map((_, k) => `<button class="${k === img ? "on" : ""}" data-k="${k}" aria-label="第 ${k + 1} 张"></button>`).join("") + `<span>${img + 1}/${p.images.length}</span>` : "";
    $("#lbPrev").disabled = cur === 0 && img === 0;
    $("#lbNext").disabled = cur === ctx.list.length - 1 && img === p.images.length - 1;
    const swap = () => {
      if (tok !== navToken) return;
      el.classList.add("loading");
      const well = el.closest(".well"); if (well) well.classList.remove("is-broken");
      const media = (p.media && p.media[img]) || {};
      if (media.w && media.h) { el.width = media.w; el.height = media.h; }
      el.onload = () => {
        if (tok !== navToken) return;
        el.classList.remove("loading");
        fitLb();
        if (dir && !reduced) { el.classList.add("pre"); void el.offsetWidth; el.classList.remove("pre", "out"); } else el.classList.remove("out");
        requestAnimationFrame(fitLb);
      };
      el.onerror = () => { el.classList.remove("loading", "out"); if (well) well.classList.add("is-broken"); };
      el.src = src; el.alt = titleOf(p);
      if (el.complete && el.naturalWidth) { el.classList.remove("loading"); fitLb(); }
    };
    lb.style.setProperty("--dir", dir < 0 ? -1 : 1);
    if (dir && !reduced && el.getAttribute("src")) { el.classList.add("out"); setTimeout(swap, 260); } else swap();
    const L = ctx.list; [L[cur + 1], L[cur - 1]].forEach((q) => { if (q) new Image().src = q.images[0]; });
    if (p.images[img + 1]) new Image().src = p.images[img + 1];
  }
  function step(d) {
    if (cur < 0) return;
    const p = ctx.list[cur];
    if (img + d >= 0 && img + d < p.images.length) { img += d; showImg(d); return; }
    const n = cur + d; if (n < 0 || n >= ctx.list.length) return;
    show(n, d < 0 ? ctx.list[n].images.length - 1 : 0, d);
  }
  function closeViewer() {
    if (lb.hidden) return;
    lb.hidden = true; cur = -1; unlock();
    history.replaceState(null, "", location.pathname + location.search);
    if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  }

  let toastT;
  function toast(t, err) { const el = $("#toast"); el.textContent = t; el.classList.toggle("err", !!err); el.classList.add("show"); clearTimeout(toastT); toastT = setTimeout(() => el.classList.remove("show"), 2600); }
  let copyT;
  function resetCopy() { clearTimeout(copyT); const b = $("#lbCopy"); b.classList.remove("ok", "err"); $(".v-copy-label", b).textContent = "复制提示词"; }
  async function copyPrompt() {
    const p = ctx.list[cur]; if (!p || !p.prompt) return;
    const t = p.prompt; let ok = false;
    try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(t); ok = true; } } catch { ok = false; }
    if (!ok) {
      try {
        const ta = document.createElement("textarea");
        ta.value = t; ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;top:0;left:0;opacity:0";
        document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, t.length);
        ok = document.execCommand("copy"); ta.remove();
      } catch { ok = false; }
    }
    const b = $("#lbCopy"); clearTimeout(copyT);
    if (ok) {
      b.classList.remove("err"); b.classList.add("ok"); $(".v-copy-label", b).textContent = "已复制 ✓";
      toast("提示词已复制到剪贴板");
    } else {
      b.classList.remove("ok"); b.classList.add("err"); $(".v-copy-label", b).textContent = "复制失败";
      const body = $("#lbPrompt"); body.classList.add("sel");
      const r = document.createRange(); r.selectNodeContents(body); const s = getSelection(); s.removeAllRanges(); s.addRange(r);
      toast("复制失败：已选中提示词，请长按或 Ctrl+C 手动复制", true);
    }
    copyT = setTimeout(resetCopy, 2600);
  }

  // ---------- gate (site.config.json adult_notice)
  const GATE_DEFAULT = { adult_notice: true, adult_notice_text: "本站包含 AI 生成的成人时尚写真（均为虚构成年模特，无裸露）。请确认你已年满 18 岁后继续浏览。", adult_notice_confirm: "我已年满 18 岁，进入", adult_notice_leave: "离开" };
  function gate(cfg) {
    // Show unless adult_notice is explicitly false. Missing, unreadable, or {} still fail closed.
    if (cfg && cfg.adult_notice === false) return;
    cfg = Object.assign({}, GATE_DEFAULT, cfg || {});
    $("#gateText").textContent = cfg.adult_notice_text || "";
    $("#gateYes").textContent = cfg.adult_notice_confirm || "进入";
    $("#gateNo").textContent = cfg.adult_notice_leave || "离开";
    const g = $("#gate"); g.hidden = false; lock();
    setTimeout(() => $("#gateYes").focus(), 50);
    $("#gateYes").onclick = () => {
      if (reduced) { g.hidden = true; unlock(); return; }
      g.classList.add("opening"); setTimeout(() => { g.hidden = true; unlock(); }, 740);
    };
  }

  // ---------- motion: reveal, parallax, bar
  let io;
  function observe(root) {
    const els = root.querySelectorAll(".rv:not(.in)");
    if (reduced || !("IntersectionObserver" in window)) { els.forEach((e) => e.classList.add("in")); return; }
    if (!io) io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -6% 0px", threshold: .08 });
    els.forEach((e) => io.observe(e));
  }
  function syncDock() {
    const bar = $("#bar");
    if (!bar) return;
    const next = Math.ceil(bar.getBoundingClientRect().height) + "px";
    const cur = document.documentElement.style.getPropertyValue("--dock");
    if (cur !== next) {
      document.documentElement.style.setProperty("--dock", next);
      requestAnimationFrame(fitCover);
    }
  }
  function watchSorter() {
    const cover = $("#cover"), el = $("#sorter"), scroller = document.querySelector("main");
    if (!cover || !el) return;
    const apply = () => {
      const past = !!(scroller && scroller.scrollTop > cover.offsetHeight * 0.62);
      document.body.classList.toggle("past-cover", past);
      const locked = document.body.classList.contains("lock");
      el.setAttribute("aria-hidden", locked ? "true" : "false");
      if (locked) closeSorter();
    };
    refreshSorter = apply;
    if (scroller) scroller.addEventListener("scroll", apply, { passive: true });
    apply();
  }
  function motion() {
    const scroller = document.querySelector("main");
    watchSorter();
    syncDock();
    let ticking = false;
    const updateRailCurrent = () => {
      if (isFlat()) return;
      const spine = innerHeight * 0.38;
      let best = null, score = -1;
      document.querySelectorAll(".hall").forEach((h) => {
        const r = h.getBoundingClientRect();
        if (r.bottom <= 80 || r.top >= innerHeight) return;
        const vis = Math.min(r.bottom, innerHeight) - Math.max(r.top, 80);
        const onSpine = r.top <= spine && r.bottom > spine;
        const s = (onSpine ? 1e6 : 0) + vis;
        if (s > score) { score = s; best = h.id; }
      });
      if (best) setRailCurrent(best);
    };
    const frame = () => {
      ticking = false;
      syncDock();
      updateRailCurrent();
    };
    const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(frame); } };
    (scroller || window).addEventListener("scroll", onScroll, { passive: true });
    addEventListener("resize", () => { syncDock(); fitCover(); fitLb(); frame(); });
    frame();
  }

  // Fine-pointer ring only. Native cursor stays; the node never receives hits.
  function mountNeedle() {
    if (reduced) return;
    const fine = matchMedia("(hover: hover) and (pointer: fine)");
    if (!fine.matches) return;
    const n = document.createElement("div");
    n.className = "needle";
    n.setAttribute("aria-hidden", "true");
    document.body.appendChild(n);
    let raf = 0, x = 0, y = 0;
    const paint = () => { raf = 0; n.style.transform = `translate3d(${x}px,${y}px,0)`; };
    const hide = () => n.classList.remove("on");
    const allowed = (e) => fine.matches && (!e.pointerType || e.pointerType === "mouse" || e.pointerType === "pen");
    addEventListener("pointermove", (e) => {
      if (!allowed(e)) { hide(); return; }
      x = e.clientX; y = e.clientY; n.classList.add("on");
      if (!raf) raf = requestAnimationFrame(paint);
    }, { passive: true });
    addEventListener("pointerdown", (e) => { if (!allowed(e)) hide(); }, { passive: true });
    addEventListener("pointerout", (e) => { if (!e.relatedTarget) hide(); });
    addEventListener("blur", hide);
  }

  // ---------- events
  function bind() {
    const ar = $("#arches"), ap = $("#archPrev"), an = $("#archNext");
    const archState = () => { const max = ar.scrollWidth - ar.clientWidth - 2; ap.disabled = ar.scrollLeft <= 2; an.disabled = ar.scrollLeft >= max; };
    const archGo = (d) => ar.scrollBy({ left: d * ar.clientWidth * .7, behavior: reduced ? "auto" : "smooth" });
    ap.onclick = () => archGo(-1); an.onclick = () => archGo(1);
    ar.addEventListener("scroll", archState, { passive: true }); addEventListener("resize", archState); archState();
    const listFor = (el) => {
      if (isFlat() || el.closest("#flat")) {
        const label = "全部 · " + (SORTS[siteSort] || "") + (flatFilter ? " · " + flatFilter : "");
        return [flatView, label];
      }
      const hall = el.closest(".hall");
      if (hall) { const h = HALLS[+hall.dataset.h]; return [h.posts, `Hall ${h.roman} · ${h.name}`]; }
      return [ALL, "作品"];
    };
    const rail = $("#rail"), mask = $("#railMask"), railOpen = $("#railOpen"), tocBtn = $("#tocBtn");
    const railOpenState = () => document.body.classList.contains("is-rail");
    const setRailOpen = (open) => {
      document.body.classList.toggle("is-rail", open);
      if (railOpen) railOpen.setAttribute("aria-expanded", open ? "true" : "false");
      if (tocBtn) tocBtn.setAttribute("aria-expanded", open ? "true" : "false");
      if (mask) mask.hidden = !open;
    };
    const toggleRail = () => setRailOpen(!railOpenState());
    if (railOpen) railOpen.addEventListener("click", (e) => { e.stopPropagation(); toggleRail(); });
    if (tocBtn) tocBtn.addEventListener("click", (e) => { e.stopPropagation(); toggleRail(); });
    if (mask) mask.addEventListener("click", () => setRailOpen(false));
    if (rail) rail.addEventListener("click", (e) => {
      const a = e.target.closest("a[data-rail]");
      if (!a) {
        if (e.target.closest(".rail-home")) setRailOpen(false);
        return;
      }
      if (isFlat()) {
        e.preventDefault();
        const v = a.dataset.rail;
        flatFilter = v === "*" ? null : v;
        renderFlat();
        renderRail();
        setRailOpen(false);
        const target = $("#flat");
        if (target) target.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
      } else {
        setRailOpen(false);
      }
    });
    document.addEventListener("click", (e) => {
      const w = e.target.closest(".work, .colossus-frame");
      if (w) { const [list, label] = listFor(w); openViewer(list, +w.dataset.i, 0, label, w); return; }
    });
    const sorterBtn = $("#sorterBtn"), sorterMenu = $("#sorterMenu");
    sorterBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = sorterMenu.hidden;
      sorterMenu.hidden = !open;
      sorterBtn.setAttribute("aria-expanded", open ? "true" : "false");
      requestAnimationFrame(syncDock);
    });
    sorterMenu.addEventListener("click", (e) => {
      const b = e.target.closest("[data-sort]"); if (!b) return;
      applySort(b.dataset.sort);
    });
    const cancel = $("#sortCancel");
    if (cancel) cancel.addEventListener("click", (e) => { e.stopPropagation(); leaveFlat(); });
    document.addEventListener("click", (e) => { if (!e.target.closest("#sorter")) closeSorter(); });
    addEventListener("keydown", (e) => {
      if (e.key === "Escape") { closeSorter(); setRailOpen(false); }
    });
    $("#lbClose").onclick = closeViewer; $("#lbPrev").onclick = () => step(-1); $("#lbNext").onclick = () => step(1);
    $("#lbCopy").onclick = copyPrompt;
    $("#lbDots").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { const k = +b.dataset.k; const d = k > img ? 1 : -1; img = k; showImg(d); } });
    $("#lbStage").addEventListener("click", (e) => {
      if (e.target.closest(".relic, .v-nav, .v-dots")) return;
      closeViewer();
    });
    const focusables = (root) => [...root.querySelectorAll("a[href], button, input, textarea, select")].filter((n) => !n.disabled && n.getClientRects().length);
    addEventListener("keydown", (e) => {
      if (e.key !== "Tab") return;
      const g = $("#gate");
      const root = g && !g.hidden ? g : !lb.hidden ? lb : null;
      if (!root) return;
      const nodes = focusables(root);
      if (!nodes.length) return;
      const first = nodes[0], last = nodes[nodes.length - 1];
      if (!root.contains(document.activeElement)) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
        return;
      }
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    addEventListener("keydown", (e) => {
      if (lb.hidden) return;
      if (e.key === "Escape") closeViewer(); else if (e.key === "ArrowRight") { e.preventDefault(); step(1); } else if (e.key === "ArrowLeft") { e.preventDefault(); step(-1); }
    });
    document.addEventListener("error", (ev) => {
      const t = ev.target;
      if (!t || t.tagName !== "IMG") return;
      const well = t.closest(".well");
      if (well) well.classList.add("is-broken");
    }, true);
    mountNeedle();
    let sx = null, sy = null;
    const st = $("#lbStage");
    st.addEventListener("touchstart", (e) => { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
    st.addEventListener("touchend", (e) => {
      if (sx == null) return; const dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
      if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.3) step(dx < 0 ? 1 : -1); sx = sy = null;
    }, { passive: true });
  }

  const cfgP = fetch("site.config.json", { cache: "no-cache" }).then((r) => r.ok ? r.json() : null).catch(() => null)
    .then((c) => { CFG = c && typeof c === "object" ? c : null; gate(CFG); return CFG; });
  Promise.all([cfgP, fetch("data/posts.json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error("posts.json " + r.status); return r.json(); })]).then(([, d]) => {
    DATA = d;
    ALL = (d.posts || []).filter((p) => p && p.id && p.images && p.images.length).map((p) => ({ ...p, series: p.series || [], metrics: p.metrics || {} })).sort(newest);
    ALL.slice().reverse().forEach((p, i) => NO.set(p.id, i + 1));
    buildHalls(); renderProfile(); renderCover(); renderAtrium(); renderHalls(); syncSortUI(); bind();
    observe(document); motion();
    const m = location.hash.match(/p=(\d+)/);
    if (m) {
      const hall = HALLS.find((h) => h.posts.some((q) => q.id === m[1]));
      const list = hall ? hall.posts : ALL;
      const i = list.findIndex((p) => p.id === m[1]);
      if (i >= 0) openViewer(list, i, 0, hall ? `Hall ${hall.roman} · ${hall.name}` : "作品");
    } else if (/^#hall-\d+$/.test(location.hash)) { const t = $(location.hash); if (t) t.scrollIntoView(); }
  }).catch((e) => { console.error(e); $("#empty").hidden = false; $("#empty").textContent = "作品数据加载失败，请稍后刷新。"; });
})();
