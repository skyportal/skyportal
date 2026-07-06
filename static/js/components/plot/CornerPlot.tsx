import { useEffect, useMemo, useState } from "react";
import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";
import { ensureMathJax } from "./mathjax";

const Plot = createPlotlyComponent(Plotly);

// Client-side corner / scatter-matrix for an analysis posterior, styled after
// corner.py: lower-triangle 2-D scatter panels, 1-D histograms on the diagonal
// with dashed 16/50/84th-percentile lines, and a per-parameter title showing
// the median with +/- 1-sigma (quantile) uncertainties. plotly.js-basic has no
// `splom`/`histogram2d`, so the grid is composed by hand. Fed the thinned
// posterior samples the fiesta fit stores as {param: [values]}.
export interface CornerPlotProps {
  posterior: Record<string, number[]>;
  title?: string;
  color?: string;
  maxParams?: number;
}

function histogram(vals: number[], bins = 24) {
  let lo = Infinity;
  let hi = -Infinity;
  for (const v of vals) {
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  const width = (hi - lo) / bins || 1;
  const centers: number[] = [];
  const counts = new Array(bins).fill(0);
  for (let b = 0; b < bins; b += 1) centers.push(lo + (b + 0.5) * width);
  for (const v of vals) {
    let k = Math.floor((v - lo) / width);
    if (k < 0) k = 0;
    if (k >= bins) k = bins - 1;
    counts[k] += 1;
  }
  return { centers, counts, width };
}

// Linear-interpolated quantile of an already-sorted ascending array.
function quantile(sorted: number[], q: number) {
  if (sorted.length === 0) return NaN;
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  const a = sorted[base];
  const b = sorted[base + 1];
  if (a === undefined) return NaN;
  return b !== undefined ? a + rest * (b - a) : a;
}

// Format a value with enough decimals to resolve `scale` (the uncertainty) to
// ~2 significant figures — keeps both small (log masses) and large (distance)
// parameters readable, like corner.py's title_fmt.
function fmt(v: number, scale: number) {
  if (!Number.isFinite(v)) return "—";
  const s = Number.isFinite(scale) && scale > 0 ? scale : Math.abs(v) || 1;
  let dec = 1 - Math.floor(Math.log10(s));
  dec = Math.max(0, Math.min(dec, 5));
  return v.toFixed(dec);
}

const CornerPlot = ({
  posterior,
  title,
  color = "#1f77b4",
  maxParams = 8,
}: CornerPlotProps) => {
  // Load MathJax so the quantile titles can be true LaTeX; re-render once ready
  // (or stay false and fall back to a plain-text label if it can't load).
  const [mjReady, setMjReady] = useState<boolean>(
    !!(
      typeof window !== "undefined" && (window as any).MathJax?.typesetPromise
    ),
  );
  useEffect(() => {
    let alive = true;
    ensureMathJax().then((ok) => {
      if (alive) setMjReady(ok);
    });
    return () => {
      alive = false;
    };
  }, []);

  const { data, layout } = useMemo(() => {
    const entries = Object.entries(posterior || {})
      .filter(([, v]) => Array.isArray(v) && v.length > 1)
      .slice(0, maxParams);
    const n = entries.length;
    // Pre-compute sorted samples + 16/50/84 quantiles per parameter.
    const stats = entries.map(([name, v]) => {
      const sorted = [...v].sort((a, b) => a - b);
      const q16 = quantile(sorted, 0.16);
      const q50 = quantile(sorted, 0.5);
      const q84 = quantile(sorted, 0.84);
      const up = q84 - q50;
      const low = q50 - q16;
      const unc = Math.min(up, low) || Math.max(up, low) || Math.abs(q50) || 1;
      const symmetric = Math.abs(up - low) <= 0.1 * Math.max(up, low, 1e-30);
      const med = fmt(q50, unc);
      // corner.py-style title: real LaTeX (median with stacked +upper/-lower)
      // when MathJax is ready; otherwise a readable plain-text fallback.
      const label = mjReady
        ? symmetric
          ? `$${med} \\pm ${fmt((up + low) / 2, unc)}$`
          : `$${med}^{+${fmt(up, unc)}}_{-${fmt(low, unc)}}$`
        : symmetric
          ? `${med} ± ${fmt((up + low) / 2, unc)}`
          : `+${fmt(up, unc)}<br>${med}<br>−${fmt(low, unc)}`;
      return { name, q16, q50, q84, label };
    });
    const traces: any[] = [];
    const shapes: any[] = [];
    const annotations: any[] = [];
    const lay: any = {
      title: title ? { text: title, font: { size: 13 } } : undefined,
      showlegend: false,
      width: Math.max(380, 160 * n),
      height: Math.max(380, 160 * n),
      margin: { l: 60, r: 14, t: title ? 62 : 46, b: 52 },
      font: { size: 9 },
      bargap: 0,
    };
    const gap = 0.012;
    const xdom = (col: number): [number, number] => [
      col / n + gap,
      (col + 1) / n - gap,
    ];
    const ydom = (row: number): [number, number] => [
      1 - (row + 1) / n + gap,
      1 - row / n - gap,
    ];
    let ax = 0;
    for (let row = 0; row < n; row += 1) {
      for (let col = 0; col <= row; col += 1) {
        ax += 1;
        const sfx = ax === 1 ? "" : String(ax);
        const xa = `x${sfx}`;
        const ya = `y${sfx}`;
        const [pj, vj] = entries[col]!;
        const [pi, vi] = entries[row]!;
        const onBottom = row === n - 1;
        const onLeft = col === 0 && row !== 0;
        lay[`xaxis${sfx}`] = {
          domain: xdom(col),
          anchor: ya,
          showticklabels: onBottom,
          title: onBottom ? { text: pj, font: { size: 9 } } : undefined,
          tickfont: { size: 7 },
          nticks: 3,
          zeroline: false,
        };
        lay[`yaxis${sfx}`] = {
          domain: ydom(row),
          anchor: xa,
          showticklabels: onLeft,
          title: onLeft ? { text: pi, font: { size: 9 } } : undefined,
          tickfont: { size: 7 },
          nticks: 3,
          zeroline: false,
        };
        if (col === row) {
          const h = histogram(vj);
          traces.push({
            type: "bar",
            x: h.centers,
            y: h.counts,
            width: h.width,
            xaxis: xa,
            yaxis: ya,
            marker: { color },
            hoverinfo: "skip",
          });
          lay[`yaxis${sfx}`].showticklabels = false;
          // Dashed 16/50/84th-percentile lines across the histogram.
          const st = stats[col]!;
          for (const [qv, dash] of [
            [st.q16, "dot"],
            [st.q50, "dash"],
            [st.q84, "dot"],
          ] as [number, string][]) {
            shapes.push({
              type: "line",
              xref: xa,
              yref: `${ya} domain`,
              x0: qv,
              x1: qv,
              y0: 0,
              y1: 1,
              line: { color: "#444", width: 1, dash },
            });
          }
          // corner.py-style per-parameter title above the diagonal cell.
          annotations.push({
            xref: `${xa} domain`,
            yref: `${ya} domain`,
            x: 0.5,
            y: 1,
            yshift: 4,
            xanchor: "center",
            yanchor: "bottom",
            showarrow: false,
            text: st.label,
            font: { size: 11, color: "#222" },
          });
        } else {
          traces.push({
            type: "scatter",
            mode: "markers",
            x: vj,
            y: vi,
            xaxis: xa,
            yaxis: ya,
            marker: { size: 2, color, opacity: 0.22 },
            hoverinfo: "skip",
          });
          // Crosshair at the medians on each 2-D panel.
          shapes.push({
            type: "line",
            xref: xa,
            yref: `${ya} domain`,
            x0: stats[col]!.q50,
            x1: stats[col]!.q50,
            y0: 0,
            y1: 1,
            line: { color: "#888", width: 0.8, dash: "dash" },
          });
          shapes.push({
            type: "line",
            xref: `${xa} domain`,
            yref: ya,
            x0: 0,
            x1: 1,
            y0: stats[row]!.q50,
            y1: stats[row]!.q50,
            line: { color: "#888", width: 0.8, dash: "dash" },
          });
        }
      }
    }
    lay.shapes = shapes;
    lay.annotations = annotations;
    return { data: traces, layout: lay };
  }, [posterior, title, color, maxParams, mjReady]);

  if (!data.length) return null;
  return (
    <Plot
      data={data}
      layout={layout}
      config={{ displaylogo: false, responsive: true }}
      useResizeHandler
      style={{ width: "100%" }}
    />
  );
};

export default CornerPlot;
