/* ============================================================
   user-journey sidebar (v3)

   Renders the left-side stage/screen tree. Subscribes to
   UJView for current-screen highlighting and emits screen
   selection back to UJView.

   Public API (window.UJSidebar):
     mount(rootEl, data)   — initial render
     refresh()             — re-render (after data change)
     focusSearch()         — focus the search box
   ============================================================ */
(function () {
  "use strict";

  const STATE_DOT_TITLE = {
    default: "Default state",
    loading: "Loading state",
    success: "Success state",
    error:   "Error state",
    warning: "Warning state",
  };

  let rootEl = null;
  let searchInput = null;
  let stagesEl = null;
  let data = null;
  let filter = "";

  function el(tag, className, text) {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function mount(root, journeyData) {
    rootEl = root;
    data = journeyData || {};
    searchInput = rootEl.querySelector("#sidebar-search-input");
    stagesEl    = rootEl.querySelector("#sidebar-stages");
    if (searchInput) {
      searchInput.addEventListener("input", (ev) => {
        filter = String(ev.target.value || "").trim().toLowerCase();
        render();
      });
    }
    window.UJView.on("screenchange", () => updateActiveState());
    window.UJView.on("modechange",   () => updateActiveState());
    render();
  }

  function refresh() {
    render();
  }

  function focusSearch() {
    if (searchInput) searchInput.focus();
  }

  /* ---------- Rendering ---------------------------------------- */

  function render() {
    if (!stagesEl) return;
    stagesEl.innerHTML = "";

    const screens = (data.screens || []);
    const stages  = (data.stages  || []);
    const stageOrder = stages.map((s) => s && s.id).filter(Boolean);

    // Group screens by stage_id; collect "no stage" bucket at the end.
    const byStage = new Map();
    stageOrder.forEach((sid) => byStage.set(sid, []));
    const orphans = [];
    screens.forEach((s) => {
      if (!s || !s.id) return;
      if (!matchesFilter(s)) return;
      const sid = s.stage_id;
      if (sid && byStage.has(sid)) {
        byStage.get(sid).push(s);
      } else {
        orphans.push(s);
      }
    });

    // Render stages in author order, skipping empty buckets unless
    // the search filter is also empty (so users can still see the
    // full tree by default).
    stages.forEach((stage) => {
      if (!stage || !stage.id) return;
      const stageScreens = byStage.get(stage.id) || [];
      if (stageScreens.length === 0 && filter) return;
      stagesEl.appendChild(renderStage(stage, stageScreens));
    });

    if (orphans.length > 0) {
      stagesEl.appendChild(renderStage({ id: "__orphans", label: "Other screens" }, orphans));
    }

    updateActiveState();
  }

  function matchesFilter(screen) {
    if (!filter) return true;
    const haystack = [
      screen.id, screen.title, screen.kind, screen.state,
      (screen.title_zh || ""), (screen.title_en || ""),
    ].join(" ").toLowerCase();
    return haystack.includes(filter);
  }

  function renderStage(stage, screens) {
    const block = el("div", "sidebar-stage");
    block.dataset.stageId = stage.id;
    const head = el("div", "sidebar-stage-head");
    const label = el("span", "sidebar-stage-label", stage.label || stage.label_zh || stage.id);
    const count = el("span", "sidebar-stage-count", String(screens.length));
    head.appendChild(label);
    head.appendChild(count);
    block.appendChild(head);

    const list = el("ul", "sidebar-screen-list");
    screens.forEach((screen) => {
      list.appendChild(renderScreenItem(screen));
    });
    block.appendChild(list);
    return block;
  }

  function renderScreenItem(screen) {
    const li = el("li", "sidebar-screen-item");
    li.dataset.screenId = screen.id;
    const btn = el("button", "sidebar-screen-btn");
    btn.type = "button";
    btn.setAttribute("data-state", screen.state || "default");
    btn.title = `${screen.title || screen.id} · ${screen.kind || "screen"}`;

    const dot = el("span", `sidebar-screen-dot sidebar-screen-dot-${screen.state || "default"}`);
    dot.title = STATE_DOT_TITLE[screen.state || "default"];
    btn.appendChild(dot);

    const title = el("span", "sidebar-screen-title",
      screen.title || screen.id);
    btn.appendChild(title);

    const kindBadge = el("span", "sidebar-screen-kind", shortKind(screen.kind));
    btn.appendChild(kindBadge);

    btn.addEventListener("click", () => {
      window.UJView.setCurrentScreen(screen.id, { source: "sidebar" });
      // If we're in canvas mode, switch to prototype on click feels
      // too aggressive — instead, just pan/highlight in canvas and
      // switch to prototype mode on DOUBLE click.
      if (window.UJView.getMode() === "prototype") {
        window.UJView.clearHistory();
      }
    });
    btn.addEventListener("dblclick", () => {
      window.UJView.setCurrentScreen(screen.id, { source: "sidebar" });
      window.UJView.setMode("prototype");
    });

    li.appendChild(btn);
    return li;
  }

  function shortKind(kind) {
    const MAP = {
      "mobile-screen":  "Mobile",
      "tablet-screen":  "Tablet",
      "desktop-window": "Desktop",
      "atm-screen":     "ATM",
      "kiosk-screen":   "Kiosk",
      "tv-screen":      "TV",
      "email":          "Email",
      "modal":          "Modal",
      "notification":   "Notif.",
    };
    return MAP[kind] || (kind || "");
  }

  function updateActiveState() {
    if (!stagesEl) return;
    const current = window.UJView.getCurrentScreenId();
    const buttons = stagesEl.querySelectorAll(".sidebar-screen-btn");
    buttons.forEach((b) => b.classList.remove("is-active"));
    if (!current) return;
    const li = stagesEl.querySelector(`.sidebar-screen-item[data-screen-id="${cssEscape(current)}"]`);
    if (li) {
      const btn = li.querySelector(".sidebar-screen-btn");
      if (btn) {
        btn.classList.add("is-active");
        // Keep the active item in view, gently.
        btn.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
      }
    }
  }

  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/(["\\#.()[\]{}><+~*=^$|:?\/])/g, "\\$1");
  }

  /* ---------- Public ------------------------------------------- */

  window.UJSidebar = { mount, refresh, focusSearch };
})();
