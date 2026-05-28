/* ============================================================
   user-journey renderer (v3 — canvas)

   One canvas, no view switching, no inspector. Reads
   journey.json + DESIGN.md tokens and lays out:

     - screen cards (via wireframe.js)
     - arrows between cards (via arrows.js)
     - stickies (free-floating canvas notes)

   on a single infinite, pannable, zoomable surface (via canvas.js).

   Auto-layout: if a screen has explicit `position: {x, y}`, that's
   honored. Otherwise it gets placed in its stage's column. Each
   stage's `stages[]` index drives the column; screens within a
   stage stack vertically in `screens[]` source order.
   ============================================================ */
(function () {
  "use strict";

  /* ---------- Constants ------------------------------------ */

  /* Per-device card widths in world-pixels. MUST stay in lockstep with
     the `.screen-card-kind-*` rules in styles.css — we read the same
     numbers here at layout time so column widths can shrink to the
     content (mobile column ≈ 360px, desktop column ≈ 880px) instead of
     forcing every column to the widest device's width. */
  const SCREEN_KIND_WIDTH = {
    "mobile-screen":   360,
    "kiosk-screen":    400,
    "tablet-screen":   600,
    "atm-screen":      720,
    "desktop-window":  880,
    "tv-screen":       880,
    "email":           600,
    "modal":           520,
    "notification":    720,
  };
  const DEFAULT_CARD_WIDTH = 760;   // fallback when screen.kind is unknown
  const COLUMN_GAP    = 160;   // gap between stage columns (room for arrows)
  const ROW_GAP       = 120;   // gap between screens within a column
  const COLUMN_TOP    = 80;    // top padding inside a column
  const STAGE_HEADER_HEIGHT = 64;

  function widthForKind(kind) {
    const w = SCREEN_KIND_WIDTH[kind];
    return typeof w === "number" ? w : DEFAULT_CARD_WIDTH;
  }

  /* Build a per-column width plan from the actual screens-per-column.
     Returns { columnWidths: Map<colIdx, number>, columnX: Map<colIdx, number> }
     where columnX is the left-edge x coordinate of each column. Every
     layout/header/reflow path reads from this so the columns line up
     and the stage header sits exactly above its screens. */
  function computeColumnPlan(byColumn, totalColumns) {
    const columnWidths = new Map();
    for (let i = 0; i < totalColumns; i += 1) {
      const screens = byColumn.get(i) || [];
      let widest = DEFAULT_CARD_WIDTH;
      let seen = false;
      screens.forEach((s) => {
        const w = widthForKind(s && s.kind);
        if (!seen || w > widest) { widest = w; seen = true; }
      });
      columnWidths.set(i, seen ? widest : DEFAULT_CARD_WIDTH);
    }
    const columnX = new Map();
    let x = 0;
    for (let i = 0; i < totalColumns; i += 1) {
      columnX.set(i, x);
      x += columnWidths.get(i) + COLUMN_GAP;
    }
    return { columnWidths, columnX };
  }

  const I18N = {
    en: {
      help_title: "Canvas shortcuts",
      help_pan:   "Drag empty canvas, or hold Space + drag",
      help_zoom_wheel: "Cmd/Ctrl + wheel · pinch trackpad",
      help_zoom_keys:  "+ / − · 0 reset · 1 to 100%",
      help_fit:   "F — fit all screens to screen",
      help_help:  "H — toggle this panel",
      help_double: "Double-click a screen — zoom to it",
      help_arrows: "Arrows keys — nudge view",
      stage_lbl:  "Stage",
      no_screens: "No screens yet. Add some to `screens[]` in journey.json.",
    },
    zh: {
      help_title: "画布快捷键",
      help_pan:   "拖动空白处,或按住 Space + 拖动",
      help_zoom_wheel: "Cmd/Ctrl + 滚轮 · 触控板捏合",
      help_zoom_keys:  "+ / − · 0 复位 · 1 回到 100%",
      help_fit:   "F — 整张画布自适应",
      help_help:  "H — 显示/隐藏本面板",
      help_double: "双击某个屏 — 缩放并居中",
      help_arrows: "方向键 — 微调视图",
      stage_lbl:  "阶段",
      no_screens: "还没有屏。请在 journey.json 的 `screens[]` 里添加。",
    },
  };

  const state = {
    data: null,
    design: null,
    t: I18N.en,
    canvas: null,
    cardsById: new Map(),
    arrowsSvg: null,
    arrowsLayer: null,
    contentBounds: { x: 0, y: 0, width: 0, height: 0 },
    // { columnWidths: Map<colIdx, number>, columnX: Map<colIdx, number> } —
    // populated on every renderEverything() so reflow + arrow resolution
    // can consult per-column geometry instead of a single global width.
    columnPlan: null,
  };

  function t(key) { return state.t[key] || key; }

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
    // State-card palette. Each state (default/loading/success/error/
    // warning) carries three slots: bg (card background), bd
    // (border / minimap dot), hd (header text). DESIGN.md may
    // override any subset; missing slots fall back to the CSS root
    // defaults. The SEMANTIC role of each state is FIXED — see
    // SKILL.md "Anti-Patterns": red is always error, green is
    // always success, etc. Presets may shift brightness / saturation
    // (e.g. dark themes) but MUST NOT reassign meaning.
    if (design.state && typeof design.state === "object") {
      for (const [stateName, slots] of Object.entries(design.state)) {
        if (!slots || typeof slots !== "object") continue;
        for (const [slot, value] of Object.entries(slots)) {
          if (!value) continue;
          root.style.setProperty(`--state-${stateName}-${slot}`, value);
        }
      }
    }
    // Arrow palette. Same semantic-lock rule applies: success-arrow is
    // always the positive-flow color, error-arrow always the
    // negative-flow color. Themes may tune saturation but NOT swap
    // meanings.
    if (design.arrows && typeof design.arrows === "object") {
      for (const [kind, value] of Object.entries(design.arrows)) {
        if (!value) continue;
        root.style.setProperty(`--arrow-${kind}`, value);
      }
    }
    // Canvas chrome (grid + background). Optional — themes use it to
    // adapt the workspace to dark mode without hijacking state colors.
    if (design.canvas && typeof design.canvas === "object") {
      for (const [token, value] of Object.entries(design.canvas)) {
        if (!value) continue;
        root.style.setProperty(`--canvas-${token}`, value);
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

  /* ---------- Frontmatter parser --------------------------- */

  function parseDesignFrontmatter(md) {
    const m = md.match(/^---\s*\n([\s\S]*?)\n---/);
    if (!m) return null;
    const yaml = m[1];
    const out = {
      colors: {}, typography: {}, rounded: {}, spacing: {},
      state: {}, arrows: {}, canvas: {},
    };
    // Sections that are flat key-value maps (one nesting level).
    const FLAT_SECTIONS = new Set([
      "colors", "rounded", "spacing", "arrows", "canvas",
    ]);
    // Sections that contain a level of named groups (two nesting levels).
    const NESTED_SECTIONS = new Set(["typography", "state"]);
    const ALL_SECTIONS = new Set([...FLAT_SECTIONS, ...NESTED_SECTIONS]);

    let section = null, currentGroup = null;
    const lines = yaml.split("\n");
    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i];
      if (!raw.trim() || raw.trim().startsWith("#")) continue;
      const indent = raw.length - raw.trimStart().length;
      const line = raw.trim();
      if (indent === 0) {
        const [k] = line.split(":");
        if (ALL_SECTIONS.has(k)) {
          section = k;
          currentGroup = null;
        } else {
          section = null;
        }
        continue;
      }
      if (!section) continue;
      const [keyRaw, ...rest] = line.split(":");
      const key = keyRaw.trim();
      const value = rest.join(":").trim();
      if (NESTED_SECTIONS.has(section)) {
        if (indent === 2 && !value) {
          currentGroup = key;
          out[section][currentGroup] = {};
        } else if (indent >= 4 && currentGroup) {
          out[section][currentGroup][key] = stripQuotes(value);
        }
      } else if (FLAT_SECTIONS.has(section)) {
        out[section][key] = stripQuotes(value);
      }
    }
    return out;
  }
  function stripQuotes(s) { return String(s || "").replace(/^["']|["']$/g, ""); }

  /* ---------- Auto-layout ---------------------------------- */

  function computeAutoLayout(data) {
    const stages  = (data && data.stages)  || [];
    const screens = (data && data.screens) || [];

    // Map stage_id → column index. Unknown stage_id → last column.
    const stageIndex = new Map();
    stages.forEach((stage, idx) => {
      if (stage && stage.id) stageIndex.set(stage.id, idx);
    });

    // Group screens by stage column.
    const byColumn = new Map();
    const orphanCol = stages.length; // dedicated trailing column for unstaged screens
    screens.forEach((screen) => {
      const colIdx = stageIndex.has(screen.stage_id)
        ? stageIndex.get(screen.stage_id)
        : orphanCol;
      if (!byColumn.has(colIdx)) byColumn.set(colIdx, []);
      byColumn.get(colIdx).push(screen);
    });

    const plan = computeColumnPlan(byColumn, stages.length + 1);

    // Compute auto position for each screen that has no explicit position.
    // Vertical stacking inside the column is determined by source order.
    const positions = new Map();
    byColumn.forEach((screens, colIdx) => {
      let y = COLUMN_TOP + STAGE_HEADER_HEIGHT;
      screens.forEach((screen) => {
        if (screen.position && typeof screen.position.x === "number"
            && typeof screen.position.y === "number") {
          positions.set(screen.id, { x: screen.position.x, y: screen.position.y });
          return;
        }
        const x = plan.columnX.get(colIdx) || 0;
        positions.set(screen.id, { x, y });
        y += estimateScreenHeight(screen) + ROW_GAP;
      });
    });

    return { positions, stageIndex, columnPlan: plan };
  }

  function estimateScreenHeight(screen) {
    // Conservative defaults so vertically-stacked screens don't overlap.
    // We trust the actual rendered height after layout; this is only used
    // for the initial y bump and gets reconciled in `reflowColumn`.
    const kind = screen.kind || "mobile-screen";
    switch (kind) {
      case "mobile-screen":  return 680;
      case "tablet-screen":  return 720;
      case "desktop-window": return 520;
      case "atm-screen":     return 720;
      case "kiosk-screen":   return 820;
      case "tv-screen":      return 520;
      case "email":          return 540;
      case "modal":          return 420;
      case "notification":   return 200;
      default:               return 600;
    }
  }

  /* ---------- Render --------------------------------------- */

  function renderEverything() {
    const viewport = document.getElementById("canvas-viewport");
    const world    = document.getElementById("canvas-world");
    const headersLayer  = document.getElementById("canvas-headers");
    const screensLayer  = document.getElementById("canvas-screens");
    const arrowsSvg     = document.getElementById("canvas-arrows");
    const stickiesLayer = document.getElementById("canvas-stickies");

    if (!viewport || !world) return;

    // Clear all layers (we re-render from scratch each time).
    headersLayer.innerHTML  = "";
    screensLayer.innerHTML  = "";
    while (arrowsSvg.firstChild) arrowsSvg.removeChild(arrowsSvg.firstChild);
    stickiesLayer.innerHTML = "";
    state.cardsById.clear();

    const data    = state.data || {};
    const screens = data.screens || [];
    const stages  = data.stages  || [];

    // Auto-layout (also gives us the per-column width plan).
    const { positions, columnPlan } = screens.length
      ? computeAutoLayout(data)
      : { positions: new Map(), columnPlan: null };
    state.columnPlan = columnPlan;

    // Stage column headers (visual cue, no interaction). Each header
    // sits exactly above its column with the column's width.
    stages.forEach((stage, idx) => {
      if (!stage) return;
      const header = document.createElement("div");
      header.className = "canvas-stage-header";
      const x = columnPlan ? (columnPlan.columnX.get(idx) || 0) : 0;
      const w = columnPlan ? (columnPlan.columnWidths.get(idx) || DEFAULT_CARD_WIDTH) : DEFAULT_CARD_WIDTH;
      header.style.left = x + "px";
      header.style.width = w + "px";
      header.style.top  = "0px";
      header.innerHTML = `
        <span class="canvas-stage-num">${String(idx + 1).padStart(2, "0")}</span>
        <span class="canvas-stage-label"></span>
        <span class="canvas-stage-summary"></span>
      `;
      header.querySelector(".canvas-stage-label").textContent = stage.label || "";
      header.querySelector(".canvas-stage-summary").textContent = stage.summary || "";
      headersLayer.appendChild(header);
    });

    if (!screens.length) {
      const empty = document.createElement("div");
      empty.className = "canvas-empty";
      empty.textContent = t("no_screens");
      empty.style.left = "0px";
      empty.style.top  = "0px";
      screensLayer.appendChild(empty);
      // Still mark canvas as bootstrapped so user sees the message.
      state.contentBounds = { x: -200, y: -200, width: 600, height: 200 };
      bootstrapCanvasIfNeeded();
      state.canvas.fit(state.contentBounds);
      return;
    }

    screens.forEach((screen) => {
      const card = window.UJWireframe.renderScreenCard(screen);
      if (!card) return;
      const pos = positions.get(screen.id) || { x: 0, y: 0 };
      card.style.left = pos.x + "px";
      card.style.top  = pos.y + "px";
      screensLayer.appendChild(card);
      state.cardsById.set(screen.id, card);
    });

    // After cards are mounted, reflow within each column so siblings don't
    // overlap if a screen ended up taller than `estimateScreenHeight`.
    reflowColumns(data);

    // Stickies.
    (data.stickies || []).forEach((sticky) => {
      if (!sticky || typeof sticky !== "object") return;
      const n = document.createElement("div");
      const color = ["yellow", "orange", "pink", "blue", "green"].includes(sticky.color)
        ? sticky.color : "yellow";
      n.className = `canvas-sticky canvas-sticky-${color}`;
      n.setAttribute("data-canvas-item", "sticky");
      n.style.left = (Number(sticky.x) || 0) + "px";
      n.style.top  = (Number(sticky.y) || 0) + "px";
      n.textContent = sticky.text || "";
      stickiesLayer.appendChild(n);
    });

    // Arrows.
    drawArrows();

    // Compute content bounds for fit-to-screen.
    state.contentBounds = computeContentBounds();

    // Bootstrap canvas controller once.
    bootstrapCanvasIfNeeded();

    // First-time fit so the user opens onto the full graph.
    state.canvas.fit(state.contentBounds);
  }

  function reflowColumns(data) {
    const stages = data.stages || [];
    const screens = data.screens || [];
    const stageIndex = new Map();
    stages.forEach((s, idx) => { if (s && s.id) stageIndex.set(s.id, idx); });
    const orphanCol = stages.length;

    const byColumn = new Map();
    screens.forEach((screen) => {
      const card = state.cardsById.get(screen.id);
      if (!card) return;
      // Screens with explicit position keep their position and are
      // excluded from reflow.
      if (screen.position && typeof screen.position.x === "number"
          && typeof screen.position.y === "number") {
        return;
      }
      const colIdx = stageIndex.has(screen.stage_id)
        ? stageIndex.get(screen.stage_id)
        : orphanCol;
      if (!byColumn.has(colIdx)) byColumn.set(colIdx, []);
      byColumn.get(colIdx).push({ screen, card });
    });

    const plan = state.columnPlan;
    byColumn.forEach((items, colIdx) => {
      let y = COLUMN_TOP + STAGE_HEADER_HEIGHT;
      const x = plan ? (plan.columnX.get(colIdx) || 0) : 0;
      items.forEach(({ card }) => {
        card.style.left = x + "px";
        card.style.top  = y + "px";
        y += (card.offsetHeight || 600) + ROW_GAP;
      });
    });
  }

  function drawArrows() {
    const arrowsSvg = document.getElementById("canvas-arrows");
    const arrows = (state.data && state.data.arrows) || [];
    window.UJArrows.render(arrowsSvg, arrows, {
      getEndpoint(addr, otherAddr) {
        return resolveEndpoint(addr, otherAddr);
      },
    });
  }

  /* Resolve `addr` ("<screen-id>" or "<screen-id>#<element-id>") into
     a world-space anchor point.

     For whole-screen anchors we pick the card edge facing `otherAddr`.

     For element-anchored endpoints we use a two-step strategy:
       1. The element has a natural exit side (data-anchor-side, e.g.
          "left" for a left-rail key, "bottom" for a bottom slot).
       2. If that side ALREADY faces the target, we anchor exactly on
          that side of the element (pinpoint precision).
       3. If the natural side points AWAY from the target, we project
          the anchor to the screen edge that DOES face the target,
          at the element's row (Y for left/right escape) or column
          (X for top/bottom escape). The arrow still visually
          originates from the element's row, but exits the screen
          cleanly instead of looping back through it.
       4. We tag the result with `viaElement` so fan-out treats this
          as still being an "element-bound" point (no further fanning).
  */
  function resolveEndpoint(addr, otherAddr) {
    if (!addr) return null;
    const parts = String(addr).split("#");
    const screenId = parts[0];
    const elementId = parts[1] || null;
    const card = state.cardsById.get(screenId);
    if (!card) return null;

    const otherCard = otherAddr
      ? state.cardsById.get(String(otherAddr).split("#")[0])
      : null;

    // Whole-screen anchor — pick the side facing the other endpoint.
    if (!elementId) {
      const side = pickFacingSide(card, otherCard);
      const anchor = window.UJWireframe.getElementAnchor(card, null, side);
      if (!anchor) return null;
      anchor.screenId = screenId;
      anchor.isElement = false;
      return anchor;
    }

    // Element anchor — get the element's exact rect first.
    const elRect = window.UJWireframe.getElementRect(card, elementId);
    if (!elRect) {
      // Element id not found — fall back to whole-screen anchor.
      const side = pickFacingSide(card, otherCard);
      const anchor = window.UJWireframe.getElementAnchor(card, null, side);
      if (!anchor) return null;
      anchor.screenId = screenId;
      anchor.isElement = false;
      return anchor;
    }

    const naturalSide = elRect.anchorSide || pickFacingSide(card, otherCard);
    const facingSide = pickFacingSide(card, otherCard);

    // Best case — natural side ALSO faces the target. Anchor pinpoint
    // on the element's edge.
    if (naturalSide === facingSide || isSameAxis(naturalSide, facingSide) && otherCard == null) {
      const pt = pointOnRectSide(elRect, naturalSide);
      return {
        x: pt.x, y: pt.y, side: naturalSide,
        screenId, isElement: true,
      };
    }

    // Mismatch — escape through the screen edge that faces the
    // target, at the element's row/column. This keeps the arrow
    // visually originating from the element while routing OUT of
    // the source screen cleanly (no U-turn through the body).
    const cardRect = {
      left: card.offsetLeft,
      top:  card.offsetTop,
      right: card.offsetLeft + card.offsetWidth,
      bottom: card.offsetTop + card.offsetHeight,
    };
    const elCenterY = elRect.top + elRect.height / 2;
    const elCenterX = elRect.left + elRect.width / 2;
    let x, y;
    if (facingSide === "right") {
      x = cardRect.right; y = elCenterY;
    } else if (facingSide === "left") {
      x = cardRect.left;  y = elCenterY;
    } else if (facingSide === "bottom") {
      x = elCenterX; y = cardRect.bottom;
    } else {
      x = elCenterX; y = cardRect.top;
    }
    return {
      x, y, side: facingSide,
      screenId, isElement: true,
    };
  }

  /* Returns true when two sides share the same axis (left/right or
     top/bottom). Used to decide whether an anchor side mismatch is
     a perpendicular "still ok" hit or a real flip. */
  function isSameAxis(a, b) {
    if (a === "left" || a === "right") return b === "left" || b === "right";
    return b === "top" || b === "bottom";
  }

  function pointOnRectSide(r, side) {
    switch (side) {
      case "right":  return { x: r.left + r.width, y: r.top + r.height / 2 };
      case "left":   return { x: r.left,           y: r.top + r.height / 2 };
      case "top":    return { x: r.left + r.width / 2, y: r.top };
      case "bottom": return { x: r.left + r.width / 2, y: r.top + r.height };
      default:       return { x: r.left + r.width, y: r.top + r.height / 2 };
    }
  }

  /* Pick whichever edge of `card` most directly faces `otherCard`.
     Falls back to "right" when there's no other card. */
  function pickFacingSide(card, otherCard) {
    if (!otherCard) return "right";
    const cx = card.offsetLeft + card.offsetWidth / 2;
    const cy = card.offsetTop  + card.offsetHeight / 2;
    const ox = otherCard.offsetLeft + otherCard.offsetWidth / 2;
    const oy = otherCard.offsetTop  + otherCard.offsetHeight / 2;
    const dx = ox - cx;
    const dy = oy - cy;
    if (Math.abs(dx) >= Math.abs(dy)) {
      return dx >= 0 ? "right" : "left";
    }
    return dy >= 0 ? "bottom" : "top";
  }

  function computeContentBounds() {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    function include(x, y, w, h) {
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x + w > maxX) maxX = x + w;
      if (y + h > maxY) maxY = y + h;
    }
    state.cardsById.forEach((card) => {
      include(card.offsetLeft, card.offsetTop, card.offsetWidth, card.offsetHeight);
    });
    document.querySelectorAll(".canvas-stage-header").forEach((h) => {
      include(h.offsetLeft, h.offsetTop, h.offsetWidth, h.offsetHeight);
    });
    document.querySelectorAll(".canvas-sticky").forEach((n) => {
      include(n.offsetLeft, n.offsetTop, n.offsetWidth, n.offsetHeight);
    });
    if (!isFinite(minX)) {
      return { x: 0, y: 0, width: 800, height: 600 };
    }
    return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
  }

  function bootstrapCanvasIfNeeded() {
    if (state.canvas) return;
    const viewport = document.getElementById("canvas-viewport");
    const world    = document.getElementById("canvas-world");
    state.canvas = window.UJCanvas.create({
      viewport,
      world,
      onChange({ zoom }) {
        const z = document.getElementById("zoom-readout");
        if (z) z.textContent = Math.round(zoom * 100) + "%";
      },
      onFitRequest() {
        return state.contentBounds;
      },
      onHelpToggle() {
        toggleHelpOverlay();
      },
      onScreenDoubleClick(screenId, card) {
        if (!card) return;
        // Two things at once: zoom into the card AND mark this as
        // the current screen so prototype view + sidebar light up.
        if (screenId && window.UJView) {
          window.UJView.setCurrentScreen(screenId, { source: "canvas-dblclick" });
        }
        const rect = {
          x: card.offsetLeft,
          y: card.offsetTop,
          width:  card.offsetWidth,
          height: card.offsetHeight,
        };
        state.canvas.fit(rect, { padding: 80 });
      },
    });
  }

  /* ---------- Help overlay --------------------------------- */

  function toggleHelpOverlay() {
    const overlay = document.getElementById("help-overlay");
    if (!overlay) return;
    overlay.hidden = !overlay.hidden;
  }

  function populateHelpOverlay() {
    const overlay = document.getElementById("help-overlay");
    if (!overlay) return;
    overlay.innerHTML = `
      <div class="help-card" data-no-pan>
        <header class="help-card-header">
          <strong>${t("help_title")}</strong>
          <button type="button" class="help-close" aria-label="Close" data-no-pan>✕</button>
        </header>
        <ul class="help-list">
          <li><kbd>drag</kbd> ${t("help_pan")}</li>
          <li><kbd>scroll</kbd> ${t("help_zoom_wheel")}</li>
          <li><kbd>+</kbd><kbd>−</kbd><kbd>0</kbd> ${t("help_zoom_keys")}</li>
          <li><kbd>F</kbd> ${t("help_fit")}</li>
          <li><kbd>H</kbd> ${t("help_help")}</li>
          <li><kbd>dblclick</kbd> ${t("help_double")}</li>
          <li><kbd>↑↓←→</kbd> ${t("help_arrows")}</li>
        </ul>
      </div>
    `;
    overlay.querySelector(".help-close").addEventListener("click", () => {
      overlay.hidden = true;
    });
  }

  /* ---------- Topbar --------------------------------------- */

  function setupTopbar() {
    const fitBtn = document.getElementById("fit-btn");
    if (fitBtn) {
      fitBtn.addEventListener("click", () => {
        if (state.canvas) state.canvas.fit(state.contentBounds);
      });
    }
    const resetBtn = document.getElementById("reset-btn");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        if (state.canvas) state.canvas.fit(state.contentBounds);
      });
    }
    const zoomInBtn = document.getElementById("zoom-in-btn");
    if (zoomInBtn) {
      zoomInBtn.addEventListener("click", () => {
        if (state.canvas) state.canvas.zoomCenter(1.2);
      });
    }
    const zoomOutBtn = document.getElementById("zoom-out-btn");
    if (zoomOutBtn) {
      zoomOutBtn.addEventListener("click", () => {
        if (state.canvas) state.canvas.zoomCenter(1 / 1.2);
      });
    }
    const helpBtn = document.getElementById("help-btn");
    if (helpBtn) {
      helpBtn.addEventListener("click", () => toggleHelpOverlay());
    }
  }

  /* ---------- Meta + bootstrap ----------------------------- */

  function setMeta() {
    if (state.data && state.data.title) {
      document.getElementById("topbar-title").textContent = state.data.title;
      document.title = state.data.title;
    }
  }

  function setupViewSwitcher() {
    const canvasBtn    = document.getElementById("view-canvas-btn");
    const prototypeBtn = document.getElementById("view-prototype-btn");
    if (!canvasBtn || !prototypeBtn) return;

    function activateButton(mode) {
      [canvasBtn, prototypeBtn].forEach((b) => {
        const isActive = b.dataset.view === mode;
        b.classList.toggle("is-active", isActive);
        b.setAttribute("aria-selected", String(isActive));
      });
    }
    function activatePane(mode) {
      document.querySelectorAll(".view-pane").forEach((p) => {
        const isActive = p.dataset.view === mode;
        p.classList.toggle("is-active", isActive);
        p.hidden = !isActive;
      });
      const zoomGroup = document.getElementById("zoom-controls");
      const fitBtn    = document.getElementById("fit-btn");
      if (zoomGroup) zoomGroup.hidden = (mode !== "canvas");
      if (fitBtn)    fitBtn.hidden    = (mode !== "canvas");
    }
    canvasBtn.addEventListener("click",    () => window.UJView.setMode("canvas"));
    prototypeBtn.addEventListener("click", () => window.UJView.setMode("prototype"));
    window.UJView.on("modechange", ({ mode }) => {
      activateButton(mode);
      activatePane(mode);
      // When switching to canvas, ensure layout is up to date and
      // pan/highlight the current screen if any.
      if (mode === "canvas") {
        if (state.canvas && state.contentBounds) {
          // Don't auto-fit; preserve the user's view. Only highlight.
          highlightCurrentScreenInCanvas();
        }
      }
    });
    // Initial pane visibility.
    activateButton(window.UJView.getMode());
    activatePane(window.UJView.getMode());
  }

  function highlightCurrentScreenInCanvas() {
    const current = window.UJView.getCurrentScreenId();
    document.querySelectorAll(".screen-card.is-focused")
      .forEach((c) => c.classList.remove("is-focused"));
    if (!current) return;
    const card = state.cardsById.get(current);
    if (card) card.classList.add("is-focused");
  }

  async function init() {
    let data = await loadJSONFile("journey.json");
    if (!data) data = loadInlineJSON("journey-data");
    let design = null;
    const designMd = await fetchText("DESIGN.md");
    if (designMd) design = parseDesignFrontmatter(designMd);
    if (!design) design = loadInlineJSON("design-tokens");

    state.data = data || {
      title: "Untitled",
      language: "en",
      personas: [],
      stages: [],
      screens: [],
      arrows: [],
      stickies: [],
    };
    state.design = design;
    state.t = I18N[state.data.language] || I18N.en;

    applyDesignTokens(design);
    setMeta();
    setupTopbar();
    populateHelpOverlay();

    // Bring up the view layer + sidebar + prototype BEFORE canvas
    // render so they can listen for events.
    window.UJView.init(state.data);
    window.UJView.installKeyboard();
    if (window.UJSidebar) {
      const sidebar = document.getElementById("sidebar");
      window.UJSidebar.mount(sidebar, state.data);
    }
    if (window.UJPrototype) {
      window.UJPrototype.mount({
        frameEl:      document.getElementById("prototype-frame"),
        breadcrumbEl: document.getElementById("prototype-breadcrumb"),
        arrowsHintEl: document.getElementById("prototype-arrows-hint"),
      });
      window.UJPrototype.installKeyboard();
    }
    if (window.UJMinimap) {
      window.UJMinimap.mount({ state });
    }
    setupViewSwitcher();

    // Bridge canvas <-> view layer: a canvas double-click sets current screen.
    window.UJView.on("screenchange", () => highlightCurrentScreenInCanvas());

    renderEverything();

    // Re-fit on window resize so the canvas stays sensible.
    window.addEventListener("resize", () => {
      if (state.canvas && window.UJView.getMode() === "canvas") {
        // Only re-fit when canvas is the active view, so we don't
        // disturb the user's prototype focus.
        state.canvas.fit(state.contentBounds);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
