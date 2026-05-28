/* ============================================================
   user-journey minimap (v3)

   Bottom-right floating panel showing the whole canvas at a
   glance, with a rectangle indicating the current viewport.
   Click anywhere on the minimap to pan there.

   Public API (window.UJMinimap):
     mount({ state })   — one-time mount; reads canvas state lazily
     refresh()          — re-render after layout changes
   ============================================================ */
(function () {
  "use strict";

  const W = 200;   // minimap inner width in CSS px
  const H = 140;   // minimap inner height in CSS px

  let mounted = false;
  let canvasEl = null;
  let viewportRectEl = null;
  let scaleX = 1;
  let scaleY = 1;
  let offsetX = 0;
  let offsetY = 0;
  let renderCtx = null;     // { state }

  function mount(ctx) {
    if (mounted) return;
    mounted = true;
    renderCtx = ctx;
    canvasEl = document.getElementById("minimap-canvas");
    viewportRectEl = document.getElementById("minimap-viewport-rect");
    if (!canvasEl || !viewportRectEl) return;

    canvasEl.addEventListener("click", (ev) => panToClick(ev));

    // Re-render minimap every time the canvas pans / zooms.
    document.addEventListener("uj-canvas-change", () => refresh());
    document.addEventListener("uj-canvas-bootstrap", () => refresh());

    window.UJView.on("modechange", () => updateVisibility());
    updateVisibility();
  }

  function updateVisibility() {
    const mode = window.UJView.getMode();
    const wrapper = document.getElementById("minimap");
    if (!wrapper) return;
    wrapper.hidden = mode !== "canvas";
  }

  function refresh() {
    if (!canvasEl || !viewportRectEl) return;
    if (!renderCtx || !renderCtx.state) return;
    const state = renderCtx.state;
    if (!state.canvas) return;

    // Re-render screen rects.
    canvasEl.innerHTML = "";
    canvasEl.appendChild(viewportRectEl);

    const bounds = state.contentBounds || { x: 0, y: 0, width: 1, height: 1 };
    if (bounds.width <= 0 || bounds.height <= 0) return;
    scaleX = W / bounds.width;
    scaleY = H / bounds.height;
    const scale = Math.min(scaleX, scaleY);
    // Centered offset within the minimap.
    offsetX = (W - bounds.width * scale) / 2;
    offsetY = (H - bounds.height * scale) / 2;
    scaleX = scale;
    scaleY = scale;

    state.cardsById.forEach((card) => {
      const r = document.createElement("div");
      r.className = "minimap-card";
      r.style.left = (offsetX + (card.offsetLeft - bounds.x) * scaleX) + "px";
      r.style.top  = (offsetY + (card.offsetTop  - bounds.y) * scaleY) + "px";
      r.style.width  = Math.max(2, card.offsetWidth  * scaleX) + "px";
      r.style.height = Math.max(2, card.offsetHeight * scaleY) + "px";
      const stateName = card.dataset.state || "default";
      r.classList.add(`minimap-card-state-${stateName}`);
      const currentId = window.UJView.getCurrentScreenId();
      if (currentId && card.dataset.screenId === currentId) {
        r.classList.add("is-current");
      }
      canvasEl.appendChild(r);
    });

    // Current viewport rectangle in world coords.
    const viewportInfo = state.canvas.getViewportWorldRect();
    if (viewportInfo) {
      const vx = offsetX + (viewportInfo.x - bounds.x) * scaleX;
      const vy = offsetY + (viewportInfo.y - bounds.y) * scaleY;
      const vw = viewportInfo.width  * scaleX;
      const vh = viewportInfo.height * scaleY;
      viewportRectEl.style.left   = vx + "px";
      viewportRectEl.style.top    = vy + "px";
      viewportRectEl.style.width  = vw + "px";
      viewportRectEl.style.height = vh + "px";
      canvasEl.appendChild(viewportRectEl);
    }
  }

  function panToClick(ev) {
    if (!renderCtx || !renderCtx.state) return;
    const state = renderCtx.state;
    if (!state.canvas) return;
    const bounds = state.contentBounds || { x: 0, y: 0 };
    const rect = canvasEl.getBoundingClientRect();
    const px = ev.clientX - rect.left;
    const py = ev.clientY - rect.top;
    // Map back to world coords.
    const wx = (px - offsetX) / scaleX + bounds.x;
    const wy = (py - offsetY) / scaleY + bounds.y;
    state.canvas.centerOnWorldPoint({ x: wx, y: wy });
  }

  window.UJMinimap = { mount, refresh };
})();
