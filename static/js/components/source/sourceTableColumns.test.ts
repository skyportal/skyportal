import { describe, it, expect } from "bun:test";

import {
  altdataKeyForField,
  buildAltdataColumnMeta,
  buildAnnotationColumnMeta,
  buildColumnPickerOptions,
  filterColumnPickerOptions,
  originKeyForAnnotationField,
} from "./sourceTableColumns";

// The annotations registry is unbounded (per-object origins like
// `ls_dr9-<objid>`), so these helpers must build a lookup — not a column each —
// and round-trip a saved field back to its origin/key.
const annotationsInfo = {
  "acai:high_h__high_n": [{ acai_v: "number" }, { age: "number" }],
  "ls_dr9-9907736172104018": [{ z_phot_median: "number" }, { type: "string" }],
};
const altdataInfo = { keys: [{ period: "number" }, { source_name: "string" }] };

describe("buildAnnotationColumnMeta", () => {
  it("maps every origin/key to a field with its origin+key", () => {
    const meta = buildAnnotationColumnMeta(annotationsInfo);
    expect(meta["annotation.acai:high_h__high_n.acai_v"]).toEqual({
      origin: "acai:high_h__high_n",
      key: "acai_v",
    });
    expect(meta["annotation.ls_dr9-9907736172104018.z_phot_median"]).toEqual({
      origin: "ls_dr9-9907736172104018",
      key: "z_phot_median",
    });
    expect(Object.keys(meta)).toHaveLength(4);
  });

  it("tolerates null/empty input", () => {
    expect(buildAnnotationColumnMeta(null)).toEqual({});
    expect(buildAnnotationColumnMeta({})).toEqual({});
  });
});

describe("buildAltdataColumnMeta", () => {
  it("maps altdata keys to fields", () => {
    const meta = buildAltdataColumnMeta(altdataInfo);
    expect(meta["altdata.period"]).toEqual({ key: "period" });
    expect(Object.keys(meta)).toHaveLength(2);
  });
  it("tolerates missing keys", () => {
    expect(buildAltdataColumnMeta(null)).toEqual({});
    expect(buildAltdataColumnMeta({})).toEqual({});
  });
});

describe("originKeyForAnnotationField", () => {
  const meta = buildAnnotationColumnMeta(annotationsInfo);

  it("resolves via the registry when present", () => {
    expect(
      originKeyForAnnotationField(
        "annotation.acai:high_h__high_n.acai_v",
        meta,
      ),
    ).toEqual({ origin: "acai:high_h__high_n", key: "acai_v" });
  });

  it("falls back to parsing when the origin aged out of the registry", () => {
    // A saved field whose origin is no longer in annotationsInfo.
    expect(
      originKeyForAnnotationField("annotation.ls_dr9-42.z_phot_std", {}),
    ).toEqual({ origin: "ls_dr9-42", key: "z_phot_std" });
  });
});

describe("altdataKeyForField", () => {
  const meta = buildAltdataColumnMeta(altdataInfo);
  it("resolves via the registry, else strips the prefix", () => {
    expect(altdataKeyForField("altdata.period", meta)).toBe("period");
    expect(altdataKeyForField("altdata.unknown_key", {})).toBe("unknown_key");
  });
});

describe("buildColumnPickerOptions", () => {
  it("labels annotation options `key (origin)` and altdata `key (altdata)`", () => {
    const opts = buildColumnPickerOptions(
      buildAnnotationColumnMeta(annotationsInfo),
      buildAltdataColumnMeta(altdataInfo),
    );
    const byField = Object.fromEntries(opts.map((o) => [o.field, o.label]));
    expect(byField["annotation.acai:high_h__high_n.acai_v"]).toBe(
      "acai_v (acai:high_h__high_n)",
    );
    expect(byField["altdata.period"]).toBe("period (altdata)");
    expect(opts).toHaveLength(6);
  });
});

describe("filterColumnPickerOptions", () => {
  const options = buildColumnPickerOptions(
    buildAnnotationColumnMeta(annotationsInfo),
    buildAltdataColumnMeta(altdataInfo),
  );

  it("returns nothing for an empty query (don't flood the dropdown)", () => {
    expect(filterColumnPickerOptions(options, "")).toEqual([]);
    expect(filterColumnPickerOptions(options, "   ")).toEqual([]);
  });

  it("case-insensitively substring-matches the label", () => {
    const hits = filterColumnPickerOptions(options, "z_phot");
    expect(hits).toHaveLength(1);
    expect(hits[0]!.field).toBe(
      "annotation.ls_dr9-9907736172104018.z_phot_median",
    );
  });

  it("caps results at the limit", () => {
    const many = buildColumnPickerOptions(
      Object.fromEntries(
        Array.from({ length: 200 }, (_, i) => [
          `annotation.ls_dr9-${i}.z_phot_median`,
          { origin: `ls_dr9-${i}`, key: "z_phot_median" },
        ]),
      ),
      {},
    );
    expect(filterColumnPickerOptions(many, "z_phot", 50)).toHaveLength(50);
  });
});
