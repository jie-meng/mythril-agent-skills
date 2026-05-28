/* ============================================================
   user-journey infinite canvas (v3)

   A Miro-style infinite canvas: one big <div class="canvas-world">
   inside a fixed <div class="canvas-viewport">. All screens, arrows,
   and stickies live inside the world. The world is positioned via
   CSS `transform: translate() scale()`.

   Public API (window.UJCanvas):

     create({ viewport, world, onChange }) -> controller
       - viewport: the fixed-size element that clips the world
       - world:    the world element being transformed
       - onChange: optional callback({zoom, pan}) on every change

     controller:
       .setView({x, y, zoom})       -> set absolute viewport
       .panBy(dx, dy)               -> nudge world by (dx, dy) screen px
       .zoomAt(clientX, clientY, factor)
                                    -> zoom centered at a screen point
       .fit(rect, opts?)            -> fit a world-space rect to viewport
       .reset()                     -> 100% zoom centered on world (0,0)
       .focus(rect, opts?)          -> animate camera to a rect
       .screenToWorld(x, y)         -> map screen px → world px
       .worldToScreen(x, y)         -> map world px → screen px
       .state()                     -> { zoom, pan }

   Keyboard shortcuts (when controller installed):
     `+` / `=`  zoom in (around viewport center)
     `-`        zoom out (around viewport center)
     `0`        reset to 100%
     `1`        zoom to 100% (alias)
     `F`        fit-to-screen (all screens + stickies)
     `Space`    hold + drag to pan (Miro style)
     `H`        toggle help overlay
     arrow keys nudge view

   Mouse / trackpad:
     - Drag empty canvas         → pan
     - Hold Space + drag         → pan (even over interactive items)
     - Mouse wheel               → pan vertically (browser default)
     - `Cmd/Ctrl` + wheel        → zoom around cursor
     - Trackpad pinch            → zoom around cursor

   No deps. ES2017+.
   ============================================================ */
