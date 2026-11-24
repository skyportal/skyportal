import dayjs from "dayjs";
import numeral from "numeral";

import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(utc);
dayjs.extend(relativeTime);

const hours_to_ra = (hours: string): number => {
  const hoursSplit = hours.split(/[^\d\w]+/);
  const hh = parseInt(hoursSplit[0] ?? "", 10);
  const mm = parseInt(hoursSplit[1] ?? "", 10) / 60;

  let ss;
  if (hoursSplit.length === 3) {
    ss = parseInt(hoursSplit[2] ?? "", 10) / (60 * 60);
  } else {
    ss = parseFloat(`${hoursSplit[2]}.${hoursSplit[3]}`) / (60 * 60);
  }

  return (360 / 24) * (hh + mm + ss);
};

const dms_to_dec = (dms: string): number => {
  const dmsSplit = dms.split(/[^\d\w]+/).filter((e) => e === "0" || e);
  let mult = 1;
  if (dms[0] === "-") {
    mult = -1;
  }

  const dd = parseInt(dmsSplit[0] ?? "", 10);
  const mm = parseInt(dmsSplit[1] ?? "", 10) / 60;

  let ss;
  if (dmsSplit.length === 3) {
    ss = parseInt(dmsSplit[2] ?? "", 10) / (60 * 60);
  } else {
    ss = parseFloat(`${dmsSplit[2]}.${dmsSplit[3]}`) / (60 * 60);
  }

  return mult * (dd + mm + ss);
};

// Sexagesimal (HH:MM:SS / ±DD:MM:SS) or decimal degrees -> degrees.
const ra_to_deg = (v: string): number =>
  v.includes(":") ? hours_to_ra(v) : parseFloat(v);

const dec_to_deg = (v: string): number =>
  v.includes(":") ? dms_to_dec(v) : parseFloat(v);

const ra_to_hours = (ra: number, sep: string | null = null): string => {
  const total = Math.round(ra * 24000) % 8640000;
  const ra_h = numeral(Math.floor(total / 360000)).format("00");
  const ra_m = numeral(Math.floor((total % 360000) / 6000)).format("00");
  const ra_s = numeral((total % 6000) / 100).format("00.00");
  if (!(sep == null)) {
    return `${ra_h}${sep}${ra_m}${sep}${ra_s}`;
  }
  return `${ra_h}h${ra_m}m${ra_s}s`;
};

const dec_to_dms = (
  deci: number,
  sep: string | null = null,
  signed = true,
): string => {
  const total = Math.round(Math.abs(deci) * 360000);
  const deg_padded = numeral(Math.floor(total / 360000)).format("00");
  const min_padded = numeral(Math.floor((total % 360000) / 6000)).format("00");
  const secstr = numeral((total % 6000) / 100).format("00.00");
  let sign = "+";

  // this is for the case where the '+' sign needs to be omitted
  if (!(deci < 0) && signed === false) {
    sign = "";
  }

  if (deci < 0) {
    sign = "-";
  }

  if (!(sep == null)) {
    return `${sign}${deg_padded}${sep}${min_padded}${sep}${secstr}`;
  }
  return `${sign}${deg_padded}d${min_padded}m${secstr}s`;
};

function mjd_to_utc(mjd: number): string {
  // Take a MJD string and return UTC time
  return dayjs
    .unix((mjd - 40587) * 86400.0)
    .utc()
    .format();
}

function utc_to_mjd(datetime?: string | null): number | null {
  // Inverse of mjd_to_utc: a UTC datetime string (naive strings are read as
  // UTC) -> MJD (Unix epoch = MJD 40587). Null if empty or unparseable.
  if (!datetime) return null;
  const ms = dayjs.utc(datetime.replace(" ", "T")).valueOf();
  return Number.isNaN(ms) ? null : ms / 86400000 + 40587;
}

function time_relative_to_local(isostring: string): string {
  // Take an ISO 8601 string and return the offset relative to the local time
  return dayjs(isostring).local().fromNow();
}

const flux_to_mag = (
  flux: number | null | undefined,
  zp: number,
): number | null =>
  // Take a flux value and return the AB mag. Return null if flux is negative or null
  flux && flux > 0 ? -2.5 * Math.log10(flux) + zp : null;

export {
  ra_to_hours,
  dec_to_dms,
  hours_to_ra,
  dms_to_dec,
  ra_to_deg,
  dec_to_deg,
  time_relative_to_local,
  mjd_to_utc,
  utc_to_mjd,
  flux_to_mag,
};
