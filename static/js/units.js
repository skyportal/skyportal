import dayjs from "dayjs";

const utc = require("dayjs/plugin/utc");
const relativeTime = require("dayjs/plugin/relativeTime");

dayjs.extend(utc);
dayjs.extend(relativeTime);

const ra_to_hours = (ra, sep = null) => {
  const ra_h = Math.floor(ra / 15)
    .toString()
    .padStart(2, "0");
  const ra_m = Math.floor((ra % 15) * 4)
    .toString()
    .padStart(2, "0");
  const ra_s = (((ra % 15) * 4) % 1) * 60;
  const ra_s_integer = Math.floor(ra_s).toString().padStart(2, "0");
  const ra_s_decimal = Math.floor((ra_s - ra_s_integer) * 100);
  const ra_s_str = `${ra_s_integer}.${ra_s_decimal}`;

  if (!(sep == null)) {
    return `${ra_h}${sep}${ra_m}${sep}${ra_s_str}`;
  }
  return `${ra_h}h${ra_m}m${ra_s_str}s`;
};

const dec_to_dms = (deci, sep = null) => {
  const dec = Math.abs(deci);
  const deg = Math.floor(dec);
  const deg_padded = deg.toString().padStart(2, "0");
  const min = Math.floor((dec - deg) * 60);
  const min_padded = min.toString().padStart(2, "0");
  const sec = (dec - deg - min / 60) * 3600;
  const sec_int = Math.floor(sec).toString().padStart(2, "0");
  const sec_decimal = Math.floor((sec - sec_int) * 100);
  let sign = "+";
  if (deci < 0) {
    sign = "-";
  }

  const secstr = `${sec_int}.${sec_decimal}`;

  if (!(sep == null)) {
    return `${sign}${deg_padded}${sep}${min_padded}${sep}${secstr}`;
  }
  return `${sign}${deg_padded}d${min_padded}m${secstr}s`;
};

function time_relative_to_local(isostring) {
  // Take an ISO 8601 string and return the offset relative to the local time
  return dayjs(isostring).local().fromNow();
}

export { ra_to_hours, dec_to_dms, time_relative_to_local };
