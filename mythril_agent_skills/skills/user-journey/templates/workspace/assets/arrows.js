/* ============================================================
   user-journey arrows renderer (v3)

   Draws curved SVG arrows between screen cards on the canvas.
   The SVG lives inside the world, so it pans + zooms with everything
   else. Arrow geometry is recomputed on demand (after screens move
   or get resized).

   Public API (window.UJArrows):

     render(svg, arrows, options) -> void
       Renders all arrows into `svg` (an <svg> element inside the world).
       `options.getEndpoint(addr, otherAddr) -> {x, y, side, rect?}` is
       REQUIRED — it resolves an arrow address (`"<screen-id>"` or
       `"<screen-id>#<element-id>"`) into a world-space point + side
       hint ("top" | "right" | "bottom" | "left"). When the address is
       a whole-screen anchor (no `#element-id`), the resolver MAY pick
       the side intelligently based on `otherAddr`'s position.

     refresh(svg, arrows, options) -> void
       Alias for render — re-runs after positions change.

   Edge fan-out:
     When multiple arrows attach to the same {screen, side} pair, the
     renderer offsets each one perpendicular to the edge so they don't
     overlap. The offset is computed from the order in which arrows
     attach to that edge.

   Arrow kinds → stroke color (CSS vars in styles.css):
     default → --arrow-default
     success → --arrow-success
     error   → --arrow-error
     cancel  → --arrow-cancel (dashed)
   ============================================================ */
