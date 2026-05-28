/* ============================================================
   user-journey wireframe renderer (v3 — canvas mode)

   Renders a `screen` from journey.json into a real-looking lo-fi
   mock inside a colored "state card" — the outer card whose color
   depends on `screen.state` (default | loading | success | error |
   warning), like the Miro user-journey reference.

   Public API (window.UJWireframe):

     renderScreenCard(screen) -> HTMLElement
       Returns the outer state card containing the wireframe + the
       card header (with screen title + kind + annotations + the
       triangle markers from screen.annotations[]).

     getElementAnchor(cardEl, elementId, side?) -> {x, y, side} | null
       Resolves an `<element-id>` (or null for "whole screen") to a
       world-space anchor point. Side hint: "top" | "right" |
       "bottom" | "left" — used by arrows.js to bias curve direction.

     getElementRect(cardEl, elementId) -> {left, top, width, height,
                                            anchorSide, target} | null
       Returns the element's world-space rect via
       getBoundingClientRect (which is robust against flex/grid
       layouts where `offsetParent` jumps over intermediate boxes).
       Used by render.js to make smart side decisions: anchor on the
       element's natural side when it faces the target, or escape to
       the screen edge at the element's row when it doesn't.

     iconGlyph(name) -> string

   No deps. ES2017+.
   ============================================================ */
