import dayjs from "dayjs";
import numeral from "numeral";

const utc = require("dayjs/plugin/utc");
const relativeTime = require("dayjs/plugin/relativeTime");

dayjs.extend(utc);
dayjs.extend(relativeTime);

const ra_to_hours = (ra, sep = null) => {
  const ra_h = numeral(Math.floor(ra / 15)).format("00");
  const ra_m = numeral(Math.floor((ra % 15) * 4)).format("00");
  const ra_s = numeral((((ra % 15) * 4) % 1) * 60).format("00.00");
  if (!(sep == null)) {
    return `${ra_h}${sep}${ra_m}${sep}${ra_s}`;
  }
  return `${ra_h}h${ra_m}m${ra_s}s`;
};

const dec_to_dms = (deci, sep = null) => {
  const dec = Math.abs(deci);
  const deg = Math.floor(dec);
  const deg_padded = numeral(deg).format("00");
  const min = Math.floor((dec - deg) * 60);
  const min_padded = numeral(min).format("00");
  const sec = (dec - deg - min / 60) * 3600;
  const secstr = numeral(sec).format("00.00");
  let sign = "+";
  if (deci < 0) {
    sign = "-";
  }

  if (!(sep == null)) {
    return `${sign}${deg_padded}${sep}${min_padded}${sep}${secstr}`;
  }
  return `${sign}${deg_padded}d${min_padded}m${secstr}s`;
};

function time_relative_to_local(isostring) {
  // Take an ISO 8601 string and return the offset relative to the local time
  return dayjs(isostring).local().fromNow();
}

const flux_to_mag = (flux, zp) => {
  // Take a flux value and return the AB mag. Return null if flux is negative or null
  return flux && flux > 0 ? -2.5 * Math.log10(flux) + zp : null;
};

export { ra_to_hours, dec_to_dms, time_relative_to_local, flux_to_mag };
