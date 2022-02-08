/* eslint no-undef: "off" */
const smoothing_func = (values, window_size) => {
  if (values === undefined || values === null) {
    return null;
  }
  const output = new Array(values.length).fill(0);
  const under = parseInt((window_size + 1) / 2, 10) - 1;
  const over = parseInt(window_size / 2, 10);

  for (let i = 0; i < values.length; i += 1) {
    const idx_low = i - under >= 0 ? i - under : 0;
    const idx_high = i + over < values.length ? i + over : values.length - 1;
    let N = 0;
    for (let j = idx_low; j <= idx_high; j += 1) {
      if (Number.isNaN(values[j]) === false) {
        N += 1;
        output[i] += values[j];
      }
    }
    output[i] /= N;
  }
  return output;
};

// callback inputs: model_dict, n_labels, checkbox, input, slider
slider.value = input.value;

let binsize = 0;
if (0 in checkbox.active) {
  binsize = input.value;
}
const fluxalph = binsize === 0 ? 1.0 : 0.1;

for (let i = 0; i < n_labels; i += 1) {
  const spectra = model_dict[`s${i}`];
  const fluxsource = spectra.data_source;
  const binsource = model_dict[`bin${i}`].data_source;

  spectra.glyph.line_alpha = fluxalph;

  if (binsize > 1) {
    binsource.data.flux = smoothing_func(fluxsource.data.flux, binsize);
  } else {
    binsource.data.flux = fluxsource.data.flux;
  }

  fluxsource.change.emit();
  binsource.change.emit();
}
