// Best-fit model/template spectrum from a spectral-classification analysis
// (e.g. SNID-SAGE, NGSF): [[wavelength, flux], ...].
export type ModelSpectrumPoints = number[][];

// "09/12/26 14:32" from an ISO timestamp; the time is what separates two
// spectra taken with the same instrument on the same night.
export const formatObservedAt = (value?: string | null): string => {
  if (!value) return "";
  const [date = "", rest = ""] = String(value).split("T");
  // Anything that is not an ISO date comes back untouched rather than being
  // sliced into nonsense.
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return String(value);
  const [year, month, day] = date.split("-") as [string, string, string];
  const time = rest.slice(0, 5);
  const stamp = `${month}/${day}/${year.slice(-2)}`;
  return time ? `${stamp} ${time}` : stamp;
};

/** Name a fit by the spectrum it was made against, not just by its service.
 *
 * Several runs of one service on one object all carry that service's name, so
 * the spectrum is what tells them apart; a service that does not report which
 * spectrum it used falls back to when the fit ran.
 */
export const describeFit = (analysis: any): ModelSpectrumFit => {
  const service =
    analysis.analysis_parameters?.source ||
    analysis.model_name ||
    analysis.analysis_service_name ||
    `analysis ${analysis.id}`;
  const source = analysis.model_spectrum_source || {};
  const spectrum = source.observed_at
    ? `${source.instrument_name || "spectrum"} ${formatObservedAt(source.observed_at)}`
    : formatObservedAt(analysis.created_at);
  return {
    id: analysis.id,
    label: spectrum ? `${service} \u00b7 ${spectrum}` : service,
    service,
    spectrum,
    sortKey: `${source.observed_at || analysis.created_at || ""}|${service}`,
    summary: analysis.model_spectrum_summary,
    model_spectrum: analysis.model_spectrum,
  };
};

export interface ModelSpectrumFit {
  id?: number | string;
  label?: string;
  service?: string; // the analysis service that produced the fit
  spectrum?: string; // the spectrum it was fitted against, or its run time
  sortKey?: string;
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