(function () {
  "use strict";

  /* ---------- Device frames --------------------------------- */

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

  /* ---------- DOM helpers ----------------------------------- */

  function el(tag, className, text) {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  /* ---------- Icon vocabulary ------------------------------- */

  const ICON_MAP = {
    back: "‹", more: "⋯", search: "⌕", share: "↗", favorite: "♡",
    menu: "≡", close: "✕", settings: "⚙", filter: "▽", add: "+",
    check: "✓", info: "ⓘ", warning: "⚠", error: "✕",
  };

  function iconGlyph(name) {
    if (!name) return "";
    if (Object.prototype.hasOwnProperty.call(ICON_MAP, name)) return ICON_MAP[name];
    return String(name);
  }

  /* ---------- Element rendering ----------------------------- */

  function renderElement(node) {
    if (!node || typeof node !== "object") return null;
    const type = node.type;
    let n = null;
    switch (type) {
      case "stack":
      case "grid":
      case "row":
        n = renderContainer(node);
        break;
      case "header":          n = renderHeader(node);          break;
      case "app-bar":         n = renderAppBar(node);          break;
      case "section":         n = renderSection(node);         break;
      case "section-header":  n = renderSectionHeader(node);   break;
      case "text":            n = renderText(node);            break;
      case "button":          n = renderButton(node);          break;
      case "keypad-button":   n = renderKeypadButton(node);    break;
      case "icon-button":     n = renderIconButton(node);      break;
      case "cta":             n = renderButton({ ...node, type: "button" }); break;
      case "form-field":      n = renderFormField(node);       break;
      case "search-bar":      n = renderSearchBar(node);       break;
      case "list":            n = renderList(node);            break;
      case "list-item":       n = renderListItem(node);        break;
      case "card":            n = renderCard(node);            break;
      case "image-placeholder": n = renderImage(node);         break;
      case "tab-bar":         n = renderTabBar(node);          break;
      case "chip":            n = renderChip(node);            break;
      case "toast":           n = renderToast(node);           break;
      case "progress":        n = renderProgress(node);        break;
      case "divider":         n = renderDivider(node);         break;
      case "badge":           n = renderBadge(node);           break;
      case "spacer":          n = renderSpacer(node);          break;
      case "side-key-rail":   n = renderSideKeyRail(node);     break;
      case "hardware-slot":   n = renderHardwareSlot(node);    break;
      case "key-value":       n = renderKeyValue(node);        break;
      case "key-value-list":  n = renderKeyValueList(node);    break;
      case "stat-tile":       n = renderStatTile(node);        break;
      case "alert":           n = renderAlert(node);           break;
      case "step-indicator":  n = renderStepIndicator(node);   break;
      case "empty-state":     n = renderEmptyState(node);      break;
      case "footer-bar":      n = renderFooterBar(node);       break;
      case "avatar":          n = renderAvatar(node);          break;
      case "metric":          n = renderStatTile(node);        break;
      default: return null;
    }
    if (!n) return null;
    if (node.span && Number.isFinite(node.span)) {
      n.style.gridColumn = `span ${node.span}`;
    }
    if (node.id) n.dataset.id = node.id;
    if (node.state) n.classList.add("wf-state-" + node.state);
    if (node.disabled) n.classList.add("wf-disabled");
    if (node.interactive) {
      n.classList.add("wf-interactive");
      n.setAttribute("data-canvas-item", "interactive");
    }
    return n;
  }

  function renderContainer(node) {
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
      const c = renderElement(child);
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

  function renderList(node) {
    const wrap = el("div", "wf-list");
    (node.elements || node.items || []).forEach((item, idx) => {
      let n = null;
      if (typeof item === "string") {
        n = el("div", "wf-list-item", item);
      } else {
        n = renderElement(item);
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

  function renderCard(node) {
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
          if (act.interactive) {
            b.classList.add("wf-interactive");
            b.setAttribute("data-canvas-item", "interactive");
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
    return el("div", `wf-chip wf-chip-${variant}`, node.label || "");
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

  /* ---------- Composition primitives -----------------------
     These wrap raw atoms into the design patterns reviewers
     expect on real screens: app bars, grouped sections, key-
     value rows, stat tiles, alerts, step indicators, empty
     states, fixed bottom action bars. Encoding them as first-
     class primitives keeps the JSON declarative AND nudges
     the AI to think in patterns, not atoms.
     ----------------------------------------------------------- */

  function renderAppBar(node) {
    const variant = node.variant === "prominent" ? "prominent" : "default";
    const div = el("div", `wf-app-bar wf-app-bar-${variant}`);
    const left = el("div", "wf-app-bar-left");
    if (node.back) left.appendChild(el("span", "wf-app-bar-back", "‹"));
    if (node.icon) left.appendChild(el("span", "wf-app-bar-icon", iconGlyph(node.icon)));
    const titleBlock = el("div", "wf-app-bar-title-block");
    if (node.title) titleBlock.appendChild(el("div", "wf-app-bar-title", node.title));
    if (node.subtitle) titleBlock.appendChild(el("div", "wf-app-bar-subtitle", node.subtitle));
    left.appendChild(titleBlock);
    div.appendChild(left);
    if (Array.isArray(node.actions) && node.actions.length) {
      const right = el("div", "wf-app-bar-actions");
      node.actions.forEach((a) => {
        const wrap = el("span", "wf-app-bar-action");
        wrap.textContent = iconGlyph(typeof a === "string" ? a : (a.icon || ""));
        if (typeof a === "object" && a.id) wrap.dataset.id = a.id;
        if (typeof a === "object" && a.badge != null) {
          wrap.appendChild(el("span", "wf-app-bar-action-badge", String(a.badge)));
        }
        right.appendChild(wrap);
      });
      div.appendChild(right);
    }
    return div;
  }

  function renderSection(node) {
    // A section is a grouped content block with optional header.
    // It can render flat (transparent) or as a surface (white card
    // with subtle border + padding). Children render inside.
    const variant = node.variant === "surface" ? "surface" : "flat";
    const div = el("div", `wf-section wf-section-${variant}`);
    if (node.title || node.subtitle || node.action) {
      const head = el("div", "wf-section-head");
      const titleStack = el("div", "wf-section-title-stack");
      if (node.title) titleStack.appendChild(el("div", "wf-section-title", node.title));
      if (node.subtitle) titleStack.appendChild(el("div", "wf-section-subtitle", node.subtitle));
      head.appendChild(titleStack);
      if (node.action) {
        const a = el("div", "wf-section-action");
        a.textContent = typeof node.action === "string" ? node.action : (node.action.label || "");
        if (typeof node.action === "object" && node.action.id) a.dataset.id = node.action.id;
        head.appendChild(a);
      }
      div.appendChild(head);
    }
    const body = el("div", "wf-section-body");
    body.dataset.gap = node.gap || "md";
    (node.elements || []).forEach((child) => {
      const c = renderElement(child);
      if (c) body.appendChild(c);
    });
    div.appendChild(body);
    return div;
  }

  function renderSectionHeader(node) {
    const div = el("div", "wf-section-header");
    if (node.eyebrow) div.appendChild(el("span", "wf-section-header-eyebrow", node.eyebrow));
    if (node.label)   div.appendChild(el("span", "wf-section-header-label",   node.label));
    if (node.trailing) div.appendChild(el("span", "wf-section-header-trailing", node.trailing));
    return div;
  }

  function renderKeyValue(node) {
    const div = el("div", "wf-key-value");
    div.appendChild(el("span", "wf-key-value-key", node.key || ""));
    const v = el("span", "wf-key-value-value", node.value != null ? String(node.value) : "");
    if (node.emphasis) v.classList.add("wf-key-value-emphasis");
    if (node.color && ["primary", "secondary", "error", "success", "warning"].includes(node.color)) {
      v.classList.add(`wf-key-value-color-${node.color}`);
    }
    div.appendChild(v);
    return div;
  }

  function renderKeyValueList(node) {
    const div = el("div", "wf-key-value-list");
    div.dataset.density = node.density || "comfortable";
    (node.items || []).forEach((item, idx) => {
      if (!item || typeof item !== "object") return;
      if (idx > 0) div.appendChild(el("div", "wf-key-value-divider"));
      div.appendChild(renderKeyValue(item));
    });
    return div;
  }

  function renderStatTile(node) {
    const div = el("div", "wf-stat-tile");
    if (node.label) div.appendChild(el("div", "wf-stat-tile-label", node.label));
    const valueWrap = el("div", "wf-stat-tile-value-wrap");
    valueWrap.appendChild(el("span", "wf-stat-tile-value", node.value != null ? String(node.value) : ""));
    if (node.unit) valueWrap.appendChild(el("span", "wf-stat-tile-unit", node.unit));
    div.appendChild(valueWrap);
    if (node.delta != null) {
      const delta = el("div", `wf-stat-tile-delta wf-stat-tile-delta-${node.delta_direction || (parseFloat(node.delta) < 0 ? "down" : "up")}`);
      delta.textContent = String(node.delta);
      div.appendChild(delta);
    }
    if (node.caption) div.appendChild(el("div", "wf-stat-tile-caption", node.caption));
    return div;
  }

  function renderAlert(node) {
    const severity = ["info", "success", "warning", "error"].includes(node.severity)
      ? node.severity : "info";
    const div = el("div", `wf-alert wf-alert-${severity}`);
    div.appendChild(el("span", "wf-alert-icon", iconGlyph(node.icon || severity)));
    const body = el("div", "wf-alert-body");
    if (node.title) body.appendChild(el("div", "wf-alert-title", node.title));
    if (node.message) body.appendChild(el("div", "wf-alert-message", node.message));
    div.appendChild(body);
    if (node.action) {
      const action = el("button", "wf-alert-action");
      action.type = "button";
      action.textContent = typeof node.action === "string" ? node.action : (node.action.label || "");
      if (typeof node.action === "object" && node.action.id) action.dataset.id = node.action.id;
      div.appendChild(action);
    }
    return div;
  }

  function renderStepIndicator(node) {
    const orientation = node.orientation === "vertical" ? "vertical" : "horizontal";
    const div = el("div", `wf-step-indicator wf-step-indicator-${orientation}`);
    const active = Math.max(0, parseInt(node.active != null ? node.active : 0, 10) || 0);
    (node.steps || []).forEach((step, idx) => {
      const status = idx < active ? "done" : (idx === active ? "current" : "todo");
      const dot = el("div", `wf-step-item wf-step-item-${status}`);
      const marker = el("span", "wf-step-marker", String(idx + 1));
      dot.appendChild(marker);
      const labelEl = el("span", "wf-step-label", typeof step === "string" ? step : (step.label || ""));
      dot.appendChild(labelEl);
      div.appendChild(dot);
      if (idx < (node.steps || []).length - 1) {
        div.appendChild(el("div", `wf-step-connector wf-step-connector-${status}`));
      }
    });
    return div;
  }

  function renderEmptyState(node) {
    const div = el("div", "wf-empty-state");
    if (node.icon) div.appendChild(el("div", "wf-empty-state-icon", iconGlyph(node.icon)));
    if (node.title) div.appendChild(el("div", "wf-empty-state-title", node.title));
    if (node.message) div.appendChild(el("div", "wf-empty-state-message", node.message));
    if (node.action) {
      const a = renderButton({
        type: "button",
        label: typeof node.action === "string" ? node.action : (node.action.label || ""),
        variant: "primary",
        id: typeof node.action === "object" ? node.action.id : null,
      });
      if (typeof node.action === "object" && node.action.id) {
        a.dataset.id = node.action.id;
        if (node.action.interactive) {
          a.classList.add("wf-interactive");
          a.setAttribute("data-canvas-item", "interactive");
        }
      }
      div.appendChild(a);
    }
    return div;
  }

  function renderFooterBar(node) {
    // A fixed-bottom action bar (different from tab-bar which is for
    // top-level navigation). Renders a row of buttons separated by a
    // top border, with primary action right-aligned by default.
    const div = el("div", "wf-footer-bar");
    if (node.summary) {
      const sum = el("div", "wf-footer-bar-summary");
      if (typeof node.summary === "string") {
        sum.textContent = node.summary;
      } else {
        if (node.summary.label) sum.appendChild(el("span", "wf-footer-bar-summary-label", node.summary.label));
        if (node.summary.value) sum.appendChild(el("span", "wf-footer-bar-summary-value", node.summary.value));
      }
      div.appendChild(sum);
    }
    const actions = el("div", "wf-footer-bar-actions");
    (node.actions || []).forEach((a) => {
      const btn = renderButton({ ...a, type: "button" });
      if (a.id) btn.dataset.id = a.id;
      if (a.interactive) {
        btn.classList.add("wf-interactive");
        btn.setAttribute("data-canvas-item", "interactive");
      }
      actions.appendChild(btn);
    });
    div.appendChild(actions);
    return div;
  }

  function renderAvatar(node) {
    const size = ["sm", "md", "lg", "xl"].includes(node.size) ? node.size : "md";
    const div = el("div", `wf-avatar wf-avatar-${size}`);
    if (node.image) {
      const img = el("div", "wf-avatar-image");
      img.style.background = node.color || "#94A3B8";
      div.appendChild(img);
    } else {
      const initials = el("div", "wf-avatar-initials");
      initials.textContent = node.initials || (node.label || "?").slice(0, 2).toUpperCase();
      if (node.color) initials.style.background = node.color;
      div.appendChild(initials);
    }
    if (node.label) div.appendChild(el("span", "wf-avatar-label", node.label));
    if (node.subtitle) div.appendChild(el("span", "wf-avatar-subtitle", node.subtitle));
    return div;
  }

  /* ---------- Device-specific elements --------------------- */

  const SLOT_GLYPHS = {
    "card-reader": "▭",
    "cash-out":    "‖‖‖",
    "cash-in":     "‖‖‖",
    "deposit":     "▦",
    "receipt":     "▤",
    "biometric":   "◉",
    "scanner":     "▥",
    "nfc":         "))) ",
    "pin-pad":     "⌗",
    "custom":      "▢",
  };

  function renderSideKeyRail(node) {
    const side = node.side === "left" ? "left" : "right";
    const wrap = el("div", `wf-side-key-rail wf-side-key-rail-${side}`);
    wrap.dataset.side = side;
    if (node.gap) wrap.dataset.gap = node.gap;
    const keys = Array.isArray(node.keys) ? node.keys : [];
    keys.forEach((key) => {
      const variant = ["primary", "secondary", "ghost", "destructive"].includes(key.variant)
        ? key.variant : "secondary";
      const row = el("div", `wf-side-key wf-side-key-${variant}`);
      if (key.id) row.dataset.id = key.id;
      if (key.disabled) row.classList.add("wf-disabled");
      if (key.interactive) {
        row.classList.add("wf-interactive");
        row.setAttribute("data-canvas-item", "interactive");
        row.dataset.anchorSide = side;
      }
      const notch = el("span", "wf-side-key-notch");
      const label = el("span", "wf-side-key-label", key.label || "");
      if (side === "left") {
        row.appendChild(notch);
        row.appendChild(label);
      } else {
        row.appendChild(label);
        row.appendChild(notch);
      }
      wrap.appendChild(row);
    });
    return wrap;
  }

  function renderHardwareSlot(node) {
    const slot = SLOT_GLYPHS[node.slot] ? node.slot : "custom";
    const wrap = el("div", `wf-hardware-slot wf-hardware-slot-${slot}`);
    if (node.id) wrap.dataset.id = node.id;
    if (node.position) wrap.dataset.position = node.position;
    wrap.appendChild(el("span", "wf-hardware-slot-glyph", SLOT_GLYPHS[slot]));
    if (node.label) wrap.appendChild(el("span", "wf-hardware-slot-label", node.label));
    if (node.interactive) {
      wrap.classList.add("wf-interactive");
      wrap.setAttribute("data-canvas-item", "interactive");
      // Anchor side mirrors the slot's bezel position.
      const pos = node.position || "bottom";
      wrap.dataset.anchorSide = pos;
    }
    return wrap;
  }

  /* ---------- Frame + chrome -------------------------------- */

  function renderFrame(screen) {
    const frameClass = frameClassFor(screen.kind);
    const frame = el("div", `wf-frame ${frameClass}`);
    if (screen.kind) frame.dataset.kind = screen.kind;
    const body = el("div", "wf-body");
    const root = renderElement(screen.layout);
    if (root) body.appendChild(root);
    frame.appendChild(body);

    // Resolve chrome: explicit value wins; ATM/kiosk default to "panel"
    // so the chassis is the rule, not the exception.
    let chrome = screen.chrome;
    if (chrome === undefined || chrome === null) {
      chrome = (screen.kind === "atm-screen" || screen.kind === "kiosk-screen")
        ? "panel"
        : "none";
    }
    if (chrome === "panel") {
      return wrapWithDevicePanel(screen, frame);
    }
    return frame;
  }

  function wrapWithDevicePanel(screen, frame) {
    const panel = el("div", `wf-device-panel wf-device-panel-${screen.kind || "atm-screen"}`);
    if (screen.kind) panel.dataset.kind = screen.kind;

    const slots = Array.isArray(screen.hardware) ? screen.hardware : [];

    const topRow = makeBezelRow("top", slots);
    if (topRow) panel.appendChild(topRow);

    const mid = el("div", "wf-device-panel-mid");
    const leftBezel = makeBezelColumn("left", slots);
    if (leftBezel) mid.appendChild(leftBezel);
    mid.appendChild(frame);
    const rightBezel = makeBezelColumn("right", slots);
    if (rightBezel) mid.appendChild(rightBezel);
    panel.appendChild(mid);

    const botRow = makeBezelRow("bottom", slots);
    if (botRow) panel.appendChild(botRow);

    return panel;
  }

  function makeBezelRow(position, slots) {
    const matching = slots.filter(s => s && s.position === position);
    if (!matching.length) return null;
    const row = el("div", `wf-bezel wf-bezel-${position}`);
    matching.forEach(s => row.appendChild(renderHardwareSlot(s)));
    return row;
  }

  function makeBezelColumn(side, slots) {
    const matching = slots.filter(s => s && s.position === side);
    const col = el("div", `wf-bezel wf-bezel-${side}`);
    matching.forEach(s => col.appendChild(renderHardwareSlot(s)));
    return col;
  }

  /* ---------- Outer state card ------------------------------ */

  const VALID_STATES = ["default", "loading", "success", "error", "warning"];

  function renderScreenCard(screen) {
    if (!screen) return null;
    const state = VALID_STATES.includes(screen.state) ? screen.state : "default";
    const card = el("div", `screen-card screen-card-state-${state} screen-card-kind-${screen.kind || "mobile-screen"}`);
    card.setAttribute("data-canvas-screen", "");
    card.setAttribute("data-canvas-item", "screen");
    if (screen.id) card.dataset.screenId = screen.id;
    if (screen.kind) card.dataset.kind = screen.kind;
    card.dataset.state = state;

    // Avoid double-titling: if the layout's first element is an
    // app-bar or header, render the card header as a compact
    // "kind chip" instead of the full title. Otherwise show the
    // full screen title above the frame.
    const layoutFirst = isLayoutHeaderlike(screen.layout);
    const header = el("div",
      layoutFirst ? "screen-card-header screen-card-header-compact" : "screen-card-header");
    if (layoutFirst) {
      // Compact mode: a small kind/state pill on the left, annotations on the right.
      const chip = el("div", "screen-card-chip");
      chip.textContent = compactKindLabel(screen.kind, screen.id);
      header.appendChild(chip);
    } else {
      const titleEl = el("div", "screen-card-title", screen.title || screen.id || "");
      header.appendChild(titleEl);
    }
    if (Array.isArray(screen.annotations) && screen.annotations.length) {
      const annoBar = el("div", "screen-card-annotations");
      screen.annotations.forEach((a) => {
        if (!a || typeof a !== "object") return;
        const n = a.n != null ? String(a.n) : "?";
        const marker = el("div", "screen-card-annotation", n);
        marker.title = a.note || "";
        annoBar.appendChild(marker);
      });
      header.appendChild(annoBar);
    }
    card.appendChild(header);

    const frame = renderFrame(screen);
    if (frame) {
      const frameWrap = el("div", "screen-card-frame");
      frameWrap.appendChild(frame);
      card.appendChild(frameWrap);
    }

    return card;
  }

  /* Return true when the screen's layout begins with a header-like
     element (app-bar / header) — meaning the outer card title would
     visually duplicate it. */
  function isLayoutHeaderlike(layout) {
    if (!layout || typeof layout !== "object") return false;
    const first = (layout.elements || [])[0];
    if (!first || typeof first !== "object") return false;
    return first.type === "app-bar" || first.type === "header";
  }

  /* A short label for the compact card header — meant as
     orientation, not a title. Reads like a Figma frame badge. */
  function compactKindLabel(kind, id) {
    const KIND_LABELS = {
      "mobile-screen":  "Mobile",
      "tablet-screen":  "Tablet",
      "desktop-window": "Desktop",
      "atm-screen":     "ATM",
      "kiosk-screen":   "Kiosk",
      "tv-screen":      "TV",
      "email":          "Email",
      "modal":          "Modal",
      "notification":   "Notification",
    };
    const k = KIND_LABELS[kind] || (kind || "Screen");
    return id ? `${k} · ${id}` : k;
  }

  /* ---------- Anchor resolution ----------------------------- */

  /* Resolve an `<element-id>` (or null) inside `cardEl` to a
     world-space anchor point. `cardEl` is positioned with
     left/top inside the world, so its offsetLeft/offsetTop ARE
     its world position (no parent transforms inside the world). */
  function getElementAnchor(cardEl, elementId, sideHint) {
    if (!cardEl) return null;
    const baseX = cardEl.offsetLeft;
    const baseY = cardEl.offsetTop;
    const w = cardEl.offsetWidth;
    const h = cardEl.offsetHeight;

    if (!elementId) {
      const side = sideHint || "right";
      return anchorFromRect(baseX, baseY, w, h, side);
    }

    const rect = getElementRect(cardEl, elementId);
    if (!rect) {
      return anchorFromRect(baseX, baseY, w, h, sideHint || "right");
    }
    const side = rect.anchorSide || sideHint || "right";
    return anchorFromRect(rect.left, rect.top, rect.width, rect.height, side);
  }

  /* Return the world-space rect + natural anchor side of an element
     inside `cardEl`. The rect is computed via getBoundingClientRect
     (robust against flex/grid layouts where offsetParent jumps) and
     inverse-mapped through the current world transform. Returns null
     if the element cannot be located. */
  function getElementRect(cardEl, elementId) {
    if (!cardEl || !elementId) return null;
    const target = cardEl.querySelector(`[data-id="${cssEscape(elementId)}"]`);
    if (!target) return null;

    // Use getBoundingClientRect on both the card and the target, then
    // express the target's rect relative to the card. Because the
    // entire world is uniformly transformed (translate + uniform
    // scale via canvas.js), the ratio of screen pixels to world
    // pixels is constant — we recover world coords by scaling the
    // screen-space delta back up, then offsetting from the card's
    // world position (which we know exactly via offsetLeft/Top).
    const cardR = cardEl.getBoundingClientRect();
    const tR    = target.getBoundingClientRect();
    const scale = cardR.width / cardEl.offsetWidth;
    if (!isFinite(scale) || scale === 0) return null;

    const left   = cardEl.offsetLeft + (tR.left   - cardR.left) / scale;
    const top    = cardEl.offsetTop  + (tR.top    - cardR.top)  / scale;
    const width  = tR.width  / scale;
    const height = tR.height / scale;
    const anchorSide = target.dataset.anchorSide || null;
    return { left, top, width, height, anchorSide, target };
  }

  function anchorFromRect(x, y, w, h, side) {
    switch (side) {
      case "top":    return { x: x + w / 2, y: y,         side: "top" };
      case "bottom": return { x: x + w / 2, y: y + h,     side: "bottom" };
      case "left":   return { x: x,         y: y + h / 2, side: "left" };
      case "right":
      default:       return { x: x + w,     y: y + h / 2, side: "right" };
    }
  }

  function cssEscape(s) {
    if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
      return CSS.escape(s);
    }
    // Tiny fallback for older browsers — escapes the chars we actually
    // emit as element ids (alphanumerics + hyphens are safe already).
    return String(s).replace(/(["\\\]\[#.:])/g, "\\$1");
  }

  window.UJWireframe = {
    renderScreenCard,
    getElementAnchor,
    getElementRect,
    iconGlyph,
  };
})();
