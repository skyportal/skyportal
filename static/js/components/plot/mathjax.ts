// Lazily load MathJax v3 (tex-svg) so Plotly can typeset LaTeX in plot text
// (e.g. corner-plot quantile titles like `0.5^{+0.1}_{-0.1}`). Loaded on demand
// — only when a plot that needs it mounts — and only once per page. Resolves to
// `true` when MathJax is ready, `false` if it failed to load (caller falls back
// to a plain-text label). Plotly's bundle supports MathJax v3 via the
// `startup`/`typeset` API, keyed on `MathJax.version`.
let mjPromise: Promise<boolean> | null = null;

export function ensureMathJax(): Promise<boolean> {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return Promise.resolve(false);
  }
  const w = window as any;
  if (w.MathJax?.typesetPromise) return Promise.resolve(true);
  if (mjPromise) return mjPromise;

  mjPromise = new Promise<boolean>((resolve) => {
    w.MathJax = {
      tex: { inlineMath: [["$", "$"]] },
      svg: { fontCache: "global" },
      // Don't auto-typeset the whole page; Plotly typesets just its own text.
      startup: {
        typeset: false,
        ready: () => {
          w.MathJax.startup.defaultReady();
          resolve(true);
        },
      },
    };
    const s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js";
    s.async = true;
    s.onerror = () => resolve(false);
    document.head.appendChild(s);
  });
  return mjPromise;
}
