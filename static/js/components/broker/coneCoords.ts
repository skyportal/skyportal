import { dms_to_dec, hours_to_ra } from "../../units";

// Accept sexagesimal (HH:MM:SS / ±DD:MM:SS) like the new-source form; decimal
// degrees are parsed as-is. Callers guard against empty input.
export const raToDeg = (v: string): number =>
  v.includes(":") ? hours_to_ra(v) : parseFloat(v);

export const decToDeg = (v: string): number =>
  v.includes(":") ? dms_to_dec(v) : parseFloat(v);
