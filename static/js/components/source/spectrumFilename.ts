// Normalized download name for a spectrum. Kept in a pure (React-free) module
// so it can be imported into unit tests without pulling in the component tree.

// <obj>_<YYYYMMDDTHHMMSS>_<instrument>.<ext>, rather than the name the uploader
// chose: two spectra on one source routinely share one (e.g. "spectrum.ascii").
// The timestamp goes to the second so several spectra from one night stay
// distinct, and no field may contain a period — the only one is the extension.
export const getSpectrumFilename = (
  spectrum: any,
  extension = "csv",
): string => {
  const digits = (spectrum.observed_at || "").replace(/\D/g, "");
  const observed =
    digits.length >= 14
      ? `${digits.slice(0, 8)}T${digits.slice(8, 14)}`
      : digits.slice(0, 8);
  return `${[spectrum.obj_id, observed, spectrum.instrument_name]
    .filter(Boolean)
    .map((part) => String(part).replace(/[^A-Za-z0-9+-]+/g, ""))
    .join("_")}.${extension}`;
};
