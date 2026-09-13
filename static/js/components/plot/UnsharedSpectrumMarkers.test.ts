import { describe, it, expect } from "bun:test";

import {
  UNSHARED_SPECTRUM,
  unsharedSpectrumTraces,
} from "./UnsharedSpectrumMarkers";
import { SpectrumAvailability } from "../../ducks/dataAccessRequests";

// The markers stand in for data the viewer cannot open, so what they carry —
// colour, epoch, and the id a click resolves to — is the whole contract.
const colors = { available: "#ff9800", requested: "#9e9e9e" };

const spectrum = (
  overrides: Partial<SpectrumAvailability> = {},
): SpectrumAvailability => ({
  id: 7,
  owner: { id: 3, username: "someone", first_name: null, last_name: null },
  instrument: { id: 2, name: "SEDM" },
  observed_at: "2020-01-10T00:00:00",
  observed_at_mjd: 58858.0,
  type: "source",
  label: null,
  origin: null,
  request: null,
  ...overrides,
});

describe("unsharedSpectrumTraces", () => {
  it("marks an unrequested spectrum at its epoch, in the available colour", () => {
    const [trace] = unsharedSpectrumTraces(
      [spectrum()],
      [18.5],
      colors,
      "#fff",
    ) as any[];

    expect(trace.name).toBe(UNSHARED_SPECTRUM);
    expect(trace.text).toEqual(["S"]);
    expect(trace.x).toEqual([58858.0]);
    expect(trace.y).toEqual([18.5]);
    expect(trace.textfont.color).toBe(colors.available);
    // What the click handler resolves back to a spectrum.
    expect(trace.customdata).toEqual([7]);
    expect(trace.hovertemplate).toContain("click to ask for it");
  });

  it("greys out a spectrum that has already been asked for", () => {
    const [trace] = unsharedSpectrumTraces(
      [spectrum({ request: { id: 1, status: "pending" } })],
      [18.5],
      colors,
      "#fff",
    ) as any[];

    expect(trace.textfont.color).toBe(colors.requested);
    expect(trace.hovertemplate).toContain("Access already requested");
  });

  it("skips a spectrum with no epoch, which has nowhere to go on the plot", () => {
    expect(
      unsharedSpectrumTraces(
        [spectrum({ observed_at_mjd: null })],
        [18.5],
        colors,
        "#fff",
      ),
    ).toEqual([]);
  });
});
