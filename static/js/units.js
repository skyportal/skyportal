import dayjs from 'dayjs';

const utc = require('dayjs/plugin/utc');
const relativeTime = require('dayjs/plugin/relativeTime');

dayjs.extend(utc);
dayjs.extend(relativeTime);


const ra_to_hours = (ra) => {
  const ra_h = Math.floor(ra / 15);
  const ra_m = Math.floor((ra % 15) * 4);
  const ra_s = (((ra % 15) * 4) % 1) * 60;
  return `${ra_h}:${ra_m}:${ra_s.toFixed(2)}`;
};

const dec_to_hours = (deci) => {
  const dec = Math.abs(deci);
  const deg = Math.floor(dec);
  const min = Math.floor((dec - deg) * 60);
  const sec = ((dec - deg - (min/60)) * 3600).toFixed(2);
  let sign = "+";
  if (deci < 0) {
    sign = "-";
  }

  return `${sign}${deg}:${min}:${sec}`;
};

function time_relative_to_local(isostring) {
  // Take an ISO 8601 string and return the offset relative to the local time
  return dayjs(isostring).local().fromNow();
}

export { ra_to_hours, dec_to_hours, time_relative_to_local };
