import { describe, it, expect } from "bun:test";

import {
  buildModelSpectrumTraces,
  describeFit,
  formatObservedAt,
  ModelSpectrumFit,
} from "./modelSpectrumTraces";

// Overlay must sit on the plot's per-spectrum normalized scale (flux / |median|),
// so a template with median flux 2 comes back at ~1 where its flux was 2.
const colorOf = (i: number) => ["red", "blue"][i] || "gray";

const fit = (): ModelSpectrumFit => ({
  id: 7,
  label: "II-flash",
  model_spectrum: [
    [4000, 1.0],
    [5000, 2.0], // median flux -> normalizes to 1
    [6000, 3.0],
    [7000, NaN], // masked -> null
  ],
});

describe("buildModelSpectrumTraces", () => {
  it("builds one normalized line trace per fit", () => {
    const traces = buildModelSpectrumTraces([fit()], colorOf);
    expect(traces).toHaveLength(1);
    const t = traces[0];
    expect(t.dataType).toBe("ModelSpectrum");
    expect(t.x).toEqual([4000, 5000, 6000, 7000]);
    // divided by |median| = 2
    expect(t.y).toEqual([0.5, 1.0, 1.5, null]);
    expect(t.name).toBe("Fit: II-flash");
    expect(t.line.color).toBe("red");
  });

  it("skips fits with no model_spectrum", () => {
    const empty = { id: 1, model_spectrum: [] } as ModelSpectrumFit;
    expect(buildModelSpectrumTraces([empty], colorOf)).toHaveLength(0);
    expect(
      buildModelSpectrumTraces([{} as ModelSpectrumFit], colorOf),
    ).toHaveLength(0);
  });

  it("returns [] for a non-array input", () => {
    expect(buildModelSpectrumTraces(null as any, colorOf)).toEqual([]);
  });
});

describe("buildModelSpectrumTraces hover", () => {
  it("bakes the classification summary into the hovertemplate", () => {
    const snidFit: ModelSpectrumFit = {
      id: 3,
      label: "SNID-SAGE",
      summary: "II II-flash · z=0.0025 · MatchQual High",
      model_spectrum: [
        [4000, 1.0],
        [5000, 1.0],
      ],
    };
    const [t] = buildModelSpectrumTraces([snidFit], () => "red");
    expect(t.hovertemplate).toContain("II II-flash");
    expect(t.hovertemplate).toContain("Fit: SNID-SAGE");
  });
});

describe("describeFit", () => {
  const analysis = (over: any = {}) => ({
    id: 1,
    obj_id: "ZTF1",
    analysis_service_name: "SNID-SAGE (OSG)",
    created_at: "2026-09-13T14:22:07",
    model_spectrum: [[4000, 1]],
    ...over,
  });

  it("names a fit by the spectrum it was made against", () => {
    const described = describeFit(
      analysis({
        model_spectrum_source: {
          instrument_name: "SEDM",
          observed_at: "2026-09-12T09:31:00",
        },
      }),
    );
    expect(described.label).toBe("SNID-SAGE (OSG) \u00b7 SEDM 09/12/26 09:31");
  });

  it("falls back to the run time when the service does not report one", () => {
    // Otherwise every run of a service on one object carries the same name.
    expect(describeFit(analysis()).label).toBe(
      "SNID-SAGE (OSG) \u00b7 09/13/26 14:22",
    );
  });

  it("distinguishes two runs of the same service", () => {
    const a = describeFit(
      analysis({ id: 1, created_at: "2026-09-13T14:22:07" }),
    );
    const b = describeFit(
      analysis({ id: 2, created_at: "2026-09-13T16:40:00" }),
    );
    expect(a.label).not.toBe(b.label);
  });

  it("sorts by the spectrum, then by service name", () => {
    const fits = [
      describeFit(
        analysis({
          id: 1,
          analysis_service_name: "NGSF (OSG)",
          model_spectrum_source: { observed_at: "2026-09-13T02:00:00" },
        }),
      ),
      describeFit(
        analysis({
          id: 2,
          analysis_service_name: "SNID-SAGE (OSG)",
          model_spectrum_source: { observed_at: "2026-09-12T02:00:00" },
        }),
      ),
      describeFit(
        analysis({
          id: 3,
          analysis_service_name: "NGSF (OSG)",
          model_spectrum_source: { observed_at: "2026-09-12T02:00:00" },
        }),
      ),
    ].sort((x, y) => (x.sortKey || "").localeCompare(y.sortKey || ""));
    // Oldest spectrum first; within one spectrum, alphabetical by service.
    expect(fits.map((f) => f.id)).toEqual([3, 2, 1]);
  });

  it("prefers an explicit source name over the service", () => {
    const described = describeFit(
      analysis({ analysis_parameters: { source: "Me2017" } }),
    );
    expect(described.service).toBe("Me2017");
  });
});

describe("formatObservedAt", () => {
  it("keeps the time, which is what separates same-night spectra", () => {
    expect(formatObservedAt("2026-09-12T09:31:47")).toBe("09/12/26 09:31");
  });

  it("handles a date with no time, and returns unparseable input unchanged", () => {
    expect(formatObservedAt("2026-09-12")).toBe("09/12/26");
    expect(formatObservedAt("")).toBe("");
    expect(formatObservedAt("not-a-date")).toBe("not-a-date");
  });
});
