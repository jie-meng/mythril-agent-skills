/* ============================================================
   user-journey renderer (v2)
   Vanilla JS, zero dependencies. Reads two inlined JSON blocks
   (#journey-data and #design-tokens) and renders four views:
   map / stage / flow / present.

   Default landing view (empty hash):
     - "flow/<first-screen-id>" when journey.screens is non-empty
     - "map" otherwise (legacy / screens-not-authored-yet projects)

   Hash routing supports two stable forms — both work:
     #map | #/map
     #stage/<id> | #/stage/<id>
     #flow/<screen-id> | #/flow/<screen-id>
     #present[/<stage-id>][/screens]
   ============================================================ */
(function () {
  "use strict";

  const I18N = {
    en: {
      map: "Map", stage: "Stage", flow: "Flow", present: "Present", screens: "Screens",
      open: "Open ›",
      actions: "Actions", touchpoints: "Touchpoints", thoughts: "Thoughts",
      pain: "Pain points", opps: "Opportunities", metrics: "Metrics",
      stages_count: n => `${n} stage${n === 1 ? "" : "s"}`,
      steps_count: n => `${n} step${n === 1 ? "" : "s"}`,
      screens_count: n => `${n} screen${n === 1 ? "" : "s"}`,
      hint_map: "Drag to pan · scroll to zoom · click a stage to drill in · click a screen thumbnail to jump to Flow",
      hint_stage: "← → switch stage · S to back to map · F to see screens · P to present",
      hint_flow: "J/K prev/next screen · Enter follow default · 1–9 follow transition · Space auto-play · Backspace go back",
      hint_present: "← → next/prev · Space to run screens for current stage · B to blank · Esc to exit",
      no_steps: "No steps yet — this stage is a skeleton.",
      no_screens: "No screens yet — add screens[] entries in journey.json so the Flow view has something to show.",
      blank: "Blank",
      prev: "Prev",
      next: "Next",
      exit: "Exit",
      run_screens: "Run screens (Space)",
      back_to_stage: "Back to stage",
      kind: "Kind",
      stage_lbl: "Stage",
      transitions_lbl: "Transitions",
      incoming_lbl: "Used by",
      neighbors_lbl: "Mini flow",
      no_transitions: "No outgoing transitions.",
      no_referrers: "Not referenced by any step.",
      hotspot_legend: "Blue outlines = tappable. Hover for destination, click to follow.",
      map_hint_prefix: "This is the bird's-eye Map. Press ",
      map_hint_suffix: " (or click any thumbnail) to walk real wireframes in Flow view.",
      stage_card_screens_hint: "Click any screen → opens it in Flow with full controls",
    },
    zh: {
      map: "地图", stage: "阶段", flow: "屏流", present: "演示", screens: "屏",
      open: "查看 ›",
      actions: "行动", touchpoints: "触点", thoughts: "想法",
      pain: "痛点", opps: "机会", metrics: "指标",
      stages_count: n => `${n} 个阶段`,
      steps_count: n => `${n} 个步骤`,
      screens_count: n => `${n} 个屏`,
      hint_map: "拖动画布平移 · 滚轮缩放 · 点击阶段进入详情 · 点击屏缩略图进入 Flow",
      hint_stage: "← → 切换阶段 · S 回到地图 · F 看屏 · P 演示",
      hint_flow: "J/K 上下屏 · Enter 主路径 · 1–9 跳第 N 个跳转 · Space 自动播放 · Backspace 后退",
      hint_present: "← → 翻页 · Space 进入当前阶段的屏播放 · B 黑屏 · Esc 退出",
      no_steps: "还没填步骤——这是骨架阶段。",
      no_screens: "还没有屏——在 journey.json 的 screens[] 里加入屏,Flow 视图才会有内容。",
      blank: "黑屏",
      prev: "上一页",
      next: "下一页",
      exit: "退出",
      run_screens: "演示屏 (Space)",
      back_to_stage: "回到阶段",
      kind: "类型",
      stage_lbl: "阶段",
      transitions_lbl: "跳转",
      incoming_lbl: "被引用于",
      neighbors_lbl: "相邻屏",
      no_transitions: "没有外向跳转。",
      no_referrers: "没有任何步骤引用此屏。",
      hotspot_legend: "蓝色虚线为可点击热区,悬停看跳转,点击跟随。",
      map_hint_prefix: "这里是鸟瞰地图。按 ",
      map_hint_suffix: " 键（或点击任意缩略图）进入 Flow 视图，查看真实可交互的线框图。",
      stage_card_screens_hint: "点击任意屏 → 进入 Flow 查看完整 UI 与跳转",
    },
  };

  const EMOTION_ORDER = ["delighted", "happy", "neutral", "frustrated", "blocked"];

  const SCREEN_KIND_ICONS = {
    "mobile-screen": "📱", "tablet-screen": "📱", "desktop-window": "🖥",
    "atm-screen": "🏧", "kiosk-screen": "🖼", "tv-screen": "📺",
    "email": "📧", "modal": "▢", "notification": "🔔",
  };

  /* ---------- Token injection ------------------------------ */

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
      const res = await fetch(path + (path.includes("?") ? "" : "?_=" + Date.now()));
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  async function fetchText(path) {
    try {
      const res = await fetch(path + (path.includes("?") ? "" : "?_=" + Date.now()));
      if (!res.ok) return null;
      return await res.text();
    } catch { return null; }
  }

  /* ---------- App state ------------------------------------ */

  const state = {
    data: null,
    design: null,
    t: I18N.en,
    view: "map",
    activeStageIdx: 0,
    activeScreenId: null,
    presentIdx: 0,
    presentScreenMode: false,
    presentScreenIdx: 0,
    zoom: 1,
    pan: { x: 0, y: 0 },
    autoplayTimer: null,
    flowHistory: [],
    screenIndex: new Map(),
    stepRefsByScreen: new Map(),
    inboundByScreen: new Map(),
    outboundByScreen: new Map(),
  };

  function t(key, ...args) {
    const v = state.t[key];
    return typeof v === "function" ? v(...args) : v || key;
  }

  /* ---------- Indexing ------------------------------------- */

  function rebuildIndexes() {
    state.screenIndex = new Map();
    state.stepRefsByScreen = new Map();
    state.inboundByScreen = new Map();
    state.outboundByScreen = new Map();
    const screens = state.data?.screens || [];
    screens.forEach(s => {
      if (!s || !s.id) return;
      state.screenIndex.set(s.id, s);
      state.stepRefsByScreen.set(s.id, []);
      state.inboundByScreen.set(s.id, []);
      state.outboundByScreen.set(s.id, []);
    });
    (state.data?.stages || []).forEach((stage, stageIdx) => {
      (stage.steps || []).forEach((step, stepIdx) => {
        (step.screen_refs || []).forEach(ref => {
          if (state.stepRefsByScreen.has(ref)) {
            state.stepRefsByScreen.get(ref).push({ stage, stageIdx, step, stepIdx });
          }
        });
      });
    });
    screens.forEach(s => {
      (s.transitions || []).forEach(tx => {
        if (!tx || !tx.to_screen) return;
        const tgt = state.inboundByScreen.get(tx.to_screen);
        if (tgt) tgt.push({ from: s.id, tx });
        const src = state.outboundByScreen.get(s.id);
        if (src) src.push(tx);
      });
    });
  }

  function getScreensByStage() {
    const map = new Map();
    (state.data?.stages || []).forEach(s => map.set(s.id, []));
    map.set("__unstaged__", []);
    (state.data?.screens || []).forEach(screen => {
      const sid = screen.stage_id && map.has(screen.stage_id) ? screen.stage_id : "__unstaged__";
      map.get(sid).push(screen);
    });
    return map;
  }

  function getScreensForStage(stage) {
    if (!stage) return [];
    // Screens directly tagged with this stage_id, in source order.
    const byTag = (state.data?.screens || []).filter(s => s.stage_id === stage.id);
    // Plus screens referenced from any step of this stage that are not already included.
    const seen = new Set(byTag.map(s => s.id));
    (stage.steps || []).forEach(step => {
      (step.screen_refs || []).forEach(ref => {
        if (!seen.has(ref) && state.screenIndex.has(ref)) {
          byTag.push(state.screenIndex.get(ref));
          seen.add(ref);
        }
      });
    });
    return byTag;
  }

  function uniqueDeviceKinds(screens) {
    const out = [];
    const seen = new Set();
    (screens || []).forEach(s => {
      const k = s.kind || "mobile-screen";
      if (!seen.has(k)) {
        seen.add(k);
        out.push(k);
      }
    });
    return out;
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
      if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
      const k = e.key.toLowerCase();
      // Global view switching
      if (k === "m") { switchView("map"); return; }
      if (k === "s") { switchView("stage"); return; }
      if (k === "f") { switchView("flow"); return; }
      if (k === "p") { switchView("present"); return; }

      if (k === "escape") {
        if (state.view === "present") {
          if (state.presentScreenMode) {
            stopPresentScreenMode();
          } else {
            document.body.classList.remove("is-blanked");
            switchView("map");
          }
        }
        return;
      }
      if (k === "b" && state.view === "present") {
        document.body.classList.toggle("is-blanked");
        return;
      }

      if (state.view === "flow") {
        if (k === "j") { flowGotoOffset(1); e.preventDefault(); return; }
        if (k === "k") { flowGotoOffset(-1); e.preventDefault(); return; }
        if (k === "enter") { flowFollowDefault(); e.preventDefault(); return; }
        if (k === "backspace") { flowGoBack(); e.preventDefault(); return; }
        if (k === " ") { toggleFlowAutoplay(); e.preventDefault(); return; }
        const idx = parseInt(k, 10);
        if (Number.isInteger(idx) && idx >= 1 && idx <= 9) {
          flowFollowNth(idx - 1);
          e.preventDefault();
          return;
        }
      }

      if (state.view === "present" && k === " ") {
        if (state.presentScreenMode) {
          presentScreenAdvance();
        } else {
          startPresentScreenMode();
        }
        e.preventDefault();
        return;
      }

      if (k === "arrowleft") navigateBack();
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
      if (state.presentScreenMode) {
        presentScreenRewind();
      } else {
        state.presentIdx = Math.max(0, state.presentIdx - 1);
        renderPresent();
      }
    }
  }
  function navigateForward() {
    const last = (state.data?.stages?.length || 1) - 1;
    if (state.view === "stage") {
      state.activeStageIdx = Math.min(last, state.activeStageIdx + 1);
      renderStage();
    } else if (state.view === "present") {
      if (state.presentScreenMode) {
        presentScreenAdvance();
      } else {
        state.presentIdx = Math.min(last, state.presentIdx + 1);
        renderPresent();
      }
    }
  }

  /* ---------- View switching + hash routing ---------------- */

  function switchView(view, opts) {
    opts = opts || {};
    state.view = view;
    document.querySelectorAll(".view").forEach(v => (v.hidden = true));
    const target = document.getElementById(`view-${view}`);
    if (!target) return;
    target.hidden = false;
    document.querySelectorAll(".view-btn").forEach(b => {
      const on = b.dataset.view === view;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    document.body.classList.toggle("is-presenting", view === "present");
    stopFlowAutoplay();

    const hintEl = document.getElementById("status-hint");
    if (view === "map") {
      hintEl.textContent = t("hint_map");
      renderMap();
    } else if (view === "stage") {
      hintEl.textContent = t("hint_stage");
      renderStage();
    } else if (view === "flow") {
      hintEl.textContent = t("hint_flow");
      renderFlow();
    } else if (view === "present") {
      hintEl.textContent = t("hint_present");
      if (!opts.keepPresentMode) state.presentScreenMode = false;
      renderPresent();
    }

    if (!opts.fromHash) {
      let hash = `#${view}`;
      if (view === "stage" && state.data?.stages[state.activeStageIdx]) {
        hash = `#stage/${state.data.stages[state.activeStageIdx].id}`;
      } else if (view === "flow" && state.activeScreenId) {
        hash = `#flow/${state.activeScreenId}`;
      } else if (view === "present" && state.data?.stages[state.presentIdx]) {
        hash = `#present/${state.data.stages[state.presentIdx].id}`;
        if (state.presentScreenMode) hash += "/screens";
      }
      if (location.hash !== hash) history.replaceState(null, "", hash);
    }
  }

  function applyHashRoute() {
    // Accept both #foo and #/foo styles.
    const h = (location.hash || "").replace(/^#\/?/, "");
    if (!h) {
      // Default landing view: Flow (real wireframes) when screens exist,
      // otherwise fall back to Map. Users with non-trivial journeys should
      // see actual UI on first open, not a thumbnail strip.
      const firstScreen = (state.data?.screens && state.data.screens[0]) || null;
      if (firstScreen) {
        state.activeScreenId = firstScreen.id;
        switchView("flow", { fromHash: true });
      } else {
        switchView("map", { fromHash: true });
      }
      return;
    }
    const parts = h.split("/");
    const view = parts[0];
    const id = parts[1];
    if (view === "map") { switchView("map", { fromHash: true }); return; }
    if (view === "stage" || view === "present") {
      if (id) {
        const idx = (state.data?.stages || []).findIndex(s => s.id === id);
        if (idx >= 0) {
          if (view === "stage") state.activeStageIdx = idx;
          else state.presentIdx = idx;
        }
      }
      if (view === "present" && parts[2] === "screens") {
        state.presentScreenMode = true;
        switchView("present", { fromHash: true, keepPresentMode: true });
      } else {
        switchView(view, { fromHash: true });
      }
      return;
    }
    if (view === "flow") {
      if (id && state.screenIndex.has(id)) {
        state.activeScreenId = id;
      }
      switchView("flow", { fromHash: true });
      return;
    }
    switchView("map", { fromHash: true });
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

    // Permanent hint: this view is the overview; real wireframes live in Flow.
    if ((state.data?.screens || []).length) {
      const banner = document.createElement("div");
      banner.className = "map-hint-banner";
      const kbd = document.createElement("kbd");
      kbd.textContent = "F";
      banner.append(
        document.createTextNode(t("map_hint_prefix")),
        kbd,
        document.createTextNode(t("map_hint_suffix")),
      );
      view.appendChild(banner);
    }

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

      const screens = getScreensForStage(stage);

      // Device-kind badges in the head: instant signal whether the stage was
      // modeled with the right device (e.g. ATM screens get 🏧, not 📱).
      const devicesEl = card.querySelector(".stage-card-devices");
      if (devicesEl) {
        const kinds = uniqueDeviceKinds(screens);
        kinds.forEach(kind => {
          const badge = document.createElement("span");
          badge.className = "device-badge";
          badge.textContent = SCREEN_KIND_ICONS[kind] || "▢";
          badge.title = kind;
          devicesEl.appendChild(badge);
        });
      }

      const emotions = card.querySelector(".stage-card-emotions");
      (stage.steps || []).forEach(step => {
        const dot = document.createElement("span");
        dot.className = `emotion-dot ${emotionToClass(step.emotion)}`;
        dot.style.background = `var(--color-emotion-${EMOTION_ORDER.includes(step.emotion) ? step.emotion : "neutral"})`;
        dot.title = step.id || "";
        emotions.appendChild(dot);
      });

      // Append per-stage screen thumbnails strip
      if (screens.length && window.UJWireframe) {
        const strip = document.createElement("div");
        strip.className = "stage-card-screens";
        screens.forEach(screen => {
          const wrap = document.createElement("button");
          wrap.className = "stage-card-screen";
          wrap.type = "button";
          wrap.title = `${screen.title || screen.id} (${screen.kind || "screen"}) — open in Flow`;
          wrap.appendChild(window.UJWireframe.renderThumbnail(screen));
          const label = document.createElement("span");
          label.className = "stage-card-screen-label";
          label.textContent = screen.title || screen.id;
          wrap.appendChild(label);
          wrap.addEventListener("click", (ev) => {
            ev.stopPropagation();
            state.activeScreenId = screen.id;
            switchView("flow");
          });
          strip.appendChild(wrap);
        });
        const hint = document.createElement("div");
        hint.className = "stage-card-screens-hint";
        hint.textContent = t("stage_card_screens_hint");
        strip.appendChild(hint);
        card.appendChild(strip);
      }

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
      const screensBlock = col.querySelector(".step-screens");
      const refs = step.screen_refs || [];
      const resolvedRefs = refs.map(r => state.screenIndex.get(r)).filter(Boolean);
      if (resolvedRefs.length) {
        screensBlock.hidden = false;
        const host = screensBlock.querySelector(".step-screens");
        host.innerHTML = "";
        resolvedRefs.forEach(screen => {
          const c = document.createElement("button");
          c.className = "step-screen-chip";
          c.type = "button";
          const icon = SCREEN_KIND_ICONS[screen.kind] || "▢";
          c.innerHTML = `<span class="step-screen-chip-icon">${icon}</span><span class="step-screen-chip-label">${escapeHTML(screen.title || screen.id)}</span>`;
          c.addEventListener("click", () => {
            state.activeScreenId = screen.id;
            switchView("flow");
          });
          host.appendChild(c);
        });
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

  /* ---------- Flow view (new) ------------------------------ */

  function ensureActiveScreenId() {
    const screens = state.data?.screens || [];
    if (state.activeScreenId && state.screenIndex.has(state.activeScreenId)) return;
    state.activeScreenId = screens[0]?.id || null;
  }

  function renderFlow() {
    ensureActiveScreenId();
    const nav = document.getElementById("flow-nav");
    const stageHost = document.getElementById("flow-stage");
    const panel = document.getElementById("flow-panel");
    nav.innerHTML = ""; stageHost.innerHTML = ""; panel.innerHTML = "";

    const screens = state.data?.screens || [];
    if (!screens.length) {
      stageHost.innerHTML = `<p style="padding: var(--space-xl); color: var(--color-secondary); max-width: 60ch;">${escapeHTML(t("no_screens"))}</p>`;
      return;
    }

    const grouped = getScreensByStage();
    (state.data?.stages || []).forEach(stage => {
      const items = grouped.get(stage.id) || [];
      if (!items.length) return;
      const sec = document.createElement("div");
      sec.className = "flow-nav-section";
      const lbl = document.createElement("div");
      lbl.className = "flow-nav-section-label";
      lbl.textContent = stage.label;
      sec.appendChild(lbl);
      items.forEach(screen => sec.appendChild(makeFlowNavItem(screen)));
      nav.appendChild(sec);
    });
    const unstaged = grouped.get("__unstaged__") || [];
    if (unstaged.length) {
      const sec = document.createElement("div");
      sec.className = "flow-nav-section";
      const lbl = document.createElement("div");
      lbl.className = "flow-nav-section-label";
      lbl.textContent = "—";
      sec.appendChild(lbl);
      unstaged.forEach(screen => sec.appendChild(makeFlowNavItem(screen)));
      nav.appendChild(sec);
    }

    const screen = state.screenIndex.get(state.activeScreenId);
    if (!screen) {
      stageHost.innerHTML = `<p style="padding: var(--space-xl); color: var(--color-secondary);">screen '${escapeHTML(state.activeScreenId || "")}' not found</p>`;
      return;
    }

    const stageOfScreen = (state.data?.stages || []).find(s => s.id === screen.stage_id);
    const header = document.createElement("div");
    header.className = "flow-stage-header";
    header.innerHTML = `
      <span class="flow-stage-title">${escapeHTML(screen.title || screen.id)}</span>
      <span class="flow-stage-sub">${escapeHTML(stageOfScreen ? stageOfScreen.label + " · " : "")}${escapeHTML(screen.kind || "screen")}</span>
    `;
    stageHost.appendChild(header);

    const screenHost = document.createElement("div");
    screenHost.className = "flow-screen-host";
    const frame = window.UJWireframe.renderScreen(screen, {
      size: "full",
      hotspots: true,
      onJump: (toScreenId) => flowGoto(toScreenId, { push: true }),
    });
    if (frame) screenHost.appendChild(frame);
    stageHost.appendChild(screenHost);

    renderFlowPanel(panel, screen);
  }

  function makeFlowNavItem(screen) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "flow-nav-item" + (screen.id === state.activeScreenId ? " is-active" : "");
    btn.innerHTML = `
      <span class="flow-nav-icon">${SCREEN_KIND_ICONS[screen.kind] || "▢"}</span>
      <span class="flow-nav-title">${escapeHTML(screen.title || screen.id)}</span>
    `;
    btn.addEventListener("click", () => flowGoto(screen.id, { push: true }));
    return btn;
  }

  function renderFlowPanel(panel, screen) {
    panel.innerHTML = "";

    const stageOfScreen = (state.data?.stages || []).find(s => s.id === screen.stage_id);
    const meta = document.createElement("div");
    meta.className = "flow-panel-meta";
    meta.innerHTML = `
      <div><strong>${escapeHTML(t("kind"))}:</strong> ${escapeHTML(screen.kind || "—")}</div>
      <div><strong>${escapeHTML(t("stage_lbl"))}:</strong> ${escapeHTML(stageOfScreen ? stageOfScreen.label : "—")}</div>
    `;
    panel.appendChild(meta);
    if (screen.notes) {
      const notes = document.createElement("div");
      notes.className = "flow-panel-meta";
      notes.style.fontStyle = "italic";
      notes.textContent = screen.notes;
      panel.appendChild(notes);
    }

    const legend = document.createElement("div");
    legend.className = "flow-panel-meta";
    legend.textContent = t("hotspot_legend");
    panel.appendChild(legend);

    // Outgoing transitions
    const outBlk = document.createElement("div");
    const outH = document.createElement("h4");
    outH.textContent = t("transitions_lbl");
    outBlk.appendChild(outH);
    const outList = document.createElement("div");
    outList.className = "flow-transitions";
    const txs = state.outboundByScreen.get(screen.id) || [];
    if (!txs.length) {
      const p = document.createElement("p");
      p.className = "flow-panel-meta";
      p.textContent = t("no_transitions");
      outBlk.appendChild(p);
    } else {
      txs.forEach((tx, idx) => outList.appendChild(makeTransitionRow(tx, idx + 1)));
      outBlk.appendChild(outList);
    }
    panel.appendChild(outBlk);

    // Incoming references (steps + screens that point here)
    const inBlk = document.createElement("div");
    const inH = document.createElement("h4");
    inH.textContent = t("incoming_lbl");
    inBlk.appendChild(inH);
    const refs = state.stepRefsByScreen.get(screen.id) || [];
    const tgts = state.inboundByScreen.get(screen.id) || [];
    if (!refs.length && !tgts.length) {
      const p = document.createElement("p");
      p.className = "flow-panel-meta";
      p.textContent = t("no_referrers");
      inBlk.appendChild(p);
    } else {
      const inList = document.createElement("div");
      inList.className = "flow-incoming";
      refs.forEach(r => {
        const row = document.createElement("button");
        row.type = "button";
        row.className = "flow-incoming-item";
        const label = `${r.stage.label} · step ${r.stepIdx + 1}`;
        row.textContent = label;
        row.style.cursor = "pointer";
        row.style.textAlign = "left";
        row.style.background = "transparent";
        row.style.border = "0";
        row.style.padding = "2px 0";
        row.title = `Go to Stage view ${r.stageIdx + 1}`;
        row.addEventListener("click", () => {
          state.activeStageIdx = r.stageIdx;
          switchView("stage");
        });
        inList.appendChild(row);
      });
      tgts.forEach(({ from, tx }) => {
        const fromScreen = state.screenIndex.get(from);
        const row = document.createElement("button");
        row.type = "button";
        row.className = "flow-incoming-item";
        row.style.cursor = "pointer";
        row.style.textAlign = "left";
        row.style.background = "transparent";
        row.style.border = "0";
        row.style.padding = "2px 0";
        row.textContent = `${fromScreen ? (fromScreen.title || fromScreen.id) : from}: ${tx.label || tx.trigger || "tap"}`;
        row.addEventListener("click", () => flowGoto(from, { push: true }));
        inList.appendChild(row);
      });
      inBlk.appendChild(inList);
    }
    panel.appendChild(inBlk);

    // Mini flow graph: incoming + current + outgoing
    const miniH = document.createElement("h4");
    miniH.textContent = t("neighbors_lbl");
    panel.appendChild(miniH);
    const mini = document.createElement("div");
    mini.className = "flow-mini-graph";
    const seenIds = new Set();
    function addLine(id, current) {
      if (!id || seenIds.has(id)) return;
      seenIds.add(id);
      const s = state.screenIndex.get(id);
      const node = document.createElement("div");
      node.className = "flow-mini-node" + (current ? " is-current" : "");
      node.textContent = s ? (s.title || s.id) : id;
      mini.appendChild(node);
    }
    tgts.slice(0, 4).forEach(({ from }) => addLine(from, false));
    addLine(screen.id, true);
    txs.slice(0, 4).forEach(tx => addLine(tx.to_screen, false));
    panel.appendChild(mini);
  }

  function makeTransitionRow(tx, n) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "flow-transition" + (tx.is_default ? " is-default" : "") + (tx.is_error_path ? " is-error" : "");
    row.innerHTML = `
      <span class="flow-transition-num">${n}</span>
      <span class="flow-transition-body">
        <div class="flow-transition-label">${escapeHTML(tx.label || tx.to_screen)}</div>
        <div class="flow-transition-meta">${escapeHTML(tx.from_element)} · ${escapeHTML(tx.trigger || "tap")} → ${escapeHTML(tx.to_screen)}${tx.delay_ms ? ` · ${tx.delay_ms}ms` : ""}${tx.is_default ? " · default" : ""}${tx.is_error_path ? " · error" : ""}</div>
      </span>
    `;
    row.addEventListener("click", () => flowGoto(tx.to_screen, { push: true }));
    return row;
  }

  function flowGoto(screenId, opts) {
    opts = opts || {};
    if (!state.screenIndex.has(screenId)) return;
    if (opts.push && state.activeScreenId && state.activeScreenId !== screenId) {
      state.flowHistory.push(state.activeScreenId);
      if (state.flowHistory.length > 100) state.flowHistory.shift();
    }
    state.activeScreenId = screenId;
    if (state.view !== "flow") {
      switchView("flow");
    } else {
      renderFlow();
      let hash = `#flow/${screenId}`;
      if (location.hash !== hash) history.replaceState(null, "", hash);
    }
  }

  function flowGoBack() {
    if (!state.flowHistory.length) return;
    const prev = state.flowHistory.pop();
    state.activeScreenId = prev;
    renderFlow();
    let hash = `#flow/${prev}`;
    if (location.hash !== hash) history.replaceState(null, "", hash);
  }

  function flowGotoOffset(delta) {
    const ids = (state.data?.screens || []).map(s => s.id);
    if (!ids.length) return;
    const cur = Math.max(0, ids.indexOf(state.activeScreenId));
    const next = Math.max(0, Math.min(ids.length - 1, cur + delta));
    flowGoto(ids[next], { push: true });
  }

  function flowFollowDefault() {
    const screen = state.screenIndex.get(state.activeScreenId);
    if (!screen) return;
    const txs = screen.transitions || [];
    const def = txs.find(t => t.is_default) || txs[0];
    if (def) flowGoto(def.to_screen, { push: true });
  }

  function flowFollowNth(idx) {
    const screen = state.screenIndex.get(state.activeScreenId);
    if (!screen) return;
    const txs = screen.transitions || [];
    const t = txs[idx];
    if (t) flowGoto(t.to_screen, { push: true });
  }

  function toggleFlowAutoplay() {
    if (state.autoplayTimer) {
      stopFlowAutoplay();
    } else {
      runFlowAutoplay();
    }
  }
  function stopFlowAutoplay() {
    if (state.autoplayTimer) {
      clearTimeout(state.autoplayTimer);
      state.autoplayTimer = null;
    }
  }
  function runFlowAutoplay() {
    stopFlowAutoplay();
    const screen = state.screenIndex.get(state.activeScreenId);
    if (!screen) return;
    const def = (screen.transitions || []).find(t => t.is_default);
    if (!def) return;
    const delay = Math.max(400, def.delay_ms || 1200);
    state.autoplayTimer = setTimeout(() => {
      flowGoto(def.to_screen, { push: true });
      // chain
      runFlowAutoplay();
    }, delay);
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

    if (state.presentScreenMode) {
      renderPresentScreens(view, stage);
    } else {
      renderPresentStage(view, stage);
    }

    if (stage.notes) {
      const notes = document.createElement("div");
      notes.className = "present-notes";
      notes.textContent = stage.notes;
      view.appendChild(notes);
    }

    const controls = document.createElement("div");
    controls.className = "present-controls";
    if (state.presentScreenMode) {
      controls.innerHTML = `
        <button data-act="prev">← ${t("prev")}</button>
        <button data-act="back-stage">${t("back_to_stage")}</button>
        <button data-act="exit">${t("exit")}</button>
        <button data-act="next">${t("next")} →</button>
      `;
      controls.querySelector("[data-act='back-stage']").addEventListener("click", stopPresentScreenMode);
    } else {
      controls.innerHTML = `
        <button data-act="prev">← ${t("prev")}</button>
        <button data-act="blank">${t("blank")}</button>
        <button data-act="exit">${t("exit")}</button>
        <button data-act="next">${t("next")} →</button>
      `;
      controls.querySelector("[data-act='blank']").addEventListener("click", () => document.body.classList.toggle("is-blanked"));
    }
    controls.querySelector("[data-act='prev']").addEventListener("click", navigateBack);
    controls.querySelector("[data-act='next']").addEventListener("click", navigateForward);
    controls.querySelector("[data-act='exit']").addEventListener("click", () => {
      document.body.classList.remove("is-blanked");
      state.presentScreenMode = false;
      switchView("map");
    });
    view.appendChild(controls);
  }

  function renderPresentStage(view, stage) {
    const sec = document.createElement("section");
    sec.className = "present-stage";
    const stages = state.data.stages;
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

    const screens = getScreensForStage(stage);
    if (screens.length) {
      const runBtn = document.createElement("button");
      runBtn.className = "present-run-btn";
      runBtn.textContent = `▷ ${t("run_screens")} · ${t("screens_count", screens.length)}`;
      runBtn.addEventListener("click", startPresentScreenMode);
      sec.appendChild(runBtn);
    }

    view.appendChild(sec);
  }

  function renderPresentScreens(view, stage) {
    const screens = getScreensForStage(stage);
    if (!screens.length) {
      stopPresentScreenMode();
      return;
    }
    state.presentScreenIdx = Math.max(0, Math.min(state.presentScreenIdx, screens.length - 1));
    const screen = screens[state.presentScreenIdx];
    const sec = document.createElement("section");
    sec.className = "present-screens";
    const frame = window.UJWireframe.renderScreen(screen, {
      size: "presenter",
      hotspots: true,
      onJump: () => presentScreenAdvance(),
    });
    if (frame) sec.appendChild(frame);
    const label = document.createElement("div");
    label.className = "present-screen-label";
    label.textContent = `${state.presentScreenIdx + 1}/${screens.length}  ·  ${screen.title || screen.id}  (${screen.kind || "screen"})`;
    sec.appendChild(label);
    view.appendChild(sec);
  }

  function startPresentScreenMode() {
    const stage = state.data?.stages?.[state.presentIdx];
    if (!stage) return;
    const screens = getScreensForStage(stage);
    if (!screens.length) return;
    state.presentScreenMode = true;
    state.presentScreenIdx = 0;
    renderPresent();
    // Update hash
    let hash = `#present/${stage.id}/screens`;
    if (location.hash !== hash) history.replaceState(null, "", hash);
  }

  function stopPresentScreenMode() {
    state.presentScreenMode = false;
    renderPresent();
    const stage = state.data?.stages?.[state.presentIdx];
    let hash = stage ? `#present/${stage.id}` : "#present";
    if (location.hash !== hash) history.replaceState(null, "", hash);
  }

  function presentScreenAdvance() {
    const stage = state.data?.stages?.[state.presentIdx];
    if (!stage) return;
    const screens = getScreensForStage(stage);
    if (!screens.length) return;
    const currentScreen = screens[state.presentScreenIdx];
    const def = (currentScreen?.transitions || []).find(t => t.is_default);
    if (def) {
      const idx = screens.findIndex(s => s.id === def.to_screen);
      if (idx >= 0) {
        state.presentScreenIdx = idx;
        renderPresent();
        return;
      }
    }
    if (state.presentScreenIdx < screens.length - 1) {
      state.presentScreenIdx += 1;
      renderPresent();
    } else {
      // End of screen flow — advance to next stage's stage view automatically
      if (state.presentIdx < state.data.stages.length - 1) {
        state.presentIdx += 1;
        state.presentScreenMode = false;
        renderPresent();
      }
    }
  }

  function presentScreenRewind() {
    if (state.presentScreenIdx > 0) {
      state.presentScreenIdx -= 1;
      renderPresent();
    } else {
      stopPresentScreenMode();
    }
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
    state.data = data || { title: "Untitled", language: "en", personas: [], stages: [], screens: [] };
    state.design = design;
    state.t = I18N[state.data.language] || I18N.en;
    rebuildIndexes();

    applyDesignTokens(design);
    setupTopbar();
    setupShortcuts();
    setMeta();
    applyHashRoute();
    window.addEventListener("hashchange", applyHashRoute);
  }

  /* ---------- Minimal YAML-frontmatter extractor ---------- */

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