(function () {
  "use strict";

  const MIN_ZOOM = 0.1;
  const MAX_ZOOM = 4.0;
  const PAN_KEY_STEP = 60;     // px per arrow-key tap (in screen space)
  const ZOOM_KEY_STEP = 1.2;   // multiplicative factor per +/- tap
  const FIT_PADDING = 64;      // px breathing room around fit rect

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function isTypingTarget(el) {
    if (!el) return false;
    const tag = el.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    if (el.isContentEditable) return true;
    return false;
  }

  /* ---------- Controller -------------------------------------- */

  function create(options) {
    const viewport = options.viewport;
    const world    = options.world;
    const onChange = options.onChange || function () {};
    if (!viewport || !world) {
      throw new Error("UJCanvas.create: viewport and world are required");
    }

    /* state.zoom = world-space-per-1-screen-px scale factor.
       state.pan  = where the world's (0,0) sits in screen px,
                    measured from the viewport's top-left.

       So a world-space point (x, y) renders at screen point
       (pan.x + x*zoom, pan.y + y*zoom). */
    const state = {
      zoom: 1,
      pan:  { x: 0, y: 0 },
    };

    /* Pointer interaction state. */
    const drag = {
      active: false,
      panStart: { x: 0, y: 0 },
      pointerStart: { x: 0, y: 0 },
      pointerId: null,
      spacePan: false,
    };

    let spaceHeld = false;

    function apply() {
      world.style.transform =
        `translate(${state.pan.x}px, ${state.pan.y}px) scale(${state.zoom})`;
      onChange({ zoom: state.zoom, pan: { ...state.pan } });
      // Fire a DOM-level event so peripheral components (minimap,
      // overview overlays) can react without tight coupling.
      document.dispatchEvent(new CustomEvent("uj-canvas-change", {
        detail: { zoom: state.zoom, pan: { ...state.pan } },
      }));
    }

    function setView(view) {
      if (!view) return;
      if (typeof view.zoom === "number") {
        state.zoom = clamp(view.zoom, MIN_ZOOM, MAX_ZOOM);
      }
      if (view.pan) {
        if (typeof view.pan.x === "number") state.pan.x = view.pan.x;
        if (typeof view.pan.y === "number") state.pan.y = view.pan.y;
      }
      apply();
    }

    function panBy(dx, dy) {
      state.pan.x += dx;
      state.pan.y += dy;
      apply();
    }

    function zoomAt(clientX, clientY, factor) {
      const rect = viewport.getBoundingClientRect();
      const sx = clientX - rect.left;
      const sy = clientY - rect.top;
      const newZoom = clamp(state.zoom * factor, MIN_ZOOM, MAX_ZOOM);
      // Anchor zoom so that the world point under (sx, sy) stays put.
      const wx = (sx - state.pan.x) / state.zoom;
      const wy = (sy - state.pan.y) / state.zoom;
      state.zoom = newZoom;
      state.pan.x = sx - wx * newZoom;
      state.pan.y = sy - wy * newZoom;
      apply();
    }

    function zoomCenter(factor) {
      const rect = viewport.getBoundingClientRect();
      zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, factor);
    }

    function reset() {
      const rect = viewport.getBoundingClientRect();
      state.zoom = 1;
      state.pan.x = rect.width / 2;
      state.pan.y = rect.height / 2;
      apply();
    }

    function screenToWorld(clientX, clientY) {
      const rect = viewport.getBoundingClientRect();
      return {
        x: (clientX - rect.left - state.pan.x) / state.zoom,
        y: (clientY - rect.top  - state.pan.y) / state.zoom,
      };
    }

    function worldToScreen(x, y) {
      const rect = viewport.getBoundingClientRect();
      return {
        x: rect.left + state.pan.x + x * state.zoom,
        y: rect.top  + state.pan.y + y * state.zoom,
      };
    }

    /* Fit a world-space bounding rect into the viewport, with padding. */
    function fit(rect, opts) {
      opts = opts || {};
      if (!rect || !isFinite(rect.width) || !isFinite(rect.height)) return;
      const vp = viewport.getBoundingClientRect();
      const pad = opts.padding != null ? opts.padding : FIT_PADDING;
      const availW = Math.max(50, vp.width  - pad * 2);
      const availH = Math.max(50, vp.height - pad * 2);
      const zx = availW / Math.max(1, rect.width);
      const zy = availH / Math.max(1, rect.height);
      const newZoom = clamp(Math.min(zx, zy), MIN_ZOOM, MAX_ZOOM);
      state.zoom = newZoom;
      // Center the rect in the viewport.
      const cx = rect.x + rect.width  / 2;
      const cy = rect.y + rect.height / 2;
      state.pan.x = vp.width  / 2 - cx * newZoom;
      state.pan.y = vp.height / 2 - cy * newZoom;
      apply();
    }

    function focus(rect, opts) {
      // Today this just snaps; if we later want easing, do it here.
      fit(rect, opts);
    }

    /* ---------- Event handlers ------------------------------- */

    function onPointerDown(ev) {
      // Only left button starts a drag.
      if (ev.button !== 0) return;
      // Skip drags that originate inside an explicit "no-pan" zone
      // (e.g. the help overlay or a sticky-note inline editor).
      if (ev.target.closest("[data-no-pan]")) return;
      // If the target is interactive (a hotspot, sticky, button etc.)
      // we only initiate a pan when Space is held.
      const isInteractive = ev.target.closest("[data-canvas-item]");
      if (isInteractive && !spaceHeld) return;

      drag.active = true;
      drag.spacePan = spaceHeld;
      drag.pointerId = ev.pointerId;
      drag.pointerStart = { x: ev.clientX, y: ev.clientY };
      drag.panStart = { ...state.pan };
      viewport.setPointerCapture(ev.pointerId);
      viewport.classList.add("is-panning");
    }

    function onPointerMove(ev) {
      if (!drag.active) return;
      const dx = ev.clientX - drag.pointerStart.x;
      const dy = ev.clientY - drag.pointerStart.y;
      state.pan.x = drag.panStart.x + dx;
      state.pan.y = drag.panStart.y + dy;
      apply();
    }

    function onPointerUp(ev) {
      if (!drag.active) return;
      drag.active = false;
      try { viewport.releasePointerCapture(drag.pointerId); } catch (e) { /* noop */ }
      drag.pointerId = null;
      viewport.classList.remove("is-panning");
    }

    function onWheel(ev) {
      // Ctrl/Cmd + wheel, or trackpad pinch (which arrives as ctrl-wheel),
      // zooms around the cursor. Bare wheel pans (translate the world).
      if (ev.ctrlKey || ev.metaKey) {
        ev.preventDefault();
        const factor = Math.exp(-ev.deltaY * 0.0015);
        zoomAt(ev.clientX, ev.clientY, factor);
        return;
      }
      // Otherwise: pan the world. Hold Shift to swap axes (like maps).
      ev.preventDefault();
      const dx = ev.shiftKey ? ev.deltaY : ev.deltaX;
      const dy = ev.shiftKey ? ev.deltaX : ev.deltaY;
      state.pan.x -= dx;
      state.pan.y -= dy;
      apply();
    }

    function onKeyDown(ev) {
      if (isTypingTarget(ev.target)) return;
      const k = ev.key.toLowerCase();

      if (k === " " || k === "spacebar") {
        if (!spaceHeld) {
          spaceHeld = true;
          viewport.classList.add("is-space-held");
        }
        ev.preventDefault();
        return;
      }
      if (k === "+" || k === "=") {
        zoomCenter(ZOOM_KEY_STEP);
        ev.preventDefault();
        return;
      }
      if (k === "-" || k === "_") {
        zoomCenter(1 / ZOOM_KEY_STEP);
        ev.preventDefault();
        return;
      }
      if (k === "0" || k === "1") {
        // 0 = reset to 100%, recenter; 1 = same alias.
        reset();
        ev.preventDefault();
        return;
      }
      if (k === "f") {
        if (typeof options.onFitRequest === "function") {
          const rect = options.onFitRequest();
          if (rect) fit(rect);
        }
        ev.preventDefault();
        return;
      }
      if (k === "h") {
        if (typeof options.onHelpToggle === "function") {
          options.onHelpToggle();
        }
        ev.preventDefault();
        return;
      }
      if (k === "arrowleft")  { panBy( PAN_KEY_STEP,  0); ev.preventDefault(); return; }
      if (k === "arrowright") { panBy(-PAN_KEY_STEP,  0); ev.preventDefault(); return; }
      if (k === "arrowup")    { panBy( 0,  PAN_KEY_STEP); ev.preventDefault(); return; }
      if (k === "arrowdown")  { panBy( 0, -PAN_KEY_STEP); ev.preventDefault(); return; }
    }

    function onKeyUp(ev) {
      const k = ev.key.toLowerCase();
      if (k === " " || k === "spacebar") {
        spaceHeld = false;
        viewport.classList.remove("is-space-held");
      }
    }

    function onContextMenu(ev) {
      // Prevent right-click menu inside the canvas — it disrupts panning.
      if (ev.target.closest("[data-no-pan]")) return;
      ev.preventDefault();
    }

    function onDoubleClick(ev) {
      // Double-click on a screen card → focus + zoom.
      const card = ev.target.closest("[data-canvas-screen]");
      if (!card) return;
      if (typeof options.onScreenDoubleClick === "function") {
        options.onScreenDoubleClick(card.dataset.screenId, card);
      }
    }

    /* ---------- Install -------------------------------------- */

    viewport.addEventListener("pointerdown",  onPointerDown);
    viewport.addEventListener("pointermove",  onPointerMove);
    viewport.addEventListener("pointerup",    onPointerUp);
    viewport.addEventListener("pointercancel", onPointerUp);
    viewport.addEventListener("wheel",        onWheel, { passive: false });
    viewport.addEventListener("dblclick",     onDoubleClick);
    viewport.addEventListener("contextmenu",  onContextMenu);
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup",   onKeyUp);

    apply();

    /* Return the world-space rectangle that's currently visible in
       the viewport. Used by minimap to draw the viewport-rect. */
    function getViewportWorldRect() {
      const vp = viewport.getBoundingClientRect();
      const tl = screenToWorld(vp.left, vp.top);
      const br = screenToWorld(vp.left + vp.width, vp.top + vp.height);
      return {
        x: tl.x, y: tl.y,
        width:  br.x - tl.x,
        height: br.y - tl.y,
      };
    }

    /* Pan so that (x, y) in world coords lands at the viewport
       center. Used by minimap clicks. */
    function centerOnWorldPoint(p) {
      if (!p) return;
      const vp = viewport.getBoundingClientRect();
      state.pan.x = vp.width  / 2 - p.x * state.zoom;
      state.pan.y = vp.height / 2 - p.y * state.zoom;
      apply();
    }

    return {
      setView,
      panBy,
      zoomAt,
      zoomCenter,
      fit,
      focus,
      reset,
      screenToWorld,
      worldToScreen,
      getViewportWorldRect,
      centerOnWorldPoint,
      state: () => ({ zoom: state.zoom, pan: { ...state.pan } }),
      destroy() {
        viewport.removeEventListener("pointerdown",  onPointerDown);
        viewport.removeEventListener("pointermove",  onPointerMove);
        viewport.removeEventListener("pointerup",    onPointerUp);
        viewport.removeEventListener("pointercancel", onPointerUp);
        viewport.removeEventListener("wheel",        onWheel);
        viewport.removeEventListener("dblclick",     onDoubleClick);
        viewport.removeEventListener("contextmenu",  onContextMenu);
        window.removeEventListener("keydown", onKeyDown);
        window.removeEventListener("keyup",   onKeyUp);
      },
    };
  }

  window.UJCanvas = { create, MIN_ZOOM, MAX_ZOOM };
})();