(function () {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";

  /* ---------- Public ----------------------------------------- */

  function render(svg, arrows, options) {
    if (!svg) return;
    options = options || {};
    const getEndpoint = options.getEndpoint;
    if (typeof getEndpoint !== "function") {
      throw new Error("UJArrows.render: options.getEndpoint is required");
    }

    // Clear existing children.
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    // Pass 1 — resolve every arrow's raw endpoints.
    const computed = [];
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    (arrows || []).forEach((arrow, idx) => {
      if (!arrow || typeof arrow !== "object") return;
      const fromPt = safeEndpoint(getEndpoint, arrow.from, arrow.to);
      const toPt   = safeEndpoint(getEndpoint, arrow.to, arrow.from);
      if (!fromPt || !toPt) return;
      computed.push({ arrow, fromPt, toPt, idx });
    });

    // Pass 2 — fan out arrows that share the same {address, side}
    // endpoint so they don't draw on top of each other. We bucket by
    // a stable "edge key" (`<screen-id>|<side>`) and then nudge each
    // arrow's endpoint perpendicular to that side. Element-anchored
    // endpoints (with an explicit `#element-id`) keep their exact
    // point — only whole-screen anchors get fanned.
    fanOutEdges(computed);

    // Pass 3 — bounding box for the SVG. Inflate enough that bezier
    // control points don't get clipped.
    computed.forEach(({ fromPt, toPt }) => {
      for (const p of [fromPt, toPt]) {
        if (p.x < minX) minX = p.x;
        if (p.x > maxX) maxX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.y > maxY) maxY = p.y;
      }
    });
    if (!isFinite(minX)) {
      svg.setAttribute("viewBox", "0 0 1 1");
      return;
    }

    const pad = 400;
    const bx = Math.floor(minX - pad);
    const by = Math.floor(minY - pad);
    const bw = Math.ceil(maxX - minX + pad * 2);
    const bh = Math.ceil(maxY - minY + pad * 2);
    svg.setAttribute("viewBox", `${bx} ${by} ${bw} ${bh}`);
    svg.setAttribute("width",  String(bw));
    svg.setAttribute("height", String(bh));
    svg.style.left = bx + "px";
    svg.style.top  = by + "px";

    // <defs> for the colored arrowheads (one per kind).
    const defs = el("defs");
    KIND_LIST.forEach((kind) => {
      defs.appendChild(makeArrowhead(kind));
    });
    svg.appendChild(defs);

    // Draw all arrows.
    computed.forEach(({ arrow, fromPt, toPt, idx }) => {
      drawArrow(svg, arrow, fromPt, toPt, idx);
    });
  }

  /* ---------- Edge fan-out ----------------------------------- */

  /* When several arrows attach to the same screen edge OR to the
     same near-pinpoint location, distribute them perpendicularly so
     they don't overlap. Two buckets:
       1. Whole-screen anchors → bucket by `{screenId, side}` — large
          edge of the card has plenty of room, big step is fine.
       2. Element-anchored escapes (multiple arrows leaving the same
          source element to different targets) → bucket by
          `{screenId, side, roundedAxisCoord}` — smaller pixel
          tolerance, smaller step.
     Pinpoint element anchors that land at the exact element edge
     (i.e. the natural side faced the target — no escape needed) get
     a softer offset so the arrowheads don't completely overlap. */
  function fanOutEdges(computed) {
    const FAN_STEP_SCREEN  = 22;   // px between whole-screen-anchored arrows
    const FAN_STEP_ELEMENT = 10;   // px between element-anchored arrows
    const FAN_MAX_OFFSET   = 90;
    const PINPOINT_TOLERANCE = 4;  // px — points within this distance share a bucket

    const buckets = new Map();

    function bucketKey(pt, end) {
      const side = pt.side || "right";
      const axisCoord = (side === "left" || side === "right") ? pt.y : pt.x;
      // Round the axis coord into 8-px bins so visually-close points
      // share a bucket. (Two arrows leaving the same button still
      // share x and side; round_y picks the bin.)
      const bin = Math.round(axisCoord / 8) * 8;
      const kind = pt.isElement ? "el" : "screen";
      return `${end}|${kind}|${pt.screenId || "?"}|${side}|${bin}`;
    }

    computed.forEach((item) => {
      if (item.fromPt.screenId) {
        const key = bucketKey(item.fromPt, "from");
        if (!buckets.has(key)) buckets.set(key, []);
        buckets.get(key).push({ item, end: "fromPt" });
      }
      if (item.toPt.screenId) {
        const key = bucketKey(item.toPt, "to");
        if (!buckets.has(key)) buckets.set(key, []);
        buckets.get(key).push({ item, end: "toPt" });
      }
    });

    buckets.forEach((entries) => {
      const n = entries.length;
      if (n < 2) return;
      const sample = entries[0].item[entries[0].end];
      const step = sample.isElement ? FAN_STEP_ELEMENT : FAN_STEP_SCREEN;
      const totalSpread = Math.min((n - 1) * step, FAN_MAX_OFFSET * 2);
      const stepActual = totalSpread / (n - 1);
      const start = -totalSpread / 2;
      entries.forEach((entry, i) => {
        const offset = start + i * stepActual;
        const pt = entry.item[entry.end];
        if (pt.side === "left" || pt.side === "right") {
          pt.y += offset;
        } else {
          pt.x += offset;
        }
      });
    });
  }

  function refresh(svg, arrows, options) {
    render(svg, arrows, options);
  }

  /* ---------- Internals -------------------------------------- */

  const KIND_LIST = ["default", "success", "error", "cancel"];

  function safeEndpoint(fn, addr, otherAddr) {
    try {
      const pt = fn(addr, otherAddr);
      if (!pt) return null;
      if (typeof pt.x !== "number" || typeof pt.y !== "number") return null;
      return {
        x: pt.x,
        y: pt.y,
        side: pt.side || "right",
        screenId: pt.screenId || null,
        isElement: !!pt.isElement,
      };
    } catch (err) {
      return null;
    }
  }

  function el(tag, attrs) {
    const n = document.createElementNS(SVG_NS, tag);
    if (attrs) {
      for (const k of Object.keys(attrs)) {
        n.setAttribute(k, String(attrs[k]));
      }
    }
    return n;
  }

  function makeArrowhead(kind) {
    const marker = el("marker", {
      id: `uj-arrowhead-${kind}`,
      viewBox: "0 0 10 10",
      refX: "9", refY: "5",
      markerWidth: "8", markerHeight: "8",
      orient: "auto-start-reverse",
    });
    const path = el("path", {
      d: "M 0 0 L 10 5 L 0 10 Z",
      class: `uj-arrowhead uj-arrowhead-${kind}`,
    });
    marker.appendChild(path);
    return marker;
  }

  function drawArrow(svg, arrow, fromPt, toPt, idx) {
    const kind = KIND_LIST.includes(arrow.kind) ? arrow.kind : "default";
    const g = el("g", {
      class: `uj-arrow uj-arrow-${kind}` + (arrow.is_default ? " is-default" : ""),
      "data-arrow-idx": String(idx),
    });
    if (arrow.id) g.setAttribute("data-arrow-id", arrow.id);

    const d = bezierPath(fromPt, toPt);
    const path = el("path", {
      d,
      class: `uj-arrow-path uj-arrow-path-${kind}`,
      fill: "none",
      "marker-end": `url(#uj-arrowhead-${kind})`,
    });
    g.appendChild(path);

    // Optional label rendered just OFF the bezier midpoint, pushed
    // perpendicular to the tangent so it doesn't sit on top of the
    // arrow line. The label is laid out as a pill (rect + text) with
    // the rect appended first so the text reads over it cleanly.
    const label = arrow.label || "";
    if (label) {
      const mid = bezierMidpoint(fromPt, toPt);
      const tan = bezierTangent(fromPt, toPt);
      // Unit normal (perpendicular). Pick the side that bulges away
      // from the curve's natural curvature so the label sits on the
      // OUTSIDE of the arc (more legible, less crowded).
      const len = Math.hypot(tan.x, tan.y) || 1;
      const nx = -tan.y / len;
      const ny =  tan.x / len;
      const LABEL_OFFSET = 14;
      const lx = mid.x + nx * LABEL_OFFSET;
      const ly = mid.y + ny * LABEL_OFFSET;
      const halo = el("text", {
        x: String(lx), y: String(ly),
        class: "uj-arrow-label-halo",
        "text-anchor": "middle",
        "dominant-baseline": "middle",
      });
      halo.textContent = label;
      const text = el("text", {
        x: String(lx), y: String(ly),
        class: `uj-arrow-label uj-arrow-label-${kind}`,
        "text-anchor": "middle",
        "dominant-baseline": "middle",
      });
      text.textContent = label;
      g.appendChild(halo);
      g.appendChild(text);
    }

    svg.appendChild(g);
  }

  /* ---------- Geometry --------------------------------------- */

  /* Build a smooth cubic-bezier path between two endpoints. Direction
     of curvature is biased by the side hint each endpoint carries
     ("top" | "right" | "bottom" | "left"). This keeps the arrows
     exiting / entering perpendicular to the card edge they touch.

     Self-loops (same screen on both ends) draw a small loop outside
     the screen on the chosen side, instead of a degenerate path. */
  function bezierPath(a, b) {
    const isSelfLoop = (a.screenId && a.screenId === b.screenId);
    if (isSelfLoop) {
      return selfLoopPath(a, b);
    }
    const ctrlA = controlOffset(a, b);
    const ctrlB = controlOffset(b, a);
    return [
      "M", a.x, a.y,
      "C", a.x + ctrlA.x, a.y + ctrlA.y,
      "  ", b.x + ctrlB.x, b.y + ctrlB.y,
      "  ", b.x, b.y,
    ].join(" ");
  }

  /* Draw a self-loop: a small lobe that exits one anchor, curves out
     perpendicular to its side, and re-enters the other anchor. Even
     when both anchors collapse to the same point (e.g. a screen-wide
     self-loop), the lobe stays visible. */
  function selfLoopPath(a, b) {
    const LOOP_R = 120;
    const sideA = a.side || "right";
    const sideB = b.side || sideA;
    // Pick a perpendicular direction (90 degrees off sideA) for the
    // lobe to bulge out into.
    const perp = perpDirection(sideA);
    const outA = vecForSide(sideA, LOOP_R);
    const outB = vecForSide(sideB, LOOP_R);
    const c1x = a.x + outA.x + perp.x * (LOOP_R * 0.6);
    const c1y = a.y + outA.y + perp.y * (LOOP_R * 0.6);
    const c2x = b.x + outB.x - perp.x * (LOOP_R * 0.6);
    const c2y = b.y + outB.y - perp.y * (LOOP_R * 0.6);
    return [
      "M", a.x, a.y,
      "C", c1x, c1y, c2x, c2y, b.x, b.y,
    ].join(" ");
  }

  function vecForSide(side, len) {
    switch (side) {
      case "right":  return { x:  len, y: 0 };
      case "left":   return { x: -len, y: 0 };
      case "top":    return { x: 0, y: -len };
      case "bottom": return { x: 0, y:  len };
      default:       return { x:  len, y: 0 };
    }
  }

  function perpDirection(side) {
    switch (side) {
      case "right":
      case "left":   return { x: 0, y: -1 };
      case "top":
      case "bottom": return { x: 1, y: 0 };
      default:       return { x: 0, y: -1 };
    }
  }

  /* Bezier control offset for one endpoint, perpendicular to its
     side. We bias the magnitude by the side's own axis distance to
     the other endpoint, not the diagonal — this avoids long curves
     swooping wildly vertically when the arrow is mostly horizontal
     (and vice versa). */
  function controlOffset(p, other) {
    const dxAxis = (p.side === "left" || p.side === "right")
      ? Math.abs(other.x - p.x)
      : Math.abs(other.y - p.y);
    const magnitude = Math.min(220, Math.max(60, dxAxis * 0.5));
    switch (p.side) {
      case "right":  return { x:  magnitude, y: 0 };
      case "left":   return { x: -magnitude, y: 0 };
      case "top":    return { x: 0, y: -magnitude };
      case "bottom": return { x: 0, y:  magnitude };
      default:       return { x:  magnitude, y: 0 };
    }
  }

  function midpoint(a, b) {
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  }

  /* Cubic-bezier point at t=0.5 — the visual midpoint of the curve.
     With t=0.5 the formula simplifies to a weighted average:
       P(0.5) = (1*P0 + 3*P1 + 3*P2 + 1*P3) / 8 */
  function bezierMidpoint(a, b) {
    const ctrlA = controlOffset(a, b);
    const ctrlB = controlOffset(b, a);
    const p1x = a.x + ctrlA.x, p1y = a.y + ctrlA.y;
    const p2x = b.x + ctrlB.x, p2y = b.y + ctrlB.y;
    return {
      x: (a.x + 3 * p1x + 3 * p2x + b.x) / 8,
      y: (a.y + 3 * p1y + 3 * p2y + b.y) / 8,
    };
  }

  /* Cubic-bezier tangent at t=0.5. Derivative of B(t):
       B'(0.5) = 3*(-0.25*P0 - 0.25*P1 + 0.25*P2 + 0.25*P3)
              ∝ (P3 + P2 - P1 - P0)  (after dropping the scalar) */
  function bezierTangent(a, b) {
    const ctrlA = controlOffset(a, b);
    const ctrlB = controlOffset(b, a);
    const p1x = a.x + ctrlA.x, p1y = a.y + ctrlA.y;
    const p2x = b.x + ctrlB.x, p2y = b.y + ctrlB.y;
    return {
      x: (b.x + p2x - p1x - a.x),
      y: (b.y + p2y - p1y - a.y),
    };
  }

  window.UJArrows = { render, refresh };
})();
