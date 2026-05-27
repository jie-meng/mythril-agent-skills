/* ============================================================
   user-journey wireframe renderer
   Turns a wireframe JSON block (see references/WIREFRAMES.md)
   into a small lo-fi mock element. Vanilla JS, no deps.
   ============================================================ */
(function () {
  "use strict";

  const KINDS = {
    "mobile-screen": "wf-mobile-screen",
    "tablet-screen": "wf-tablet-screen",
    "desktop-window": "wf-desktop-window",
    "email": "wf-email",
    "modal": "wf-modal",
    "notification": "wf-notification",
  };

  function el(tag, className, text) {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function escapeHTML(s) {
    return String(s || "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    }[c]));
  }

  function renderRow(row) {
    if (!row || typeof row !== "object") return null;
    switch (row.type) {
      case "header": return renderHeader(row);
      case "search-bar": return el("div", "wf-row wf-search", row.label || "Search...");
      case "text": return renderText(row);
      case "list": return renderList(row);
      case "card": return renderCard(row);
      case "image-placeholder": return renderImage(row);
      case "form-field": return renderForm(row);
      case "cta": return renderCTA(row);
      case "tab-bar": return renderTabBar(row);
      case "toast": return renderToast(row);
      case "spacer": return el("div", `wf-row wf-spacer-${row.size || "md"}`);
      default: return null;
    }
  }

  function renderHeader(row) {
    const div = el("div", "wf-row wf-header");
    const left = el("span");
    if (row.back) left.textContent = "‹ ";
    left.textContent += row.label || "";
    div.appendChild(left);
    if (row.actions && row.actions.length) {
      const right = el("span", "wf-header-actions");
      row.actions.forEach(a => { right.appendChild(el("span", null, iconGlyph(a))); });
      div.appendChild(right);
    }
    return div;
  }

  function iconGlyph(name) {
    const map = {
      back: "‹", more: "⋯", search: "⌕", share: "↗", favorite: "♡",
      menu: "≡", close: "✕", settings: "⚙", filter: "▽", add: "+",
    };
    return map[name] || "◇";
  }

  function renderText(row) {
    const size = row.size === "lg" ? "lg" : row.size === "sm" ? "sm" : "md";
    const cls = "wf-row wf-text-" + size + (row.weight === "bold" ? " wf-bold" : "");
    return el("div", cls, row.label || "");
  }

  function renderList(row) {
    const wrap = el("div", "wf-row wf-list");
    (row.items || []).forEach(item => {
      wrap.appendChild(el("div", "wf-list-item", item));
    });
    return wrap;
  }

  function renderCard(row) {
    const card = el("div", "wf-row wf-card");
    if (row.title) card.appendChild(el("div", "wf-card-title", row.title));
    if (row.body) card.appendChild(el("div", "wf-card-body", row.body));
    return card;
  }

  function renderImage(row) {
    const ratio = (row.ratio || "16:9").replace(":", "-");
    const div = el("div", `wf-row wf-image wf-image-${ratio}`);
    div.textContent = row.label || "Image";
    return div;
  }

  function renderForm(row) {
    const wrap = el("div", "wf-row wf-form");
    if (row.label) wrap.appendChild(el("div", "wf-form-label", row.label));
    wrap.appendChild(el("div", "wf-form-input", row.placeholder || ""));
    return wrap;
  }

  function renderCTA(row) {
    const variant = row.variant === "secondary" ? "wf-cta-secondary"
      : row.variant === "ghost" ? "wf-cta-ghost"
      : "wf-cta-primary";
    return el("div", `wf-row wf-cta ${variant}`, row.label || "Action");
  }

  function renderTabBar(row) {
    const bar = el("div", "wf-row wf-tab-bar");
    (row.items || []).forEach(item => {
      const tab = el("div", "wf-tab" + (item === row.active ? " is-active" : ""), item);
      bar.appendChild(tab);
    });
    return bar;
  }

  function renderToast(row) {
    const variant = ["info", "success", "warning", "error"].includes(row.variant) ? row.variant : "info";
    return el("div", `wf-row wf-toast wf-toast-${variant}`, row.label || "");
  }

  function render(wireframe) {
    const kind = wireframe && wireframe.kind;
    const frameClass = KINDS[kind] || "wf-mobile-screen";
    const frame = el("div", "wf-frame " + frameClass);
    if (wireframe?.title) {
      const t = el("div", "wf-row wf-header", wireframe.title);
      frame.appendChild(t);
    }
    const body = el("div", "wf-body");
    (wireframe?.elements || []).forEach(row => {
      const r = renderRow(row);
      if (r) body.appendChild(r);
    });
    frame.appendChild(body);
    return frame;
  }

  window.UJWireframe = { render };
})();
