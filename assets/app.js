(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const fmt = (n) => n == null ? "—" : n >= 10000 ? (n / 10000).toFixed(n >= 100000 ? 0 : 1) + "万" : n.toLocaleString("zh-CN");
  const fmtDate = (iso, withTime) => {
    const d = new Date(iso);
    const p = (x) => String(x).padStart(2, "0");
    // render in Asia/Shanghai regardless of the visitor's zone
    const s = new Date(d.getTime() + (d.getTimezoneOffset() + 480) * 60000);
    const day = `${s.getFullYear()}.${p(s.getMonth() + 1)}.${p(s.getDate())}`;
    return withTime ? `${day} ${p(s.getHours())}:${p(s.getMinutes())}` : day;
  };
  const titleOf = (p) => {
    const c = (p.caption || "").replace(/#\S+/g, "").trim();
    if (c) return c;
    const m = (p.prompt || "").replace(/^[#*\s]+/, "").match(/^[^\n。.]{1,40}/);
    return m ? m[0] : "无题";
  };

  let DATA = null, view = [], filter = "全部", sort = "new", cur = -1, img = 0;

  const state = { cols: 0 };
  const colCount = () => innerWidth < 560 ? 2 : innerWidth < 900 ? 3 : 4;

  function sortPosts(list) {
    const k = { hot: "impressions", likes: "likes", bookmarks: "bookmarks" }[sort];
    return list.slice().sort((a, b) =>
      sort === "old" ? a.id.localeCompare(b.id, "en", { numeric: true })
        : k ? (b.metrics[k] || 0) - (a.metrics[k] || 0)
        : b.id.localeCompare(a.id, "en", { numeric: true }));
  }

  function render() {
    const grid = $("#grid");
    view = sortPosts(DATA.posts.filter((p) => filter === "全部" || p.series.includes(filter)));
    $("#empty").hidden = view.length > 0;
    const n = colCount(); state.cols = n;
    const cols = Array.from({ length: n }, () => { const c = document.createElement("div"); c.className = "col"; return c; });
    const h = new Array(n).fill(0);
    view.forEach((p, i) => {
      const m = p.media[0] || {}; const ratio = (m.h && m.w) ? m.h / m.w : 1.5;
      const card = document.createElement("article");
      card.className = "card"; card.tabIndex = 0; card.dataset.i = i;
      card.style.animationDelay = Math.min(i, 24) * 35 + "ms";
      const title = titleOf(p);
      card.setAttribute("aria-label", title);
      card.innerHTML =
        `<img src="${p.thumbs[0]}" alt="${title.replace(/"/g, "&quot;")}" loading="lazy" decoding="async" width="${m.w || 720}" height="${m.h || 1080}">` +
        (p.images.length > 1 ? `<span class="badge">${p.images.length} 张</span>` : "") +
        `<span class="tag">${p.series[0]}</span>` +
        `<div class="meta"><p>${escapeHtml(title)}</p><span>${fmtDate(p.created_at)} · ♥ ${fmt(p.metrics.likes)} · 曝光 ${fmt(p.metrics.impressions)}</span></div>`;
      let j = h.indexOf(Math.min(...h)); cols[j].appendChild(card); h[j] += ratio;
    });
    grid.replaceChildren(...cols);
  }

  function escapeHtml(s) { return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  function chips() {
    const counts = {};
    DATA.posts.forEach((p) => p.series.forEach((s) => counts[s] = (counts[s] || 0) + 1));
    const order = ["全部", ...DATA.series_order.filter((s) => counts[s])];
    $("#chips").innerHTML = order.map((s) =>
      `<button class="chip" role="tab" aria-selected="${s === filter}" data-s="${s}">${s}<small>${s === "全部" ? DATA.posts.length : counts[s]}</small></button>`).join("");
  }

  // ---- lightbox
  function open(i, k = 0) {
    cur = i; img = k; const p = view[i]; if (!p) return;
    const lb = $("#lb"); lb.hidden = false; document.body.style.overflow = "hidden";
    $("#lbDate").textContent = fmtDate(p.created_at, true) + "（上海时间）";
    $("#lbCaption").textContent = titleOf(p);
    $("#lbTags").innerHTML = p.series.map((s) => `<span>${s}</span>`).join("");
    const M = p.metrics;
    $("#lbMetrics").innerHTML = [["曝光", M.impressions], ["点赞", M.likes], ["收藏", M.bookmarks]]
      .map(([l, v]) => `<div><b>${fmt(v)}</b>${l}</div>`).join("");
    $("#lbPrompt").textContent = p.prompt || "";
    $("#lbPromptWrap").hidden = !p.prompt;
    $("#lbLink").href = p.url;
    history.replaceState(null, "", "#p=" + p.id);
    showImg();
  }
  function showImg() {
    const p = view[cur]; const el = $("#lbImg");
    el.classList.add("loading");
    el.onload = () => el.classList.remove("loading");
    el.src = p.images[img]; el.alt = titleOf(p);
    $("#lbDots").innerHTML = p.images.length > 1 ? p.images.map((_, k) => `<button class="${k === img ? "on" : ""}" data-k="${k}" aria-label="第 ${k + 1} 张"></button>`).join("") : "";
    // preload neighbours
    [view[cur + 1], view[cur - 1]].forEach((q) => { if (q) new Image().src = q.images[0]; });
  }
  function step(d) {
    const p = view[cur];
    if (img + d >= 0 && img + d < p.images.length) { img += d; showImg(); return; }
    const n = cur + d; if (n < 0 || n >= view.length) return;
    open(n, d < 0 ? view[n].images.length - 1 : 0);
  }
  function close() {
    $("#lb").hidden = true; document.body.style.overflow = ""; cur = -1;
    history.replaceState(null, "", location.pathname + location.search);
  }
  function toast(t) { const el = $("#toast"); el.textContent = t; el.classList.add("show"); clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("show"), 2400); }

  async function copyPrompt() {
    const pre = $("#lbPrompt"); const t = pre.textContent;
    let ok = false;
    try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(t); ok = true; } } catch { ok = false; }
    if (!ok) {
      try {
        const ta = document.createElement("textarea");
        ta.value = t; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.select();
        ok = document.execCommand("copy");
        ta.remove();
      } catch { ok = false; }
    }
    if (ok) { toast("提示词已复制"); return; }
    // failed: select the prompt so it can be copied by hand
    const r = document.createRange(); r.selectNodeContents(pre);
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
    toast("复制失败，已选中提示词，请手动复制");
  }

  // site.config.json switches (both default off)
  function gate(cfg) {
    if (!cfg || !cfg.adult_notice) return;
    try { if (localStorage.getItem("adult_ok") === "1") return; } catch {}
    $("#gateText").textContent = cfg.adult_notice_text || "";
    $("#gateYes").textContent = cfg.adult_notice_confirm || "进入";
    $("#gateNo").textContent = cfg.adult_notice_leave || "离开";
    $("#gate").hidden = false; document.body.style.overflow = "hidden";
    $("#gateYes").onclick = () => { try { localStorage.setItem("adult_ok", "1"); } catch {} $("#gate").hidden = true; document.body.style.overflow = ""; };
  }

  function profile() {
    const P = DATA.profile || {};
    if (P.name) $("#name").textContent = P.name;
    if (P.bio) $("#bio").textContent = P.bio;
    if (P.banner) $("#heroBg").style.backgroundImage = `url(${P.banner})`;
    if (P.avatar) $("#avatar").src = P.avatar;
    const imgs = DATA.posts.reduce((s, p) => s + p.images.length, 0);
    $("#stats").innerHTML = [["作品", DATA.posts.length], ["图片", imgs], ["关注者", P.followers]]
      .filter(([, v]) => v != null).map(([l, v]) => `<div><b>${fmt(v)}</b>${l}</div>`).join("");
    $("#updated").textContent = fmtDate(DATA.last_updated, true);
    $("#updated").dateTime = DATA.last_updated;
  }

  function bind() {
    $("#chips").addEventListener("click", (e) => {
      const b = e.target.closest(".chip"); if (!b) return;
      filter = b.dataset.s; chips(); render();
    });
    $("#sort").addEventListener("change", (e) => { sort = e.target.value; render(); });
    $("#grid").addEventListener("click", (e) => { const c = e.target.closest(".card"); if (c) open(+c.dataset.i); });
    $("#grid").addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.classList.contains("card")) open(+e.target.dataset.i); });
    $("#lbClose").onclick = close; $("#lbPrev").onclick = () => step(-1); $("#lbNext").onclick = () => step(1);
    $("#lbCopy").onclick = copyPrompt;
    $("#lbDots").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { img = +b.dataset.k; showImg(); } });
    $("#lb").addEventListener("click", (e) => { if (e.target.id === "lb" || e.target.id === "lbStage") close(); });
    addEventListener("keydown", (e) => {
      if (cur < 0) return;
      if (e.key === "Escape") close(); else if (e.key === "ArrowRight") step(1); else if (e.key === "ArrowLeft") step(-1);
    });
    let sx = null;
    $("#lbStage").addEventListener("touchstart", (e) => { sx = e.touches[0].clientX; }, { passive: true });
    $("#lbStage").addEventListener("touchend", (e) => { if (sx == null) return; const dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 50) step(dx < 0 ? 1 : -1); sx = null; });
    let t; addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => { if (colCount() !== state.cols) render(); }, 150); });
  }

  fetch("site.config.json", { cache: "no-cache" }).then((r) => r.ok ? r.json() : null).then(gate).catch(() => {});
  fetch("data/posts.json", { cache: "no-cache" }).then((r) => r.json()).then((d) => {
    DATA = d; profile(); chips(); render(); bind();
    const m = location.hash.match(/p=(\d+)/);
    if (m) { const i = view.findIndex((p) => p.id === m[1]); if (i >= 0) open(i); }
  }).catch((e) => { console.error(e); $("#empty").hidden = false; $("#empty").textContent = "作品数据加载失败，请稍后刷新。"; });
})();
