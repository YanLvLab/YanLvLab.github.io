/* HARA · 巨人殿 — vanilla JS, reads data/posts.json (already filtered by update.py / hidden.json). */
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
  let archiveFilter = "全部", archiveSort = "new", archiveView = [];
  let ctx = { list: [], label: "" }, cur = -1, img = 0, lastFocus = null, navToken = 0;
  let locks = 0;
  const lock = () => { if (++locks === 1) document.body.classList.add("lock"); };
  const unlock = () => { locks = Math.max(0, locks - 1); if (!locks) document.body.classList.remove("lock"); };

  // ---------- build halls
  function buildHalls() {
    const order = DATA.series_order || [];
    const groups = new Map();
    const charOf = (p) => (p.series || []).find((s) => CHARACTERS.includes(s)) || CHARACTERS.find((c) => (p.text || "").includes(c));
    const charCount = {};
    ALL.forEach((p) => { const c = charOf(p); if (c) charCount[c] = (charCount[c] || 0) + 1; });
    ALL.forEach((p) => {
      const ser = (p.series || []).filter((s) => !CHARACTERS.includes(s));
      const c = charOf(p);
      const prim = c && charCount[c] >= 3 ? c : ser[0] || "其他"; // a character hall needs at least 3 works
      if (!groups.has(prim)) groups.set(prim, []);
      groups.get(prim).push(p);
    });
    const side = [];
    const halls = [];
    for (const [name, posts] of groups) {
      if (posts.length < 3 && name !== "其他") side.push(...posts);
      else halls.push({ name, posts });
    }
    if (side.length) {
      const misc = halls.find((h) => h.name === "其他");
      if (misc) { misc.posts.push(...side); misc.name = "偏殿"; misc.merged = true; }
      else halls.push({ name: "偏殿", posts: side, merged: true });
    }
    const rank = (n) => CHARACTERS.includes(n) ? -10 + CHARACTERS.indexOf(n) : n === "偏殿" ? 999 : (order.indexOf(n) < 0 ? 500 : order.indexOf(n));
    halls.sort((a, b) => rank(a.name) - rank(b.name));
    halls.forEach((h, i) => {
      h.posts.sort((a, b) => (b.metrics.impressions || 0) - (a.metrics.impressions || 0) || newest(a, b));
      h.id = "hall-" + (i + 1); h.roman = ROMAN[i + 1] || String(i + 1); h.en = EN[h.name] || h.name;
      h.label = CHARACTERS.includes(h.name) ? "人物殿 · Character" : h.merged ? "偏殿 · Lesser Halls" : "系列殿 · Series";
    });
    HALLS = halls;
  }

  const workHTML = (p, i, cls = "") => {
    const t = esc(titleOf(p)); const n = p.images.length;
    return `<button type="button" class="work rv ${cls}" data-id="${p.id}" data-i="${i}" aria-label="${t}">
      <img src="${esc(thumbOf(p))}" alt="${t}" loading="lazy" decoding="async" width="720" height="900">
      ${n > 1 ? `<span class="work-multi">${n} 张</span>` : ""}
      <span class="work-meta"><span class="work-no">Nº ${pad3(NO.get(p.id))}</span><span class="work-title">${t}</span></span></button>`;
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
    const im = $("#coverImg"); im.src = hero.images[0]; im.alt = titleOf(hero);
    $("#coverBtn").onclick = () => openViewer(ALL, ALL.indexOf(hero), 0, "封面", $("#coverBtn"));
    $("#coverCaption").innerHTML = `<b>COVER · Nº ${pad3(NO.get(hero.id))}</b>${esc(titleOf(hero))}`;
    const imgs = ALL.reduce((s, p) => s + p.images.length, 0);
    $("#coverStats").textContent = `${ALL.length} Works · ${imgs} Images · ${HALLS.length} Halls`;
    $("#issueDate").textContent = "Issue " + fmtDate(DATA.last_updated);
    $("#issueVol").textContent = "Vol. I · Nº " + pad3(ALL.length);
    const feats = HALLS.slice().sort((a, b) => b.posts.length - a.posts.length).slice(0, 3);
    $("#coverFeatures").innerHTML = `<p class="cl-kicker">Features</p>` + feats.map((h) =>
      `<a class="feat" href="#${h.id}" style="display:block;text-decoration:none"><em>HALL ${h.roman}</em><b>${esc(h.name)}</b><span>${esc(h.en)} · ${h.posts.length} works</span></a>`).join("");
  }

  function renderProfile() {
    const P = DATA.profile || {};
    if (P.name) $("#name").textContent = P.name;
    if (P.bio) $("#bio").textContent = P.bio;
    if (P.avatar) $("#avatar").src = P.avatar;
    if (P.username) { $("#handle").textContent = "@" + P.username; $("#handle").href = P.url || "https://x.com/" + P.username; }
    const imgs = ALL.reduce((s, p) => s + p.images.length, 0);
    $("#stats").innerHTML = [["作品", ALL.length], ["图片", imgs], ["关注者", P.followers]]
      .filter(([, v]) => v != null).map(([l, v]) => `<div><b>${fmt(v)}</b>${l}</div>`).join("");
    $("#updated").textContent = fmtDate(DATA.last_updated, true);
    $("#updated").dateTime = DATA.last_updated;
  }

  function renderAtrium() {
    $("#arches").innerHTML = HALLS.map((h) => `<a class="arch rv" href="#${h.id}">
      <span class="arch-door"><span class="arch-r">${h.roman}</span><img src="${esc(thumbOf(h.posts[0]))}" alt="" loading="lazy" decoding="async"></span>
      <span class="arch-name">${esc(h.name)}</span><span class="arch-en">${esc(h.en)}</span><span class="arch-c">${h.posts.length} WORKS</span></a>`).join("");
    $("#toc").innerHTML = HALLS.map((h) => `<a href="#${h.id}"><span class="r">${h.roman}</span><span class="n">${esc(h.name)}<i>${esc(h.en)}</i></span><span class="c">${h.posts.length}</span></a>`).join("")
      + `<a href="#archive"><span class="r">∞</span><span class="n">档案馆<i>The Archive</i></span><span class="c">${ALL.length}</span></a>`;
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
          <button type="button" class="colossus-frame" data-id="${top.id}" data-i="0" aria-label="${esc(titleOf(top))}">
            <img src="${esc(top.images[0])}" alt="${esc(titleOf(top))}" loading="lazy" decoding="async">
            <span class="plaque"><em>镇殿之作 · Nº ${pad3(NO.get(top.id))}</em><b>${esc(titleOf(top))}</b><span>${fmtDate(top.created_at)} · 曝光 ${fmt(top.metrics.impressions)}</span></span>
          </button>
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
  function renderChips() {
    const counts = {};
    ALL.forEach((p) => p.series.forEach((s) => counts[s] = (counts[s] || 0) + 1));
    const order = ["全部", ...(DATA.series_order || []).filter((s) => counts[s]), ...Object.keys(counts).filter((s) => !(DATA.series_order || []).includes(s))];
    $("#chips").innerHTML = order.map((s) =>
      `<button class="chip" role="tab" aria-selected="${s === archiveFilter}" data-s="${esc(s)}">${esc(s)}<small>${s === "全部" ? ALL.length : counts[s]}</small></button>`).join("");
  }
  function renderArchive() {
    archiveView = sortPosts(ALL.filter((p) => archiveFilter === "全部" || p.series.includes(archiveFilter)));
    $("#empty").hidden = archiveView.length > 0;
    $("#grid").innerHTML = archiveView.map((p, i) => workHTML(p, i)).join("");
    $("#archiveNote").textContent = `共 ${ALL.length} 件作品，每件都附提示词。当前显示 ${archiveView.length} 件。`;
    observe($("#grid"));
  }

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
    $("#lbTags").innerHTML = p.series.map((s) => `<a href="#archive" data-s="${esc(s)}">${esc(s)}</a>`).join("");
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
      el.onload = () => {
        if (tok !== navToken) return;
        el.classList.remove("loading");
        if (dir && !reduced) { el.classList.add("pre"); void el.offsetWidth; el.classList.remove("pre", "out"); } else el.classList.remove("out");
      };
      el.onerror = () => { el.classList.remove("loading", "out"); };
      el.src = src; el.alt = titleOf(p);
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
    cfg = cfg || GATE_DEFAULT; // config missing or unreadable: fail closed and still ask
    if (!cfg.adult_notice) return;
    try { if (localStorage.getItem("adult_ok") === "1") return; } catch {}
    $("#gateText").textContent = cfg.adult_notice_text || "";
    $("#gateYes").textContent = cfg.adult_notice_confirm || "进入";
    $("#gateNo").textContent = cfg.adult_notice_leave || "离开";
    const g = $("#gate"); g.hidden = false; lock();
    setTimeout(() => $("#gateYes").focus(), 50);
    $("#gateYes").onclick = () => {
      try { localStorage.setItem("adult_ok", "1"); } catch {}
      if (reduced) { g.hidden = true; unlock(); return; }
      g.classList.add("opening"); setTimeout(() => { g.hidden = true; unlock(); }, 1500);
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
  const live = new Set();
  function motion() {
    const bar = $("#bar"), cover = $("#cover"), fig = $("#coverFigure");
    if (!reduced && "IntersectionObserver" in window) {
      const pio = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting ? live.add(e.target) : live.delete(e.target)), { rootMargin: "20% 0px" });
      document.querySelectorAll(".colossus-frame").forEach((f) => pio.observe(f));
    }
    let ticking = false;
    const frame = () => {
      ticking = false;
      const y = scrollY, vh = innerHeight;
      bar.classList.toggle("on", y > cover.offsetHeight * .72);
      if (reduced) return;
      if (y < vh * 1.2) fig.style.setProperty("--cy", (y * .28).toFixed(1) + "px");
      live.forEach((f) => { const r = f.getBoundingClientRect(); const p = Math.min(1, Math.max(0, (vh - r.top) / (vh + r.height))); f.style.setProperty("--p", p.toFixed(4)); });
    };
    addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }, { passive: true });
    addEventListener("resize", frame);
    frame();
  }

  // ---------- events
  function bind() {
    const ar = $("#arches"), ap = $("#archPrev"), an = $("#archNext");
    const archState = () => { const max = ar.scrollWidth - ar.clientWidth - 2; ap.disabled = ar.scrollLeft <= 2; an.disabled = ar.scrollLeft >= max; };
    const archGo = (d) => ar.scrollBy({ left: d * ar.clientWidth * .7, behavior: reduced ? "auto" : "smooth" });
    ap.onclick = () => archGo(-1); an.onclick = () => archGo(1);
    ar.addEventListener("scroll", archState, { passive: true }); addEventListener("resize", archState); archState();
    const listFor = (el) => {
      const hall = el.closest(".hall");
      if (hall) { const h = HALLS[+hall.dataset.h]; return [h.posts, `Hall ${h.roman} · ${h.name}`]; }
      return [archiveView, "档案馆 · " + archiveFilter];
    };
    document.addEventListener("click", (e) => {
      const w = e.target.closest(".work, .colossus-frame");
      if (w) { const [list, label] = listFor(w); openViewer(list, +w.dataset.i, 0, label, w); return; }
      const toc = $("#toc");
      if (e.target.closest("#tocBtn")) { const open = toc.hidden; toc.hidden = !open; $("#tocBtn").setAttribute("aria-expanded", open); return; }
      if (!toc.hidden && !e.target.closest("#toc")) { toc.hidden = true; $("#tocBtn").setAttribute("aria-expanded", "false"); }
      if (e.target.closest("#toc a")) { toc.hidden = true; $("#tocBtn").setAttribute("aria-expanded", "false"); }
    });
    $("#chips").addEventListener("click", (e) => { const b = e.target.closest(".chip"); if (!b) return; archiveFilter = b.dataset.s; renderChips(); renderArchive(); });
    $("#sort").addEventListener("change", (e) => { archiveSort = e.target.value; renderArchive(); });
    $("#lbTags").addEventListener("click", (e) => {
      const a = e.target.closest("a[data-s]"); if (!a) return; e.preventDefault();
      archiveFilter = a.dataset.s; renderChips(); renderArchive(); closeViewer();
      $("#archive").scrollIntoView({ behavior: reduced ? "auto" : "smooth" });
    });
    $("#lbClose").onclick = closeViewer; $("#lbPrev").onclick = () => step(-1); $("#lbNext").onclick = () => step(1);
    $("#lbCopy").onclick = copyPrompt;
    $("#lbDots").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { const k = +b.dataset.k; const d = k > img ? 1 : -1; img = k; showImg(d); } });
    $("#lbStage").addEventListener("click", (e) => { if (e.target === e.currentTarget || e.target.id === "vFigure") closeViewer(); });
    addEventListener("keydown", (e) => {
      if (lb.hidden) { if (e.key === "Escape" && !$("#toc").hidden) { $("#toc").hidden = true; $("#tocBtn").setAttribute("aria-expanded", "false"); } return; }
      if (e.key === "Escape") closeViewer(); else if (e.key === "ArrowRight") { e.preventDefault(); step(1); } else if (e.key === "ArrowLeft") { e.preventDefault(); step(-1); }
    });
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
    buildHalls(); renderProfile(); renderCover(); renderAtrium(); renderHalls(); renderChips(); renderArchive(); bind();
    observe(document); motion();
    const m = location.hash.match(/p=(\d+)/);
    if (m) { const i = ALL.findIndex((p) => p.id === m[1]); if (i >= 0) openViewer(ALL, i, 0, "档案馆 · 全部"); }
    else if (/^#hall-\d+$/.test(location.hash)) { const t = $(location.hash); if (t) t.scrollIntoView(); }
  }).catch((e) => { console.error(e); $("#empty").hidden = false; $("#empty").textContent = "作品数据加载失败，请稍后刷新。"; });
})();
