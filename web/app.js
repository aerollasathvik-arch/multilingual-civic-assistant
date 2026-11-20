// Week 8 front-end (T34): language picker, right-to-left layout, cited answers and source cards.
// Model output is only ever inserted with textContent, never innerHTML.
"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const BULLET = /^\s*(?:[-*•]|\d+[.)])\s+/;
  const CITE = /\[(\d+)\]/g;

  let T = null;            // i18n.json
  let ui = "en";           // interface language
  let maxChars = 500;
  let backend = "loading"; // loading | ready | error | unreachable
  let busy = false;
  let statusKey = null;    // kept so messages can be re-translated when the language changes
  let errorKey = null;
  let last = null;         // last answer, redrawn when the language changes

  const fill = (s, vars) => s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
  const t = (key, vars = {}) => fill((T && (T[ui]?.[key] ?? T.en[key])) ?? key, { max: maxChars, ...vars });
  const dirOf = (lang) => (T.rtl.includes(lang) ? "rtl" : "ltr");
  const el = (tag, props = {}, ...children) => {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children);
    return node;
  };

  // ---------- language ----------
  function remembered() { try { return localStorage.getItem("ui-lang"); } catch { return null; } }
  function remember(lang) { try { localStorage.setItem("ui-lang", lang); } catch { /* private mode */ } }

  function initialLanguage() {
    const fromUrl = new URLSearchParams(location.search).get("lang");  // e.g. study links: /?lang=ur
    for (const cand of [fromUrl, remembered(), ...(navigator.languages || [])]) {
      const base = (cand || "").toLowerCase().split("-")[0];
      if (T.order.includes(base)) return base;
    }
    return "en";
  }

  function applyLanguage(lang) {
    ui = lang;
    const root = document.documentElement;
    root.lang = lang;
    root.dir = dirOf(lang);
    for (const node of document.querySelectorAll("[data-i18n]")) node.textContent = t(node.dataset.i18n);
    $("lang").value = lang;
    $("question").maxLength = maxChars;
    renderExamples();
    if (statusKey) setStatus(statusKey, $("status").classList.contains("busy"));
    if (errorKey) showError(errorKey, false);
    if (last) render(last, false);
    else document.title = t("page_title");
  }

  function buildPicker() {
    const select = $("lang");
    select.replaceChildren(...T.order.map((code) =>
      el("option", { value: code, lang: code, dir: dirOf(code), textContent: T[code].name })));
    select.addEventListener("change", () => { remember(select.value); applyLanguage(select.value); });
  }

  // ---------- status and errors ----------
  function setStatus(key, spinning = false) {
    statusKey = key;
    const node = $("status");
    node.textContent = key ? t(key) : "";
    node.classList.toggle("busy", spinning);
  }

  function showError(code, focus = true) {
    errorKey = code;
    const box = $("question-error");
    box.textContent = t(`err_${code}`);
    box.hidden = false;
    const q = $("question");
    q.setAttribute("aria-invalid", "true");
    q.setAttribute("aria-describedby", "question-error question-hint");
    if (focus) q.focus();
  }

  function clearError() {
    errorKey = null;
    $("question-error").hidden = true;
    const q = $("question");
    q.removeAttribute("aria-invalid");
    q.setAttribute("aria-describedby", "question-hint");
  }

  async function fetchStatus() {
    try {
      const r = await fetch("/api/status", { cache: "no-store" });
      const j = await r.json();
      backend = j.status;
      if (j.max_chars && j.max_chars !== maxChars) { maxChars = j.max_chars; applyLanguage(ui); }
    } catch {
      backend = "unreachable";
    }
  }

  async function poll() {
    await fetchStatus();
    if (busy) return;
    if (backend === "loading") { setStatus("starting", true); setTimeout(poll, 3000); }
    else if (backend === "ready") { if (statusKey === "starting" || statusKey === "err_network") setStatus("ready"); }
    else if (backend === "error") setStatus("err_error");
    else { setStatus("err_network"); setTimeout(poll, 5000); }
  }

  // ---------- asking ----------
  async function ask(event) {
    event.preventDefault();
    if (busy) return;
    const question = $("question").value.trim();
    if (!question) return showError("empty");
    if (question.length > maxChars) return showError("too_long");
    clearError();
    if (backend !== "ready") await fetchStatus();  // the first status check may not have returned yet
    if (backend === "loading") return setStatus("err_loading");

    busy = true;
    $("ask").setAttribute("aria-disabled", "true");
    $("result").setAttribute("aria-busy", "true");
    setStatus("searching", true);
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), 5 * 60 * 1000);
    try {
      const r = await fetch("/api/ask", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }), signal: abort.signal,
      });
      const j = await r.json().catch(() => null);
      if (!r.ok) {
        const code = j?.error || "server";
        if (code === "empty" || code === "too_long") { setStatus(null); showError(code); }
        else setStatus(`err_${code}` in T.en ? `err_${code}` : "err_server");
        if (code === "loading") { backend = "loading"; setTimeout(poll, 3000); }
        return;
      }
      last = j;
      setStatus(null);
      render(j, true);
    } catch {
      setStatus("err_network");
    } finally {
      clearTimeout(timer);
      busy = false;
      $("ask").removeAttribute("aria-disabled");
      $("result").removeAttribute("aria-busy");
    }
  }

  // ---------- rendering ----------
  function formatDate(value) {
    if (!value) return null;
    const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00Z` : value);
    if (Number.isNaN(d.getTime())) return value;
    try {
      const locale = ui === "en" ? "en-GB" : ui;  // "28 October 2026", not the US order
      return new Intl.DateTimeFormat(locale, { dateStyle: "long", timeZone: "Europe/London", numberingSystem: "latn" })
        .format(d);
    } catch {
      return d.toISOString().slice(0, 10);
    }
  }

  function withCitations(node, text, valid) {
    let at = 0;
    for (const m of text.matchAll(CITE)) {
      node.append(text.slice(at, m.index));
      const n = Number(m[1]);
      if (valid.has(n)) {
        const link = el("a", { href: `#source-${n}`, className: "cite", textContent: `[${n}]` });
        link.setAttribute("aria-label", t("source_n", { n }));
        node.append(el("bdi", { dir: "ltr" }, link));
      } else {
        node.append(m[0]);
      }
      at = m.index + m[0].length;
    }
    node.append(text.slice(at));
  }

  function renderAnswer(box, text, valid) {
    box.replaceChildren();
    let list = null;
    let ordered = false;
    for (const raw of text.split("\n")) {
      const line = raw.replace(/\*\*/g, "").trim();  // drop markdown bold the model sometimes adds
      if (!line) { list = null; continue; }
      const bullet = line.match(BULLET);
      if (bullet) {
        const isOrdered = /\d/.test(bullet[0]);
        if (!list || ordered !== isOrdered) {
          list = el(isOrdered ? "ol" : "ul");
          ordered = isOrdered;
          box.append(list);
        }
        const item = el("li");
        withCitations(item, line.slice(bullet[0].length), valid);
        list.append(item);
      } else {
        list = null;
        const p = el("p");
        withCitations(p, line, valid);
        box.append(p);
      }
    }
  }

  function sourceCard(s) {
    const card = el("li", { className: "source" });
    const label = el("p", { className: "source-label" });
    if (s.n != null) {  // cited source: target of the [n] links in the answer
      card.id = `source-${s.n}`;
      card.tabIndex = -1;
      label.append(`${t("source_n", { n: s.n })} · `);
    }
    label.append(el("bdi", { lang: "en", dir: "ltr", textContent: s.source }));
    card.append(label);
    card.append(el("h4", { lang: "en", dir: "ltr", textContent: s.title }));
    if (s.heading && s.heading !== s.title) {
      card.append(el("p", { className: "section", lang: "en", dir: "ltr", textContent: s.heading }));
    }
    const dates = el("dl");
    for (const [key, value] of [["updated", s.public_updated_at], ["copied", s.fetched_at]]) {
      const shown = formatDate(value);
      if (shown) dates.append(el("dt", { textContent: t(key) }), el("dd", { textContent: shown }));
    }
    card.append(dates);
    if (/^https:\/\//.test(s.url || "")) {
      const link = el("a", { href: s.url, target: "_blank", rel: "noopener noreferrer", textContent: t("open") });
      link.append(el("span", { className: "visually-hidden", textContent: ` ${t("new_tab")}` }));
      card.append(link, el("span", { className: "url", lang: "en", dir: "ltr",
                                     textContent: s.url.replace(/^https:\/\//, "") }));
    }
    return card;
  }

  function render(res, moveFocus) {
    const valid = new Set(res.sources.map((s) => s.n));
    const heading = t(res.refused ? "refused_heading" : "answer_heading");
    $("result").hidden = false;
    $("result-heading").textContent = heading;
    $("answer-lang").textContent = t("answer_lang", { lang: T[res.lang]?.name || res.lang });

    const answer = $("answer");
    answer.lang = res.lang;
    answer.dir = dirOf(res.lang);
    renderAnswer(answer, res.answer, valid);

    $("health").hidden = !res.health_note;
    const note = $("health-text");
    note.textContent = res.health_note || "";
    note.lang = res.lang;
    note.dir = dirOf(res.lang);

    $("official").hidden = !res.refused;
    $("sources-block").hidden = res.sources.length === 0;
    $("sources-intro").textContent = t(res.cited === false ? "searched_intro" : "sources_intro");
    const byNumber = [...res.sources].sort((a, b) => (a.n ?? 0) - (b.n ?? 0));  // Source 1, 2, 3 in order
    $("sources").replaceChildren(...byNumber.map(sourceCard));

    document.title = `${heading} – ${t("page_title")}`;
    if (moveFocus) $("result-heading").focus();
  }

  function renderExamples() {
    $("examples").replaceChildren(...T[ui].examples_list.map((q) => {
      const b = el("button", { type: "button", className: "example", textContent: q });
      b.addEventListener("click", () => {
        $("question").value = q;
        clearError();
        $("question").focus();
      });
      return el("li", {}, b);
    }));
  }

  // ---------- start ----------
  async function start() {
    try {
      T = await (await fetch("/static/i18n.json")).json();
    } catch {
      $("status").textContent = "Could not load the page text. Reload the page.";
      return;
    }
    buildPicker();
    applyLanguage(initialLanguage());

    $("ask-form").addEventListener("submit", ask);
    $("question").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) $("ask-form").requestSubmit();
    });
    $("question").addEventListener("input", () => { if (errorKey) clearError(); });
    // Citation links move keyboard focus to the source card, not just the scroll position.
    $("answer").addEventListener("click", (e) => {
      const link = e.target.closest("a.cite");
      if (!link) return;
      const card = document.querySelector(link.getAttribute("href"));
      if (!card) return;
      e.preventDefault();
      card.focus();
    });
    poll();
  }

  start();
})();
