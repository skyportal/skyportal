const ra_to_hours = ({ ra }) => {
  const ra_h = Math.floor(ra / 15);
  const ra_m = (ra % 15) * 4;
  const ra_s = (ra_m % 1) * 60;
  return `${ra_h}:${ra_m}:${ra_s}`
}

const dec_to_hours = ({ dec }) => {
  const dec_arch = Math.floor(dec);
  const dec_arcm = Math.floor((dec % 1) * 60);
  const dec_arcs = (((dec % 1) * 60) % 1) * 60;
  return `${dec_arch}:${dec_arcm}:${dec_arcs}`
}

export { ra_to_hours, dec_to_hours }
