(() => {
  const root = document.querySelector(".erd");
  const stage = root?.querySelector(".erd-stage");
  const svg = stage?.querySelector("svg");
  if (!svg) return;

  const input = root.querySelector(".erd-input");
  const hits = root.querySelector(".erd-hits");
  const level = root.querySelector(".erd-level");
  const status = root.querySelector(".erd-status");
  const rel = root.querySelector(".erd-rel");
  const detail = root.querySelector(".erd-detail");

  const MAX_HITS = 12;
  const ZOOM_STEP = 1.35;
  const MAX_SCALE = 60;

  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const nameOf = (g) => g?.querySelector("title")?.textContent.trim();
  const say = (msg) => {
    status.textContent = msg;
  };
  const el = (tag, props, ...kids) => {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...kids);
    return node;
  };
  const fill = (target, kids) => {
    target.replaceChildren(...kids);
    target.hidden = !kids.length;
  };

  const [gx, gy, gw, gh] = svg
    .getAttribute("viewBox")
    .split(/[\s,]+/)
    .map(Number);

  const tables = new Map(
    [...svg.querySelectorAll("g.node")].map((g) => [nameOf(g), g]),
  );
  const links = [...svg.querySelectorAll("g.edge")]
    .map((g) => ({ g, ends: (nameOf(g) || "").split("--") }))
    .filter(({ ends }) => ends.length === 2);
  const names = [...tables.keys()];

  let cx = gx + gw / 2;
  let cy = gy + gh / 2;
  let w = gw;
  let baseW = gw;

  const rect = () => stage.getBoundingClientRect();
  const ratio = () => rect().height / rect().width;

  const draw = () => {
    const h = w * ratio();
    svg.setAttribute("viewBox", `${cx - w / 2} ${cy - h / 2} ${w} ${h}`);
    level.value = `${Math.round((baseW / w) * 100)}%`;
  };

  const fit = () => {
    // an inline height would beat the fullscreen rule in erd.css
    stage.style.height = document.fullscreenElement
      ? ""
      : `${clamp(rect().width / (gw / gh), 420, 760)}px`;
    w = baseW = Math.max(gw, gh / ratio()) * 1.02;
    cx = gx + gw / 2;
    cy = gy + gh / 2;
    draw();
  };

  const zoomTo = (width, fx = 0.5, fy = 0.5) => {
    const ux = cx + (fx - 0.5) * w;
    const uy = cy + (fy - 0.5) * w * ratio();
    w = clamp(width, baseW / MAX_SCALE, baseW);
    cx = ux - (fx - 0.5) * w;
    cy = uy - (fy - 0.5) * w * ratio();
    draw();
  };

  const zoomAt = (factor, clientX, clientY) => {
    const r = rect();
    zoomTo(
      w / factor,
      (clientX - r.left) / r.width,
      (clientY - r.top) / r.height,
    );
  };

  const clearFocus = () => {
    stage.classList.remove("has-focus");
    stage
      .querySelectorAll(".is-on, .is-hit")
      .forEach((node) => node.classList.remove("is-on", "is-hit"));
    fill(rel, []);
    fill(detail, []);
  };

  const chip = (name, className = "") =>
    el("button", {
      type: "button",
      className,
      textContent: name,
      onclick: () => pick(name),
    });

  const focus = (name) => {
    clearFocus();
    const g = tables.get(name);
    if (!g) return;
    stage.classList.add("has-focus");
    g.classList.add("is-on", "is-hit");

    const near = new Set();
    links.forEach(({ g: edge, ends }) => {
      if (!ends.includes(name)) return;
      edge.classList.add("is-on");
      near.add(ends[0] === name ? ends[1] : ends[0]);
    });
    near.forEach((n) => tables.get(n)?.classList.add("is-on"));

    fill(rel, [
      el("span", { className: "erd-rel-label", textContent: "Related" }),
      ...[...near].sort().map((n) => chip(n, "erd-chip")),
    ]);

    const enums = window.ERD_ENUMS || {};
    fill(
      detail,
      Object.entries(enums)
        .filter(([key]) => key.startsWith(`${name}.`))
        .map(([key, values]) =>
          el(
            "details",
            { className: "erd-enum" },
            el("summary", {
              textContent: `${key.split(".")[1]} - ${values.length} accepted values`,
            }),
            el("p", { textContent: values.join(", ") }),
          ),
        ),
    );

    say(
      `${name} - ${near.size} related table${near.size === 1 ? "" : "s"}. Esc to clear.`,
    );
  };

  const centre = (name) => {
    const gr = tables.get(name)?.getBoundingClientRect();
    if (!gr) return;
    const sr = rect();
    cx += ((gr.left + gr.width / 2 - sr.left) / sr.width - 0.5) * w;
    cy += ((gr.top + gr.height / 2 - sr.top) / sr.height - 0.5) * w * ratio();
    w = clamp(
      Math.max(
        (gr.width / sr.width) * w * 3.2,
        (gr.height / sr.height) * w * 1.5,
      ),
      baseW / MAX_SCALE,
      baseW,
    );
    draw();
  };

  const pick = (name) => {
    input.value = name;
    fill(hits, []);
    focus(name);
    centre(name);
  };

  const search = (term) => {
    const q = term.trim().toLowerCase();
    if (!q) return fill(hits, []);
    const rank = (name) => {
      const n = name.toLowerCase();
      return n === q ? 0 : n.startsWith(q) ? 1 : 2;
    };
    const found = names
      .filter((n) => n.toLowerCase().includes(q))
      .sort((a, b) => rank(a) - rank(b) || a.length - b.length);
    fill(
      hits,
      found.slice(0, MAX_HITS).map((n) => el("li", {}, chip(n))),
    );
    say(
      found.length
        ? `${found.length} of ${names.length} tables${found.length > MAX_HITS ? `, showing ${MAX_HITS}` : ""}.`
        : `No table matches "${q}".`,
    );
  };

  let dragging = null;
  const stopDrag = () => {
    dragging = null;
    stage.classList.remove("is-panning");
  };

  stage.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    dragging = { x: e.clientX, y: e.clientY, moved: false };
    stage.setPointerCapture(e.pointerId);
    stage.classList.add("is-panning");
  });

  stage.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const r = rect();
    const dx = e.clientX - dragging.x;
    const dy = e.clientY - dragging.y;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragging.moved = true;
    cx -= (dx / r.width) * w;
    cy -= (dy / r.height) * w * ratio();
    dragging.x = e.clientX;
    dragging.y = e.clientY;
    draw();
  });

  stage.addEventListener("pointerup", (e) => {
    if (!dragging) return;
    const { moved } = dragging;
    stopDrag();
    if (moved) return;
    const name = nameOf(e.target.closest?.("g.node"));
    if (!name) {
      clearFocus();
      return say("");
    }
    input.value = name;
    fill(hits, []);
    focus(name);
  });

  stage.addEventListener("pointercancel", stopDrag);

  stage.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      zoomAt(e.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP, e.clientX, e.clientY);
    },
    { passive: false },
  );

  const actions = {
    "zoom-in": () => zoomTo(w / ZOOM_STEP),
    "zoom-out": () => zoomTo(w * ZOOM_STEP),
    fit: () => {
      clearFocus();
      input.value = "";
      fill(hits, []);
      fit();
      say("");
    },
    full: () =>
      document.fullscreenElement
        ? document.exitFullscreen()
        : root.requestFullscreen?.(),
  };
  root
    .querySelectorAll("[data-erd]")
    .forEach((b) => b.addEventListener("click", actions[b.dataset.erd]));

  input.addEventListener("input", () => search(input.value));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      hits.querySelector("button")?.click();
    } else if (e.key === "Escape") fill(hits, []);
  });

  document.addEventListener("click", (e) => {
    if (!root.contains(e.target)) fill(hits, []);
  });

  stage.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      clearFocus();
      say("");
    } else if (e.key === "+" || e.key === "=") zoomTo(w / ZOOM_STEP);
    else if (e.key === "-") zoomTo(w * ZOOM_STEP);
  });

  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(draw, 120);
  });
  document.addEventListener("fullscreenchange", () => setTimeout(fit, 60));

  fit();
  say(`${names.length} tables. Drag to pan, scroll to zoom, click to focus.`);
})();
