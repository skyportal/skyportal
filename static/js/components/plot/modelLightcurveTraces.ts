import { rgba } from "../../utils/calculations";

// Per-filter model light curve from an analysis service:
// filter -> [[mjd, mag_median, mag_lo, mag_hi], ...]  (apparent mag, 68% band).
export type ModelLightcurve = Record<string, number[][]>;

export interface ModelFit {
  id?: number | string; // grouped fits use a composite `${analysisId}:${model}` id
  label?: string;
  dash?: string; // Plotly line dash, to distinguish models that share a filter color
  model_lightcurve: ModelLightcurve;
  analysisId?: number; // source analysis id, for the on-demand corner fetch
  model?: string; // model key into the analysis posteriors
  baseLabel?: string; // model name before run-disambiguation, for grouping runs
  createdAt?: string; // run timestamp — disambiguates repeated runs of a model
  nDet?: number; // detections used in the fit — also disambiguates runs
}

// Build Plotly traces (credible band + median line) per filter to overlay an
// analysis-service model fit (e.g. NMMA) on the source photometry plot.
//
// - `filter2color`: filter -> [r,g,b] (config.bandpassesColors), matched to the
//   photometry markers so the fit lines up by color.
// - `xOf`: maps an MJD to the plot's current x value (MJD, or sec/days-since-t0)
//   so the overlay tracks whatever x-axis mode the plot is in.
// - Magnitude axis only (the model is in mags); returns [] for flux.
export function buildModelLightcurveTraces(
  modelFits: ModelFit[],
  filter2color: Record<string, number[]>,
  xOf: (mjd: number) => number,
  plotType: string,
): any[] {
  if (plotType !== "mag" || !Array.isArray(modelFits)) return [];
  const traces: any[] = [];
  modelFits.forEach((fit, fi) => {
    const mlc = fit?.model_lightcurve || {};
    Object.entries(mlc).forEach(([filt, pts]) => {
      if (!Array.isArray(pts) || pts.length === 0) return;
      const color = filter2color?.[filt] || [80, 80, 80];
      const xs = pts.map((p) => xOf(p[0]));
      const med = pts.map((p) => p[1]);
      const lo = pts.map((p) => p[2]);
      const hi = pts.map((p) => p[3]);
      const group = `modelfit-${fit.id ?? fi}-${filt}`;
      const label = fit.label ? ` (${fit.label})` : "";

      // 68% credible band as a filled polygon (up the hi edge, back down the lo).
      traces.push({
        dataType: "modelFit",
        x: [...xs, ...xs.slice().reverse()],
        y: [...hi, ...lo.slice().reverse()],
        mode: "lines",
        type: "scatter",
        fill: "toself",
        fillcolor: rgba(color, 0.15),
        line: { width: 0 },
        hoverinfo: "skip",
        showlegend: false,
        legendgroup: group,
      });
      // Median model light curve. Kept out of the plot legend — model
      // visibility is driven by the per-model toggle buttons; the dash style
      // (matched in the button) distinguishes models sharing a filter color.
      traces.push({
        dataType: "modelFit",
        x: xs,
        y: med,
        mode: "lines",
        type: "scatter",
        line: { color: rgba(color, 1), width: 2, dash: fit.dash || "solid" },
        name: `${filt} fit${label}`,
        legendgroup: group,
        showlegend: false,
        hovertemplate: `${filt} fit${label}<br>MJD %{x}<br>mag %{y:.2f}<extra></extra>`,
      });
    });
  });
  return traces;
}
