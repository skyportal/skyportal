import { describe, it, expect } from "bun:test";

import { getSpectrumFilename } from "./spectrumFilename";

const spectrum = {
  obj_id: "ZTF20abucjsa",
  observed_at: "2020-09-09T04:33:12",
  instrument_name: "SEDM",
};

describe("getSpectrumFilename", () => {
  it("builds <obj>_<timestamp>_<instrument> with the given extension", () => {
    expect(getSpectrumFilename(spectrum, "ascii")).toBe(
      "ZTF20abucjsa_20200909T043312_SEDM.ascii",
    );
  });

  it("defaults to the generated-CSV extension", () => {
    expect(getSpectrumFilename(spectrum)).toBe(
      "ZTF20abucjsa_20200909T043312_SEDM.csv",
    );
  });

  it("distinguishes two spectra taken the same night", () => {
    const later = { ...spectrum, observed_at: "2020-09-09T06:15:00" };
    expect(getSpectrumFilename(spectrum)).not.toBe(getSpectrumFilename(later));
  });

  it("leaves the extension as the only period", () => {
    const name = getSpectrumFilename(
      {
        ...spectrum,
        observed_at: "2020-09-09T04:33:12.481000",
        instrument_name: "ALFOSC (NOT) v1.2",
      },
      "fits",
    );
    expect(name).toBe("ZTF20abucjsa_20200909T043312_ALFOSCNOTv12.fits");
    expect(name.split(".").length - 1).toBe(1);
  });

  it("drops the time when observed_at carries only a date", () => {
    expect(
      getSpectrumFilename({ ...spectrum, observed_at: "2020-09-09" }),
    ).toBe("ZTF20abucjsa_20200909_SEDM.csv");
  });

  it("omits fields that are missing rather than leaving empty separators", () => {
    expect(
      getSpectrumFilename({ obj_id: "AT2017gfo", instrument_name: "DBSP" }),
    ).toBe("AT2017gfo_DBSP.csv");
  });
});
