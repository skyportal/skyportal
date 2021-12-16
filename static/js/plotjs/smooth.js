/* eslint-disable */
const smoothing_func = (values, window_size) => {
  if (values === undefined || values === null) {
    return null;
  }
  const output = new Array(values.length).fill(0);
  const under = parseInt(window_size / 2) - 1;
  const over = parseInt(window_size / 2);

  for (let i = 0; i < values.length; i++) {
    const idx_low = i - under >= 0 ? i - under : 0;
    const idx_high = i + over < values.length ? i + over : values.length - 1;
    let N = 0;
    for (let j = idx_low; j < idx_high; j++) {
      N++;
      output[i] += values[j];
    }
    output[i] /= N;
  }
  return output;
};
plots.forEach((p) => {
  let new_flux = [];
  if (0 in checkbox.active) {
    new_flux = smoothing_func(p.data_source.data.flux_original, window.value);
  } else {
    new_flux = p.data_source.data.flux_original;
  }
  p.data_source.data.flux = new_flux;
  p.data_source.change.emit();
});
