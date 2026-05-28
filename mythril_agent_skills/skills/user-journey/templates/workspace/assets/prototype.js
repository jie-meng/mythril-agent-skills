/* ============================================================
   user-journey prototype view (v3)

   Renders ONE screen at a time at actual scale, surfaces its
   outgoing arrows as clickable hotspots, and keeps a back-stack.

   Public API (window.UJPrototype):
     mount(els)         — wire up DOM (called once at boot)
     refresh()          — re-render the current screen
     focusScreen(id)    — show this screen (also pushes history)
     goBack()           — pop history, return previous screen id
   ============================================================ */
(function () {
  "use strict";

  let els = null;          // { frameEl, breadcrumbEl, arrowsHintEl }
  let elementIdToArrow = new Map();  // for the active screen
  let wholeScreenArrows = [];

  function el(tag, className, text) {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function mount(refs) {
    els = refs;
    window.UJView.on("screenchange", (ev) => {
      if (window.UJView.getMode() !== "prototype") {
        // Re-render lazily when prototype becomes active.
        return;
      }
      render(ev.source === "sidebar" || ev.source === "api");
    });
    window.UJView.on("modechange", (ev) => {
      if (ev.mode === "prototype") render(true);
    });
    window.UJView.on("historychange", () => renderBreadcrumb());
  }

  function refresh() {
    render(false);
  }

  function focusScreen(screenId) {
    if (!screenId) return;
    const current = window.UJView.getCurrentScreenId();
    if (current && current !== screenId) {
      window.UJView.pushHistory(current);
    }
    window.UJView.setCurrentScreen(screenId, { source: "prototype" });
  }

  function goBack() {
    const prev = window.UJView.popHistory();
    if (prev) {
      window.UJView.setCurrentScreen(prev, { source: "prototype-back" });
    }
    return prev;
  }

  /* ---------- Rendering ---------------------------------------- */

  function render(forceFresh) {
    if (!els || !els.frameEl) return;
    const screen = window.UJView.getCurrentScreen();
    if (!screen) {
      els.frameEl.innerHTML = "";
      els.arrowsHintEl.innerHTML = "";
      renderBreadcrumb();
      return;
    }
    // Build a fresh card; the wireframe.js renderer already produces
    // the full state-colored frame. We unwrap it slightly so the
    // prototype view shows the screen at actual size.
    els.frameEl.innerHTML = "";
    const card = window.UJWireframe.renderScreenCard(screen);
    if (card) {
      card.classList.add("prototype-card");
      els.frameEl.appendChild(card);
    }
    indexArrows(screen.id);
    annotateHotspots(card);
    renderArrowsHint(screen);
    renderBreadcrumb();
  }

  function indexArrows(screenId) {
    elementIdToArrow.clear();
    wholeScreenArrows = [];
    const arrows = window.UJView.getArrowsFromScreen(screenId);
    arrows.forEach((arrow) => {
      // via_elements[] — every listed element becomes a hotspot
      // routing to the same target. We register the same arrow
      // under each element id so click dispatch picks it up.
      if (Array.isArray(arrow.via_elements) && arrow.via_elements.length) {
        arrow.via_elements.forEach((elementId) => {
          if (!elementId || typeof elementId !== "string") return;
          if (!elementIdToArrow.has(elementId)) {
            elementIdToArrow.set(elementId, []);
          }
          elementIdToArrow.get(elementId).push(arrow);
        });
        // The bundle ALSO surfaces in the right-side arrows hint panel
        // as a single "via N elements" entry — handled in renderArrowHintItem.
        return;
      }
      const addr = String(arrow.from || "");
      const parts = addr.split("#");
      if (parts.length === 2) {
        const elementId = parts[1];
        if (!elementIdToArrow.has(elementId)) {
          elementIdToArrow.set(elementId, []);
        }
        elementIdToArrow.get(elementId).push(arrow);
      } else {
        wholeScreenArrows.push(arrow);
      }
    });
  }

  /* Mark elements that own an outgoing arrow as click-through
     hotspots. Click → navigate to arrow.to. */
  function annotateHotspots(cardEl) {
    if (!cardEl) return;
    elementIdToArrow.forEach((arrowList, elementId) => {
      const target = cardEl.querySelector(`[data-id="${cssEscape(elementId)}"]`);
      if (!target) return;
      target.classList.add("prototype-hotspot");
      target.setAttribute("data-prototype-element", elementId);
      target.addEventListener("click", (ev) => {
        ev.stopPropagation();
        ev.preventDefault();
        // If multiple arrows leave this element, prefer is_default,
        // otherwise the first one in document order. (A future UI
        // could show a chooser; for now we pick deterministically.)
        const chosen = arrowList.find((a) => a.is_default === true) || arrowList[0];
        if (chosen) follow(chosen);
      });
    });
  }

  function follow(arrow) {
    const to = String(arrow.to || "");
    const targetScreen = to.split("#")[0];
    if (!targetScreen) return;
    focusScreen(targetScreen);
  }

  /* ---------- Arrows hint panel (right side) ------------------- */

  function renderArrowsHint(screen) {
    if (!els.arrowsHintEl) return;
    els.arrowsHintEl.innerHTML = "";

    const head = el("div", "prototype-arrows-hint-head", "Transitions");
    els.arrowsHintEl.appendChild(head);

    const allArrows = window.UJView.getArrowsFromScreen(screen.id);
    if (allArrows.length === 0) {
      const empty = el("div", "prototype-arrows-hint-empty",
        "No outgoing arrows. This is a terminal screen.");
      els.arrowsHintEl.appendChild(empty);
      return;
    }

    const list = el("ul", "prototype-arrows-hint-list");
    allArrows.forEach((arrow) => {
      list.appendChild(renderArrowHintItem(arrow));
    });
    els.arrowsHintEl.appendChild(list);

    // Auto / timeout arrows have no clickable element on the screen;
    // surface them as a big "Continue" CTA at the bottom of the stage.
    const autoArrow = wholeScreenArrows.find((a) =>
      a.trigger === "auto" || a.trigger === "timeout" || a.is_default === true
    );
    if (autoArrow) {
      const cta = el("button", "prototype-continue-btn");
      cta.type = "button";
      const label = autoArrow.label
        ? `Continue · ${autoArrow.label}`
        : (autoArrow.trigger === "timeout" ? "Continue · timeout" : "Continue");
      cta.textContent = label;
      cta.addEventListener("click", () => follow(autoArrow));
      els.frameEl.appendChild(cta);
    }
  }

  function renderArrowHintItem(arrow) {
    const li = el("li", `prototype-arrows-hint-item kind-${arrow.kind || "default"}`);
    if (arrow.is_default) li.classList.add("is-default");

    const fromEl = el("div", "prototype-arrows-hint-from");
    if (Array.isArray(arrow.via_elements) && arrow.via_elements.length) {
      const n = arrow.via_elements.length;
      fromEl.textContent = `via ${n} element${n === 1 ? "" : "s"}`;
      fromEl.title = arrow.via_elements.map((e) => `#${e}`).join(", ");
    } else {
      const addr = String(arrow.from || "");
      const parts = addr.split("#");
      if (parts.length === 2) {
        fromEl.textContent = `#${parts[1]}`;
      } else {
        fromEl.textContent = "(whole screen)";
      }
    }
    li.appendChild(fromEl);

    const arrowGlyph = el("span", "prototype-arrows-hint-arrow", "→");
    li.appendChild(arrowGlyph);

    const toEl = el("button", "prototype-arrows-hint-to");
    toEl.type = "button";
    const targetScreenId = String(arrow.to || "").split("#")[0];
    const target = window.UJView.getScreen(targetScreenId);
    toEl.textContent = target ? (target.title || target.id) : targetScreenId;
    toEl.addEventListener("click", () => follow(arrow));
    li.appendChild(toEl);

    if (arrow.label) {
      const labelEl = el("div", "prototype-arrows-hint-label", arrow.label);
      li.appendChild(labelEl);
    }
    return li;
  }

  /* ---------- Breadcrumb --------------------------------------- */

  function renderBreadcrumb() {
    if (!els || !els.breadcrumbEl) return;
    els.breadcrumbEl.innerHTML = "";
    const history = window.UJView.getHistory();
    const current = window.UJView.getCurrentScreen();

    // Back button (always rendered; disabled when empty).
    const back = el("button", "prototype-breadcrumb-back");
    back.type = "button";
    back.title = "Back (Backspace)";
    back.textContent = "← Back";
    back.disabled = history.length === 0;
    back.addEventListener("click", goBack);
    els.breadcrumbEl.appendChild(back);

    // Path: history[0] / history[1] / ... / current
    const path = el("ol", "prototype-breadcrumb-path");
    history.forEach((sid, idx) => {
      const s = window.UJView.getScreen(sid);
      const crumb = el("li", "prototype-breadcrumb-crumb");
      const btn = el("button", "prototype-breadcrumb-btn");
      btn.type = "button";
      btn.textContent = s ? (s.title || s.id) : sid;
      btn.addEventListener("click", () => {
        // Rewind to this index: drop everything after `idx` and set current.
        const future = history.slice(0, idx);
        // Replace history wholesale:
        window.UJView.clearHistory();
        future.forEach((f) => window.UJView.pushHistory(f));
        window.UJView.setCurrentScreen(sid, { source: "breadcrumb" });
      });
      crumb.appendChild(btn);
      path.appendChild(crumb);
      const sep = el("li", "prototype-breadcrumb-sep", "›");
      path.appendChild(sep);
    });
    if (current) {
      const here = el("li", "prototype-breadcrumb-current",
        current.title || current.id);
      path.appendChild(here);
    }
    els.breadcrumbEl.appendChild(path);
  }

  /* ---------- Keyboard inside prototype mode ------------------- */

  function installKeyboard() {
    document.addEventListener("keydown", (ev) => {
      if (window.UJView.getMode() !== "prototype") return;
      const target = ev.target;
      const tag = (target && target.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || (target && target.isContentEditable)) {
        return;
      }
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      if (ev.key === "Backspace") {
        ev.preventDefault();
        goBack();
      } else if (ev.key === "Enter") {
        // Follow default arrow if any.
        ev.preventDefault();
        const sid = window.UJView.getCurrentScreenId();
        if (!sid) return;
        const arrows = window.UJView.getArrowsFromScreen(sid);
        const def = arrows.find((a) => a.is_default === true) || arrows[0];
        if (def) follow(def);
      } else if (ev.key === "j" || ev.key === "k") {
        // Next/prev screen in document order.
        ev.preventDefault();
        const all = window.UJView.getAllScreens();
        if (all.length === 0) return;
        const cur = window.UJView.getCurrentScreenId();
        const i = all.findIndex((s) => s.id === cur);
        const step = (ev.key === "j") ? 1 : -1;
        const next = all[(i + step + all.length) % all.length];
        if (next) {
          window.UJView.setCurrentScreen(next.id, { source: "keyboard" });
          window.UJView.clearHistory();
        }
      }
    });
  }

  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/(["\\#.()[\]{}><+~*=^$|:?\/])/g, "\\$1");
  }

  /* ---------- Public ------------------------------------------- */

  window.UJPrototype = { mount, refresh, focusScreen, goBack, installKeyboard };
})();
