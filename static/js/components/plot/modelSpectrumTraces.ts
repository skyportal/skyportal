// Best-fit model/template spectrum from a spectral-classification analysis
// (e.g. SNID-SAGE, NGSF): [[wavelength, flux], ...].
export type ModelSpectrumPoints = number[][];

export interface ModelSpectrumFit {
  id?: number | string;
  label?: string;
  summary?: string; // classification headline (type/subtype/z/quality) for the hover
  dash?: string; // Plotly line dash, to distinguish overlaid models
  model_spectrum: ModelSpectrumPoints;
}

// |median flux|, used to put a model on the plot's per-spectrum normalized scale.
const medianAbs = (ys: number[]): number => {
  const finite = ys.filter((y) => Number.isFinite(y));
  if (!finite.length) return 1;
  const sorted = [...finite].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const m =
    sorted.length % 2 ? sorted[mid]! : (sorted[mid - 1]! + sorted[mid]!) / 2;
  return Math.abs(m) || 1;
};

// Build a Plotly line trace per model fit to overlay a best-fit template spectrum
// on the (median-normalized) spectrum plot. The model is normalized the same way
// (by |median flux|) so it lines up with the data; a color per entry keeps
// multiple overlays distinguishable.
export function buildModelSpectrumTraces(
  fits: ModelSpectrumFit[],
  colorOf: (i: number) => string,
): any[] {
  if (!Array.isArray(fits)) return [];
  const traces: any[] = [];
  fits.forEach((fit, fi) => {
    const pts = fit?.model_spectrum;
    if (!Array.isArray(pts) || pts.length === 0) return;
    const xs = pts.map((p) => p[0]);
    const ysRaw = pts.map((p) => p[1]!);
    const norm = medianAbs(ysRaw);
    const ys = ysRaw.map((y) => (Number.isFinite(y) ? y / norm : null));
    const title = fit.label ? `Fit: ${fit.label}` : "Model spectrum";
    // Classification headline is constant across the trace, so bake it into the hover.
    const summaryLine = fit.summary ? `${fit.summary}<br>` : "";
    traces.push({
      mode: "lines",
      type: "scatter",
      dataType: "ModelSpectrum",
      modelId: fit.id ?? fi,
      x: xs,
      y: ys,
      name: title,
      legendgroup: `modelspectrum-${fit.id ?? fi}`,
      line: { width: 1.5, color: colorOf(fi), dash: fit.dash || "solid" },
      hoverlabel: { align: "left" },
      hovertemplate: `<b>${title}</b><br>${summaryLine}%{x:.1f} &#8491;<br>model flux %{y:.3f}<extra></extra>`,
      visible: true,
    });
  });
  return traces;
}
