/* ============================================================
   user-journey wireframe renderer (v2)

   Renders a `screen` from journey.json (see references/WIREFRAMES.md
   and references/SCHEMA.md) into a real-looking lo-fi mock with
   interactive hotspot overlays driven by `screen.transitions`.

   Public API:
     UJWireframe.renderScreen(screen, options)  -> HTMLElement
     UJWireframe.renderThumbnail(screen)        -> HTMLElement (no hotspots)

   Options:
     options.size       -> "full" (default) | "thumbnail" | "presenter"
     options.onJump     -> function(toScreenId) — called when user clicks
                           an interactive hotspot or "any" overlay
     options.hotspots   -> boolean (default true) — overlay numbered
                           hotspot bubbles on interactive elements

   No deps. Plain ES2017+.
   ============================================================ */
(function () {
  "use strict";

  // ---------- Device frames -------------------------------------------------

  const KINDS = {
    "mobile-screen":  { cls: "wf-mobile-screen",  aspect: "9 / 19.5" },
    "tablet-screen":  { cls: "wf-tablet-screen",  aspect: "3 / 4"    },
    "desktop-window": { cls: "wf-desktop-window", aspect: "16 / 10"  },
    "atm-screen":     { cls: "wf-atm-screen",     aspect: "4 / 3"    },
    "kiosk-screen":   { cls: "wf-kiosk-screen",   aspect: "9 / 16"   },
    "tv-screen":      { cls: "wf-tv-screen",      aspect: "16 / 9"   },
    "email":          { cls: "wf-email",          aspect: "3 / 4"    },
    "modal":          { cls: "wf-modal",          aspect: "4 / 3"    },
    "notification":   { cls: "wf-notification",   aspect: "8 / 1"    },
  };

  function frameClassFor(kind) {
    const entry = KINDS[kind] || KINDS["mobile-screen"];
    return entry.cls;
  }

  // ---------- DOM helpers ---------------------------------------------------

  function el(tag, className, text) {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  // ---------- Icon vocabulary ----------------------------------------------

  const ICON_MAP = {
    back: "‹", more: "⋯", search: "⌕", share: "↗", favorite: "♡",
    menu: "≡", close: "✕", settings: "⚙", filter: "▽", add: "+",
    check: "✓", info: "ⓘ", warning: "⚠", error: "✕",
  };

  function iconGlyph(name) {
    if (!name) return "";
    if (Object.prototype.hasOwnProperty.call(ICON_MAP, name)) return ICON_MAP[name];
    // Treat as raw glyph (e.g. an emoji or unicode char).
    return String(name);
  }

  // ---------- Element rendering --------------------------------------------

  function renderElement(node, ctx) {
    if (!node || typeof node !== "object") return null;
    const type = node.type;
    let n = null;
    switch (type) {
      case "stack":
      case "grid":
      case "row":
        n = renderContainer(node, ctx);
        break;
      case "header":          n = renderHeader(node);          break;
      case "text":            n = renderText(node);            break;
      case "button":          n = renderButton(node);          break;
      case "keypad-button":   n = renderKeypadButton(node);    break;
      case "icon-button":     n = renderIconButton(node);      break;
      case "cta":             n = renderButton({ ...node, type: "button" }); break;
      case "form-field":      n = renderFormField(node);       break;
      case "search-bar":      n = renderSearchBar(node);       break;
      case "list":            n = renderList(node, ctx);       break;
      case "list-item":       n = renderListItem(node);        break;
      case "card":            n = renderCard(node, ctx);       break;
      case "image-placeholder": n = renderImage(node);         break;
      case "tab-bar":         n = renderTabBar(node);          break;
      case "chip":            n = renderChip(node);            break;
      case "toast":           n = renderToast(node);           break;
      case "progress":        n = renderProgress(node);        break;
      case "divider":         n = renderDivider(node);         break;
      case "badge":           n = renderBadge(node);           break;
      case "spacer":          n = renderSpacer(node);          break;
      default: return null;
    }
    if (!n) return null;
    if (node.span && Number.isFinite(node.span)) {
      n.style.gridColumn = `span ${node.span}`;
    }
    if (node.id) n.dataset.id = node.id;
    if (node.state) n.classList.add("wf-state-" + node.state);
    if (node.disabled) n.classList.add("wf-disabled");
    if (node.interactive && ctx && ctx.hotspots !== false) {
      decorateHotspot(n, node, ctx);
    }
    return n;
  }

  function renderContainer(node, ctx) {
    const type = node.type;
    const cls = "wf-" + type;
    const div = el("div", cls);
    const gap = node.gap || "md";
    div.dataset.gap = gap;
    if (type === "grid") {
      const cols = Math.max(1, Math.min(6, parseInt(node.cols || 1, 10) || 1));
      div.style.gridTemplateColumns = `repeat(${cols}, minmax(0, 1fr))`;
    }
    if (type === "row" && node.justify) {
      div.dataset.justify = node.justify;
    }
    (node.elements || []).forEach((child) => {
      const c = renderElement(child, ctx);
      if (c) div.appendChild(c);
    });
    return div;
  }

  function renderHeader(node) {
    const div = el("div", "wf-header");
    const left = el("div", "wf-header-left");
    if (node.back) left.appendChild(el("span", "wf-header-back", "‹"));
    left.appendChild(el("span", "wf-header-title", node.label || ""));
    div.appendChild(left);
    if (node.actions && node.actions.length) {
      const right = el("div", "wf-header-actions");
      node.actions.forEach((a) => {
        right.appendChild(el("span", "wf-header-action", iconGlyph(a)));
      });
      div.appendChild(right);
    }
    return div;
  }

  function renderText(node) {
    const size = ["xl", "lg", "md", "sm"].includes(node.size) ? node.size : "md";
    const weight = node.weight === "bold" ? "bold" : "regular";
    const color = ["primary", "secondary", "error", "success"].includes(node.color)
      ? node.color : "default";
    const cls = `wf-text wf-text-${size} wf-text-${weight} wf-text-color-${color}`;
    return el("div", cls, node.label || "");
  }

  function renderButton(node) {
    const variant = ["primary", "secondary", "ghost", "destructive"].includes(node.variant)
      ? node.variant : "primary";
    const btn = el("button", `wf-button wf-button-${variant}`);
    btn.type = "button";
    if (node.icon) {
      btn.appendChild(el("span", "wf-button-icon", iconGlyph(node.icon)));
    }
    btn.appendChild(el("span", "wf-button-label", node.label || ""));
    if (node.disabled) btn.disabled = true;
    return btn;
  }

  function renderKeypadButton(node) {
    const variant = ["primary", "secondary", "ghost", "destructive"].includes(node.variant)
      ? node.variant : "ghost";
    const btn = el("button", `wf-keypad-button wf-button-${variant}`);
    btn.type = "button";
    btn.textContent = node.label || "";
    if (node.disabled) btn.disabled = true;
    return btn;
  }

  function renderIconButton(node) {
    const btn = el("button", "wf-icon-button");
    btn.type = "button";
    btn.appendChild(el("span", "wf-icon-glyph", iconGlyph(node.icon || "more")));
    if (node.badge !== undefined && node.badge !== null && String(node.badge) !== "") {
      btn.appendChild(el("span", "wf-icon-badge", String(node.badge)));
    }
    if (node.disabled) btn.disabled = true;
    return btn;
  }

  function renderFormField(node) {
    const wrap = el("div", "wf-form-field");
    if (node.label) wrap.appendChild(el("label", "wf-form-label", node.label));
    const input = el("div", "wf-form-input");
    input.textContent = node.prefilled || node.placeholder || "";
    if (!node.prefilled && node.placeholder) input.classList.add("wf-placeholder");
    wrap.appendChild(input);
    if (node.state === "error" && node.validation && node.validation.error_message) {
      wrap.appendChild(el("div", "wf-form-error", node.validation.error_message));
    }
    return wrap;
  }

  function renderSearchBar(node) {
    const wrap = el("div", "wf-search-bar");
    wrap.appendChild(el("span", "wf-search-icon", "⌕"));
    wrap.appendChild(el("span", "wf-search-text", node.label || "Search"));
    return wrap;
  }

  function renderList(node, ctx) {
    const wrap = el("div", "wf-list");
    (node.elements || node.items || []).forEach((item, idx) => {
      let n = null;
      if (typeof item === "string") {
        n = el("div", "wf-list-item", item);
      } else {
        n = renderElement(item, ctx);
      }
      if (n) {
        if (idx > 0) wrap.appendChild(el("div", "wf-list-divider"));
        wrap.appendChild(n);
      }
    });
    return wrap;
  }

  function renderListItem(node) {
    const row = el("div", "wf-list-item");
    if (node.icon) row.appendChild(el("span", "wf-list-icon", iconGlyph(node.icon)));
    const stack = el("div", "wf-list-stack");
    if (node.title) stack.appendChild(el("div", "wf-list-title", node.title));
    if (node.subtitle) stack.appendChild(el("div", "wf-list-subtitle", node.subtitle));
    row.appendChild(stack);
    const trailing = node.trailing;
    if (trailing && trailing !== "none") {
      let trailEl;
      if (trailing === "chevron") {
        trailEl = el("span", "wf-list-trailing wf-chevron", "›");
      } else if (typeof trailing === "string" && trailing.startsWith("badge:")) {
        trailEl = el("span", "wf-list-trailing wf-badge", trailing.slice(6));
      } else if (typeof trailing === "string" && trailing.startsWith("text:")) {
        trailEl = el("span", "wf-list-trailing wf-trailing-text", trailing.slice(5));
      } else {
        trailEl = el("span", "wf-list-trailing", String(trailing));
      }
      row.appendChild(trailEl);
    }
    return row;
  }

  function renderCard(node, ctx) {
    const card = el("div", "wf-card");
    if (node.image) {
      const img = renderImage({ ...node.image, type: "image-placeholder" });
      if (img) card.appendChild(img);
    }
    if (node.title) card.appendChild(el("div", "wf-card-title", node.title));
    if (node.body) card.appendChild(el("div", "wf-card-body", node.body));
    if (node.footer_actions && node.footer_actions.length) {
      const footer = el("div", "wf-card-footer");
      node.footer_actions.forEach((act) => {
        const b = renderButton({ ...act, type: "button" });
        if (b) {
          if (act.id) b.dataset.id = act.id;
          if (act.interactive && ctx && ctx.hotspots !== false) {
            decorateHotspot(b, act, ctx);
          }
          footer.appendChild(b);
        }
      });
      card.appendChild(footer);
    }
    return card;
  }

  function renderImage(node) {
    const ratio = (node.ratio || "16:9").replace(":", "-");
    const div = el("div", `wf-image wf-image-${ratio}`);
    div.textContent = node.label || "Image";
    return div;
  }

  function renderTabBar(node) {
    const bar = el("div", "wf-tab-bar");
    (node.items || []).forEach((item) => {
      const isActive = item.id ? item.id === node.active : false;
      const tab = el("div", "wf-tab" + (isActive ? " is-active" : ""));
      if (item.id) tab.dataset.id = item.id;
      if (item.icon) tab.appendChild(el("span", "wf-tab-icon", iconGlyph(item.icon)));
      if (item.label) tab.appendChild(el("span", "wf-tab-label", item.label));
      if (item.badge !== undefined && item.badge !== null && String(item.badge) !== "") {
        tab.appendChild(el("span", "wf-tab-badge", String(item.badge)));
      }
      bar.appendChild(tab);
    });
    return bar;
  }

  function renderChip(node) {
    const variant = node.variant === "outlined" ? "outlined" : "filled";
    const chip = el("div", `wf-chip wf-chip-${variant}`, node.label || "");
    return chip;
  }

  function renderToast(node) {
    const variant = ["info", "success", "warning", "error"].includes(node.variant)
      ? node.variant : "info";
    return el("div", `wf-toast wf-toast-${variant}`, node.label || "");
  }

  function renderProgress(node) {
    const kind = ["linear", "circular", "indeterminate"].includes(node.kind) ? node.kind : "linear";
    const wrap = el("div", `wf-progress wf-progress-${kind}`);
    if (kind === "linear") {
      const bar = el("div", "wf-progress-bar");
      const fill = el("div", "wf-progress-fill");
      const value = Math.max(0, Math.min(100, Number(node.value) || 0));
      fill.style.width = value + "%";
      bar.appendChild(fill);
      wrap.appendChild(bar);
    } else if (kind === "circular") {
      wrap.appendChild(el("div", "wf-progress-circle"));
    } else {
      wrap.appendChild(el("div", "wf-progress-indeterminate"));
    }
    if (node.label) wrap.appendChild(el("div", "wf-progress-label", node.label));
    return wrap;
  }

  function renderDivider(node) {
    const wrap = el("div", "wf-divider");
    if (node.label) wrap.appendChild(el("span", "wf-divider-label", node.label));
    return wrap;
  }

  function renderBadge(node) {
    const variant = ["accent", "neutral", "success", "warning", "error"].includes(node.variant)
      ? node.variant : "neutral";
    return el("span", `wf-badge wf-badge-${variant}`, node.label || "");
  }

  function renderSpacer(node) {
    return el("div", `wf-spacer-${node.size || "md"}`);
  }

  // ---------- Hotspot decoration -------------------------------------------

  function decorateHotspot(node, srcModel, ctx) {
    node.classList.add("wf-hotspot");
    const matchingTx = ctx.transitionsByElement
      ? ctx.transitionsByElement.get(srcModel.id)
      : null;

    // Numbered bubble
    let n = srcModel.hotspot_number;
    if (n == null) {
      n = ctx.nextHotspotNumber();
    }
    const bubble = el("span", "wf-hotspot-bubble", String(n));
    node.appendChild(bubble);

    // Tooltip card
    if (matchingTx) {
      const tip = el("div", "wf-hotspot-tip");
      tip.appendChild(el("span", "wf-hotspot-tip-arrow", "→"));
      tip.appendChild(el("span", "wf-hotspot-tip-label", matchingTx.label || matchingTx.to_screen));
      const meta = el("span", "wf-hotspot-tip-meta", "trigger: " + (matchingTx.trigger || "tap"));
      tip.appendChild(meta);
      node.appendChild(tip);
      if (matchingTx.is_error_path) node.classList.add("wf-hotspot-error");
      if (ctx.onJump) {
        node.addEventListener("click", (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          ctx.onJump(matchingTx.to_screen, matchingTx);
        });
      }
    } else {
      node.classList.add("wf-hotspot-unconnected");
    }
  }

  // ---------- Public render -------------------------------------------------

  function buildContext(screen, options) {
    const opts = options || {};
    const hotspots = opts.hotspots !== false;
    const transitionsByElement = new Map();
    let anyTx = null;
    (screen.transitions || []).forEach((tx) => {
      if (!tx || typeof tx !== "object") return;
      if (tx.from_element === "any") {
        anyTx = tx;
      } else if (tx.from_element) {
        if (!transitionsByElement.has(tx.from_element)) {
          transitionsByElement.set(tx.from_element, tx);
        }
      }
    });
    let counter = 0;
    return {
      hotspots,
      transitionsByElement,
      anyTx,
      onJump: opts.onJump || null,
      nextHotspotNumber: () => ++counter,
    };
  }

  function renderScreen(screen, options) {
    if (!screen) return null;
    const opts = options || {};
    const size = opts.size || "full";
    const ctx = buildContext(screen, opts);
    const frameClass = frameClassFor(screen.kind);
    const frame = el("div", `wf-frame wf-size-${size} ${frameClass}`);
    if (screen.kind) frame.dataset.kind = screen.kind;
    const body = el("div", "wf-body");
    const root = renderElement(screen.layout, ctx);
    if (root) body.appendChild(root);
    frame.appendChild(body);

    if (ctx.anyTx && ctx.hotspots && opts.onJump) {
      const overlay = el("button", "wf-any-overlay");
      overlay.type = "button";
      overlay.setAttribute("aria-label", ctx.anyTx.label || ("→ " + ctx.anyTx.to_screen));
      overlay.appendChild(el("span", "wf-any-label", ctx.anyTx.label || "Tap anywhere"));
      overlay.addEventListener("click", () => opts.onJump(ctx.anyTx.to_screen, ctx.anyTx));
      frame.appendChild(overlay);
    }
    return frame;
  }

  function renderThumbnail(screen) {
    return renderScreen(screen, { size: "thumbnail", hotspots: false, onJump: null });
  }

  window.UJWireframe = { renderScreen, renderThumbnail, iconGlyph };
})();
