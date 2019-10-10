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

export { ra_to_hours, dec_to_hours };
