/* ============================================================
   user-journey renderer
   Vanilla JS, zero dependencies. Reads two inlined JSON blocks
   (#journey-data and #design-tokens) and renders three views:
   map / stage / present. Hash routing keeps deep links stable.
   ============================================================ */
(function () {
  "use strict";

  const I18N = {
    en: {
      map: "Map", stage: "Stage", present: "Present",
      open: "Open ›",
      actions: "Actions", touchpoints: "Touchpoints", thoughts: "Thoughts",
      pain: "Pain points", opps: "Opportunities", metrics: "Metrics",
      stages_count: n => `${n} stage${n === 1 ? "" : "s"}`,
      steps_count: n => `${n} step${n === 1 ? "" : "s"}`,
      hint_map: "Drag to pan · scroll to zoom · click a stage to drill in",
      hint_stage: "← → switch stage · S to back to map · P to present",
      hint_present: "← → next/prev · B to blank · Esc to exit",
      no_steps: "No steps yet — this stage is a skeleton.",
      blank: "Blank",
      prev: "Prev",
      next: "Next",
      exit: "Exit",
    },
    zh: {
      map: "地图", stage: "阶段", present: "演示",
      open: "查看 ›",
      actions: "行动", touchpoints: "触点", thoughts: "想法",
      pain: "痛点", opps: "机会", metrics: "指标",
      stages_count: n => `${n} 个阶段`,
      steps_count: n => `${n} 个步骤`,
      hint_map: "拖动画布平移 · 滚轮缩放 · 点击阶段进入详情",
      hint_stage: "← → 切换阶段 · 按 S 回到地图 · 按 P 演示",
      hint_present: "← → 翻页 · 按 B 黑屏 · Esc 退出",
      no_steps: "还没填步骤——这是骨架阶段。",
      blank: "黑屏",
      prev: "上一页",
      next: "下一页",
      exit: "退出",
    },
  };

  const EMOTION_ORDER = ["delighted", "happy", "neutral", "frustrated", "blocked"];

  /* ---------- Token injection ------------------------------ */

  function flattenTokens(tokens, prefix, out) {
    out = out || {};
    if (!tokens || typeof tokens !== "object") return out;
    for (const key of Object.keys(tokens)) {
      const value = tokens[key];
      const path = prefix ? `${prefix}-${key}` : key;
      if (value && typeof value === "object" && !Array.isArray(value)) {
        flattenTokens(value, path, out);
      } else {
        out[path] = value;
      }
    }
    return out;
  }

  function applyDesignTokens(design) {
    if (!design) return;
    const root = document.documentElement;
    if (design.colors) {
      for (const [name, hex] of Object.entries(design.colors)) {
        root.style.setProperty(`--color-${name}`, hex);
      }
    }
    if (design.rounded) {
      for (const [size, dim] of Object.entries(design.rounded)) {
        root.style.setProperty(`--radius-${size}`, dim);
      }
    }
    if (design.spacing) {
      for (const [size, dim] of Object.entries(design.spacing)) {
        const v = typeof dim === "number" ? dim + "px" : dim;
        root.style.setProperty(`--space-${size}`, v);
      }
    }
    if (design.typography) {
      const fontStr = t => `${t.fontWeight || 400} ${t.fontSize || "14px"}/${t.lineHeight || 1.5} ${t.fontFamily || "system-ui, sans-serif"}`;
      for (const [name, t] of Object.entries(design.typography)) {
        if (t && typeof t === "object") {
          root.style.setProperty(`--font-${name}`, fontStr(t));
        }
      }
    }
  }

  /* ---------- Data loading --------------------------------- */

  function loadInlineJSON(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try {
      const text = (el.textContent || "").trim();
      if (!text || text.startsWith("{{")) return null;
      return JSON.parse(text);
    } catch (err) {
      console.error(`Failed to parse JSON in #${id}:`, err);
      return null;
    }
  }

  async function loadJSONFile(path) {
    try {
      const res = await fetch(path);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  /* ---------- App state ------------------------------------ */

  const state = {
    data: null,
    design: null,
    t: I18N.en,
    view: "map",
    activeStageIdx: 0,
    presentIdx: 0,
    zoom: 1,
    pan: { x: 0, y: 0 },
  };

  function t(key, ...args) {
    const v = state.t[key];
    return typeof v === "function" ? v(...args) : v || key;
  }

  /* ---------- Topbar / shortcuts --------------------------- */

  function setupTopbar() {
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const k = el.dataset.i18n;
      const text = t(k);
      if (text) el.textContent = text;
    });
    document.querySelectorAll(".view-btn").forEach(btn => {
      btn.addEventListener("click", () => switchView(btn.dataset.view));
    });
    document.getElementById("zoom-reset").addEventListener("click", () => {
      state.zoom = 1;
      state.pan = { x: 0, y: 0 };
      applyMapTransform();
    });
  }

  function setupShortcuts() {
    document.addEventListener("keydown", e => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      const k = e.key.toLowerCase();
      if (k === "m") switchView("map");
      else if (k === "s") switchView("stage");
      else if (k === "p") switchView("present");
      else if (k === "escape") {
        if (state.view === "present") { document.body.classList.remove("is-blanked"); switchView("map"); }
      } else if (k === "b" && state.view === "present") {
        document.body.classList.toggle("is-blanked");
      } else if (k === "arrowleft") navigateBack();
      else if (k === "arrowright") navigateForward();
      else if (k === "+" || k === "=") { state.zoom = Math.min(2.5, state.zoom + 0.1); applyMapTransform(); }
      else if (k === "-") { state.zoom = Math.max(0.3, state.zoom - 0.1); applyMapTransform(); }
      else if (k === "0") { state.zoom = 1; state.pan = { x: 0, y: 0 }; applyMapTransform(); }
    });
  }

  function navigateBack() {
    if (state.view === "stage") {
      state.activeStageIdx = Math.max(0, state.activeStageIdx - 1);
      renderStage();
    } else if (state.view === "present") {
      state.presentIdx = Math.max(0, state.presentIdx - 1);
      renderPresent();
    }
  }
  function navigateForward() {
    const last = (state.data?.stages?.length || 1) - 1;
    if (state.view === "stage") {
      state.activeStageIdx = Math.min(last, state.activeStageIdx + 1);
      renderStage();
    } else if (state.view === "present") {
      state.presentIdx = Math.min(last, state.presentIdx + 1);
      renderPresent();
    }
  }

  /* ---------- View switching + hash routing ---------------- */

  function switchView(view, opts) {
    opts = opts || {};
    state.view = view;
    document.querySelectorAll(".view").forEach(v => (v.hidden = true));
    document.getElementById(`view-${view}`).hidden = false;
    document.querySelectorAll(".view-btn").forEach(b => {
      const on = b.dataset.view === view;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    document.body.classList.toggle("is-presenting", view === "present");

    const hintEl = document.getElementById("status-hint");
    if (view === "map") {
      hintEl.textContent = t("hint_map");
      renderMap();
    } else if (view === "stage") {
      hintEl.textContent = t("hint_stage");
      renderStage();
    } else if (view === "present") {
      hintEl.textContent = t("hint_present");
      renderPresent();
    }

    if (!opts.fromHash) {
      let hash = `#${view}`;
      if (view === "stage" && state.data?.stages[state.activeStageIdx]) {
        hash = `#stage/${state.data.stages[state.activeStageIdx].id}`;
      } else if (view === "present" && state.data?.stages[state.presentIdx]) {
        hash = `#present/${state.data.stages[state.presentIdx].id}`;
      }
      if (location.hash !== hash) history.replaceState(null, "", hash);
    }
  }

  function applyHashRoute() {
    const h = (location.hash || "").replace(/^#/, "");
    if (!h) { switchView("map", { fromHash: true }); return; }
    const [view, id] = h.split("/");
    if (view === "map") { switchView("map", { fromHash: true }); return; }
    if (view === "stage" || view === "present") {
      if (id) {
        const idx = (state.data?.stages || []).findIndex(s => s.id === id);
        if (idx >= 0) {
          if (view === "stage") state.activeStageIdx = idx;
          else state.presentIdx = idx;
        }
      }
      switchView(view, { fromHash: true });
    } else {
      switchView("map", { fromHash: true });
    }
  }

  /* ---------- Map view ------------------------------------- */

  function emotionToClass(e) {
    return EMOTION_ORDER.includes(e) ? `e-${e}` : "e-neutral";
  }

  function applyMapTransform() {
    const canvas = document.querySelector("#view-map .map-canvas");
    if (!canvas) return;
    canvas.style.transform = `translate(${state.pan.x}px, ${state.pan.y}px) scale(${state.zoom})`;
    const z = document.getElementById("zoom-reset");
    if (z) z.textContent = `${Math.round(state.zoom * 100)}%`;
  }

  function renderMap() {
    const view = document.getElementById("view-map");
    view.innerHTML = "";

    if (state.data?.personas?.length) {
      const personaStrip = document.createElement("div");
      personaStrip.className = "persona-strip";
      state.data.personas.forEach(p => {
        const card = document.createElement("div");
        card.className = "persona-card";
        const goals = (p.goals || []).slice(0, 3).join(" · ");
        card.innerHTML = `
          <div class="persona-card-name">${escapeHTML(p.name || p.id)}</div>
          <div class="persona-card-role">${escapeHTML(p.role || "")}</div>
          ${goals ? `<div class="persona-card-goals">${escapeHTML(goals)}</div>` : ""}
        `;
        personaStrip.appendChild(card);
      });
      view.appendChild(personaStrip);
    }

    const scroller = document.createElement("div");
    scroller.className = "map-scroller";
    const canvas = document.createElement("div");
    canvas.className = "map-canvas";

    const tpl = document.getElementById("tpl-stage-card");
    const edgeTpl = document.getElementById("tpl-stage-edge");

    (state.data?.stages || []).forEach((stage, idx) => {
      const card = tpl.content.firstElementChild.cloneNode(true);
      card.querySelector(".stage-card-num").textContent = String(idx + 1).padStart(2, "0");
      card.querySelector(".stage-card-label").textContent = stage.label;
      card.querySelector(".stage-card-summary").textContent = stage.summary || "";
      const stepsEl = card.querySelector(".stage-card-steps");
      stepsEl.textContent = t("steps_count", (stage.steps || []).length);
      card.querySelector(".stage-card-cta").textContent = t("open");

      const emotions = card.querySelector(".stage-card-emotions");
      (stage.steps || []).forEach(step => {
        const dot = document.createElement("span");
        dot.className = `emotion-dot ${emotionToClass(step.emotion)}`;
        dot.style.background = `var(--color-emotion-${EMOTION_ORDER.includes(step.emotion) ? step.emotion : "neutral"})`;
        dot.title = step.id || "";
        emotions.appendChild(dot);
      });

      if (idx === state.activeStageIdx) card.classList.add("is-active");
      card.addEventListener("click", () => {
        state.activeStageIdx = idx;
        switchView("stage");
      });
      card.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          state.activeStageIdx = idx;
          switchView("stage");
        }
      });
      canvas.appendChild(card);

      if (idx < (state.data?.stages?.length || 0) - 1) {
        canvas.appendChild(edgeTpl.content.firstElementChild.cloneNode(true));
      }
    });

    scroller.appendChild(canvas);
    view.appendChild(scroller);
    applyMapTransform();
    setupMapPanZoom(view, canvas);
  }

  function setupMapPanZoom(view, canvas) {
    let dragging = false, startX = 0, startY = 0, originX = 0, originY = 0;
    view.addEventListener("mousedown", e => {
      if (e.target.closest(".stage-card") || e.target.closest(".persona-card")) return;
      dragging = true; view.classList.add("is-panning");
      startX = e.clientX; startY = e.clientY;
      originX = state.pan.x; originY = state.pan.y;
    });
    window.addEventListener("mousemove", e => {
      if (!dragging) return;
      state.pan.x = originX + (e.clientX - startX);
      state.pan.y = originY + (e.clientY - startY);
      applyMapTransform();
    });
    window.addEventListener("mouseup", () => { dragging = false; view.classList.remove("is-panning"); });
    view.addEventListener("wheel", e => {
      if (!e.ctrlKey && !e.metaKey && Math.abs(e.deltaY) < 10) return;
      e.preventDefault();
      const delta = -e.deltaY * 0.001;
      state.zoom = Math.max(0.3, Math.min(2.5, state.zoom + delta));
      applyMapTransform();
    }, { passive: false });
  }

  /* ---------- Stage view ----------------------------------- */

  function renderStage() {
    const view = document.getElementById("view-stage");
    view.innerHTML = "";
    const stages = state.data?.stages || [];
    if (!stages.length) { view.textContent = t("no_steps"); return; }
    state.activeStageIdx = Math.max(0, Math.min(state.activeStageIdx, stages.length - 1));
    const stage = stages[state.activeStageIdx];

    const header = document.createElement("header");
    header.className = "stage-header";
    header.innerHTML = `
      <div class="stage-header-left">
        <span class="stage-header-eyebrow">${String(state.activeStageIdx + 1).padStart(2, "0")} / ${String(stages.length).padStart(2, "0")}</span>
        <h2 class="stage-header-title">${escapeHTML(stage.label)}</h2>
        <p class="stage-header-summary">${escapeHTML(stage.summary || "")}</p>
      </div>
    `;
    view.appendChild(header);

    const crumbs = document.createElement("nav");
    crumbs.className = "stage-breadcrumb";
    stages.forEach((s, idx) => {
      const c = document.createElement("button");
      c.className = "crumb" + (idx === state.activeStageIdx ? " is-active" : "");
      c.textContent = `${idx + 1}. ${s.label}`;
      c.addEventListener("click", () => { state.activeStageIdx = idx; renderStage(); switchView("stage"); });
      crumbs.appendChild(c);
    });
    view.appendChild(crumbs);

    const stepsWrap = document.createElement("div");
    stepsWrap.className = "stage-steps";
    const tpl = document.getElementById("tpl-step-column");
    if (!(stage.steps || []).length) {
      const empty = document.createElement("p");
      empty.style.padding = "var(--space-xl)";
      empty.style.color = "var(--color-secondary)";
      empty.textContent = t("no_steps");
      view.appendChild(empty);
      return;
    }
    stage.steps.forEach((step, idx) => {
      const col = tpl.content.firstElementChild.cloneNode(true);
      col.querySelector(".step-col-num").textContent = `${state.activeStageIdx + 1}.${idx + 1}`;

      const chip = col.querySelector(".emotion-chip");
      const emotion = EMOTION_ORDER.includes(step.emotion) ? step.emotion : "neutral";
      chip.textContent = emotion;
      chip.classList.add(`e-${emotion}`);

      fillList(col.querySelector(".step-actions ul"), step.actions);
      fillList(col.querySelector(".step-touchpoints ul"), step.touchpoints);
      fillList(col.querySelector(".step-thoughts ul"), step.thoughts);

      const painBlock = col.querySelector(".step-pain");
      if (step.pain_points && step.pain_points.length) {
        painBlock.hidden = false;
        fillList(painBlock.querySelector("ul"), step.pain_points);
      }
      const oppsBlock = col.querySelector(".step-opps");
      if (step.opportunities && step.opportunities.length) {
        oppsBlock.hidden = false;
        fillList(oppsBlock.querySelector("ul"), step.opportunities);
      }
      const metricsBlock = col.querySelector(".step-metrics");
      if (step.metrics && step.metrics.length) {
        metricsBlock.hidden = false;
        const ul = metricsBlock.querySelector("ul");
        step.metrics.forEach(m => {
          const li = document.createElement("li");
          li.innerHTML = `<span class="metric-name">${escapeHTML(m.name || "")}</span>${m.target ? ` <span class="metric-target">${escapeHTML(m.target)}</span>` : ""}`;
          ul.appendChild(li);
        });
      }
      const wfBlock = col.querySelector(".step-wireframe");
      if (step.wireframe && window.UJWireframe) {
        wfBlock.hidden = false;
        wfBlock.appendChild(window.UJWireframe.render(step.wireframe));
      }
      col.querySelectorAll("[data-i18n]").forEach(el => {
        const text = t(el.dataset.i18n);
        if (text) el.textContent = text;
      });
      stepsWrap.appendChild(col);
    });
    view.appendChild(stepsWrap);
  }

  function fillList(ul, items) {
    (items || []).forEach(s => {
      const li = document.createElement("li");
      li.textContent = s;
      ul.appendChild(li);
    });
  }

  /* ---------- Present view --------------------------------- */

  function renderPresent() {
    const view = document.getElementById("view-present");
    view.innerHTML = "";
    const stages = state.data?.stages || [];
    if (!stages.length) { view.textContent = t("no_steps"); return; }
    state.presentIdx = Math.max(0, Math.min(state.presentIdx, stages.length - 1));
    const stage = stages[state.presentIdx];

    const progress = document.createElement("div");
    progress.className = "present-progress";
    stages.forEach((_, idx) => {
      const dot = document.createElement("span");
      dot.className = "present-dot" + (idx === state.presentIdx ? " is-active" : "");
      progress.appendChild(dot);
    });
    view.appendChild(progress);

    const sec = document.createElement("section");
    sec.className = "present-stage";
    sec.innerHTML = `
      <div class="present-eyebrow">${String(state.presentIdx + 1).padStart(2, "0")} / ${String(stages.length).padStart(2, "0")} · ${escapeHTML(state.data?.title || "")}</div>
      <h2 class="present-title">${escapeHTML(stage.label)}</h2>
      <p class="present-summary">${escapeHTML(stage.summary || "")}</p>
    `;

    if (stage.steps && stage.steps.length) {
      const allActions = stage.steps.flatMap(s => s.actions || []);
      const allTouchpoints = stage.steps.flatMap(s => s.touchpoints || []);
      const allThoughts = stage.steps.flatMap(s => s.thoughts || []);
      const grid = document.createElement("div");
      grid.className = "present-grid";
      grid.appendChild(buildPresentCol(t("actions"), allActions));
      grid.appendChild(buildPresentCol(t("touchpoints"), allTouchpoints));
      grid.appendChild(buildPresentCol(t("thoughts"), allThoughts));
      sec.appendChild(grid);
    }
    view.appendChild(sec);

    if (stage.notes) {
      const notes = document.createElement("div");
      notes.className = "present-notes";
      notes.textContent = stage.notes;
      view.appendChild(notes);
    }

    const controls = document.createElement("div");
    controls.className = "present-controls";
    controls.innerHTML = `
      <button data-act="prev">← ${t("prev")}</button>
      <button data-act="blank">${t("blank")}</button>
      <button data-act="exit">${t("exit")}</button>
      <button data-act="next">${t("next")} →</button>
    `;
    controls.querySelector("[data-act='prev']").addEventListener("click", navigateBack);
    controls.querySelector("[data-act='next']").addEventListener("click", navigateForward);
    controls.querySelector("[data-act='blank']").addEventListener("click", () => document.body.classList.toggle("is-blanked"));
    controls.querySelector("[data-act='exit']").addEventListener("click", () => { document.body.classList.remove("is-blanked"); switchView("map"); });
    view.appendChild(controls);
  }

  function buildPresentCol(label, items) {
    const col = document.createElement("div");
    col.className = "present-col";
    const h = document.createElement("h4"); h.textContent = label;
    const ul = document.createElement("ul");
    items.slice(0, 6).forEach(text => {
      const li = document.createElement("li"); li.textContent = text; ul.appendChild(li);
    });
    col.appendChild(h);
    col.appendChild(ul);
    return col;
  }

  /* ---------- Meta + bootstrap ----------------------------- */

  function escapeHTML(s) {
    return String(s || "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    }[c]));
  }

  function setMeta() {
    const stages = state.data?.stages || [];
    document.getElementById("meta-stage-count").textContent = t("stages_count", stages.length);
    if (state.data?.title) {
      document.getElementById("topbar-title").textContent = state.data.title;
      document.title = state.data.title;
    }
  }

  async function init() {
    /* Prefer freshly-fetched files so the page reflects edits made after
       the initial scaffold. Fall back to the inlined JSON when fetch is
       blocked (e.g. some browsers' file:// CORS policy). */
    let data = await loadJSONFile("journey.json");
    if (!data) data = loadInlineJSON("journey-data");
    let design = null;
    const designMd = await fetchText("DESIGN.md");
    if (designMd) design = parseDesignFrontmatter(designMd);
    if (!design) design = loadInlineJSON("design-tokens");
    state.data = data || { title: "Untitled", language: "en", personas: [], stages: [] };
    state.design = design;
    state.t = I18N[state.data.language] || I18N.en;

    applyDesignTokens(design);
    setupTopbar();
    setupShortcuts();
    setMeta();
    applyHashRoute();
    window.addEventListener("hashchange", applyHashRoute);
  }

  async function fetchText(path) {
    try {
      const res = await fetch(path);
      if (!res.ok) return null;
      return await res.text();
    } catch { return null; }
  }

  /* ---------- Minimal YAML-frontmatter extractor ----------
     Only used as a fallback when DESIGN.md isn't inlined. We
     extract `colors:`, `typography:`, `rounded:`, `spacing:`
     using a small hand-written parser — no YAML lib. */

  function parseDesignFrontmatter(md) {
    const m = md.match(/^---\s*\n([\s\S]*?)\n---/);
    if (!m) return null;
    const yaml = m[1];
    const out = { colors: {}, typography: {}, rounded: {}, spacing: {} };
    let section = null, currentTypo = null;
    const lines = yaml.split("\n");
    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i];
      if (!raw.trim() || raw.trim().startsWith("#")) continue;
      const indent = raw.length - raw.trimStart().length;
      const line = raw.trim();
      if (indent === 0) {
        const [k] = line.split(":");
        if (["colors", "typography", "rounded", "spacing"].includes(k)) { section = k; currentTypo = null; }
        else section = null;
        continue;
      }
      if (!section) continue;
      const [keyRaw, ...rest] = line.split(":");
      const key = keyRaw.trim();
      const value = rest.join(":").trim();
      if (section === "typography") {
        if (indent === 2 && !value) {
          currentTypo = key;
          out.typography[currentTypo] = {};
        } else if (indent >= 4 && currentTypo) {
          out.typography[currentTypo][key] = stripQuotes(value);
        }
      } else if (section === "colors") {
        out.colors[key] = stripQuotes(value);
      } else if (section === "rounded") {
        out.rounded[key] = stripQuotes(value);
      } else if (section === "spacing") {
        out.spacing[key] = stripQuotes(value);
      }
    }
    return out;
  }
  function stripQuotes(s) { return String(s || "").replace(/^["']|["']$/g, ""); }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else { init(); }
})();
