import { describe, it, expect } from "bun:test";

import {
  buildModelSpectrumTraces,
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
