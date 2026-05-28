/* ============================================================
   user-journey view controller (v3)

   Owns the cross-cutting view state shared by canvas, sidebar,
   and prototype:

     window.UJView.state = {
       mode:            "canvas" | "prototype",
       currentScreenId: string | null,
       history:         string[],   // prototype back-stack
     }

   Other modules subscribe via UJView.on(event, handler) and
   call UJView.setMode / setCurrentScreen / pushHistory etc.

   Events fired:
     "modechange"        — { mode }
     "screenchange"      — { screenId, source }
     "historychange"     — { history }

   Pure JS, no deps. Renderers register themselves on DOMContent-
   Loaded; render.js calls UJView.init(data) once after parsing
   journey.json.
   ============================================================ */
(function () {
  "use strict";

  const VALID_MODES = ["canvas", "prototype"];

  const state = {
    mode: "canvas",
    currentScreenId: null,
    history: [],
    data: null,            // journey.json parsed
    screensById: new Map(),
    arrowsByFromScreen: new Map(),   // screenId -> arrows[]
  };

  const listeners = new Map();

  function on(event, handler) {
    if (!listeners.has(event)) listeners.set(event, []);
    listeners.get(event).push(handler);
  }

  function off(event, handler) {
    const arr = listeners.get(event);
    if (!arr) return;
    const idx = arr.indexOf(handler);
    if (idx >= 0) arr.splice(idx, 1);
  }

  function emit(event, payload) {
    (listeners.get(event) || []).forEach((fn) => {
      try { fn(payload); } catch (err) { /* swallow */ }
    });
  }

  /* ---------- Mode --------------------------------------------- */

  function setMode(mode, opts) {
    if (!VALID_MODES.includes(mode)) return;
    if (state.mode === mode) return;
    state.mode = mode;
    emit("modechange", { mode, ...(opts || {}) });
  }

  function getMode() {
    return state.mode;
  }

  /* ---------- Current screen ----------------------------------- */

  function setCurrentScreen(screenId, opts) {
    if (!screenId || !state.screensById.has(screenId)) return;
    if (state.currentScreenId === screenId && !opts?.force) return;
    state.currentScreenId = screenId;
    emit("screenchange", { screenId, source: opts?.source || "api" });
  }

  function getCurrentScreen() {
    return state.currentScreenId
      ? state.screensById.get(state.currentScreenId) || null
      : null;
  }

  function getCurrentScreenId() {
    return state.currentScreenId;
  }

  /* ---------- Prototype history -------------------------------- */

  function pushHistory(screenId) {
    if (!screenId) return;
    state.history.push(screenId);
    emit("historychange", { history: state.history.slice() });
  }

  function popHistory() {
    if (state.history.length === 0) return null;
    const sid = state.history.pop();
    emit("historychange", { history: state.history.slice() });
    return sid;
  }

  function clearHistory() {
    if (state.history.length === 0) return;
    state.history = [];
    emit("historychange", { history: [] });
  }

  function getHistory() {
    return state.history.slice();
  }

  /* ---------- Data index --------------------------------------- */

  function init(data) {
    state.data = data || {};
    state.screensById.clear();
    state.arrowsByFromScreen.clear();
    const screens = state.data.screens || [];
    screens.forEach((s) => {
      if (s && typeof s === "object" && s.id) {
        state.screensById.set(s.id, s);
      }
    });
    const arrows = state.data.arrows || [];
    arrows.forEach((a) => {
      if (!a || typeof a !== "object") return;
      const fromAddr = String(a.from || "");
      const screenId = fromAddr.split("#")[0];
      if (!screenId) return;
      if (!state.arrowsByFromScreen.has(screenId)) {
        state.arrowsByFromScreen.set(screenId, []);
      }
      state.arrowsByFromScreen.get(screenId).push(a);
    });
    if (!state.currentScreenId && screens.length > 0 && screens[0].id) {
      state.currentScreenId = screens[0].id;
    }
  }

  function getScreen(id) {
    return state.screensById.get(id) || null;
  }

  function getAllScreens() {
    return Array.from(state.screensById.values());
  }

  function getArrowsFromScreen(screenId) {
    return (state.arrowsByFromScreen.get(screenId) || []).slice();
  }

  /* ---------- Keyboard glue ------------------------------------ */

  function installKeyboard() {
    document.addEventListener("keydown", (ev) => {
      // Ignore when typing into inputs / textareas / contenteditable.
      const target = ev.target;
      const tag = (target && target.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || (target && target.isContentEditable)) {
        return;
      }
      if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
      if (ev.key === "v" || ev.key === "V") {
        ev.preventDefault();
        setMode("canvas");
      } else if (ev.key === "p" || ev.key === "P") {
        ev.preventDefault();
        setMode("prototype");
      }
    });
  }

  /* ---------- Public ------------------------------------------- */

  window.UJView = {
    init,
    on, off,
    getMode, setMode,
    getCurrentScreen, getCurrentScreenId, setCurrentScreen,
    getHistory, pushHistory, popHistory, clearHistory,
    getScreen, getAllScreens, getArrowsFromScreen,
    installKeyboard,
    get state() { return state; },
  };
})();
