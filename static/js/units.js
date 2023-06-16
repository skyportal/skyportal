import dayjs from "dayjs";
import numeral from "numeral";

import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(utc);
dayjs.extend(relativeTime);

const hours_to_ra = (hours) => {
  const hoursSplit = hours.split(/[^\d\w]+/);
  const hh = parseInt(hoursSplit[0], 10);
  const mm = parseInt(hoursSplit[1], 10) / 60;

  let ss;
  if (hoursSplit.length === 3) {
    ss = parseInt(hoursSplit[2], 10) / (60 * 60);
  } else {
    ss = parseFloat(`${hoursSplit[2]}.${hoursSplit[3]}`) / (60 * 60);
  }

  return (360 / 24) * (hh + mm + ss);
};

const dms_to_dec = (dms) => {
  const dmsSplit = dms.split(/[^\d\w]+/).filter((e) => e === 0 || e);
  let mult = 1;
  if (dms[0] === "-") {
    mult = -1;
  }

  const dd = parseInt(dmsSplit[0], 10);
  const mm = parseInt(dmsSplit[1], 10) / 60;

  let ss;
  if (dmsSplit.length === 3) {
    ss = parseInt(dmsSplit[2], 10) / (60 * 60);
  } else {
    ss = parseFloat(`${dmsSplit[2]}.${dmsSplit[3]}`) / (60 * 60);
  }

  return mult * (dd + mm + ss);
};

const ra_to_hours = (ra, sep = null) => {
  const ra_h = numeral(Math.floor(ra / 15)).format("00");
  const ra_m = numeral(Math.floor((ra % 15) * 4)).format("00");
  const ra_s = numeral((((ra % 15) * 4) % 1) * 60).format("00.00");
  if (!(sep == null)) {
    return `${ra_h}${sep}${ra_m}${sep}${ra_s}`;
  }
  return `${ra_h}h${ra_m}m${ra_s}s`;
};

const dec_to_dms = (deci, sep = null, signed = true) => {
  const dec = Math.abs(deci);
  const deg = Math.floor(dec);
  const deg_padded = numeral(deg).format("00");
  const min = Math.floor((dec - deg) * 60);
  const min_padded = numeral(min).format("00");
  const sec = (dec - deg - min / 60) * 3600;
  const secstr = numeral(sec).format("00.00");
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

function mjd_to_utc(mjd) {
  // Take a MJD string and return UTC time
  return dayjs
    .unix((mjd - 40587) * 86400.0)
    .utc()
    .format();
}

function time_relative_to_local(isostring) {
  // Take an ISO 8601 string and return the offset relative to the local time
  return dayjs(isostring).local().fromNow();
}

const flux_to_mag = (flux, zp) =>
  // Take a flux value and return the AB mag. Return null if flux is negative or null
  flux && flux > 0 ? -2.5 * Math.log10(flux) + zp : null;

export {
  ra_to_hours,
  dec_to_dms,
  hours_to_ra,
  dms_to_dec,
  time_relative_to_local,
  mjd_to_utc,
  flux_to_mag,
};
