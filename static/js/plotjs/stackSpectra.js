/* eslint-disable */
const binsize = bin_slider.value;
const fluxalph = binsize === 0 ? 1.0 : 0.1;

for (let i = 0; i < n_labels; i++) {
  const spectra = eval(`s${i}`);
  const fluxsource = spectra.data_source;
  const binsource = eval(`bin${i}`).data_source;

  const minWavelength = Math.min.apply(Math, fluxsource.data.wavelength) - 100;
  const maxWavelength = Math.max.apply(Math, fluxsource.data.wavelength) + 100;

  binsource.data.wavelength = [];
  binsource.data.flux = [];
  binsource.data.telescope = [];
  binsource.data.instrument = [];
  binsource.data.date_observed = [];
  binsource.data.id = [];
  binsource.data.pi = [];
  binsource.data.origin = [];
  binsource.data.altdata = [];

  spectra.glyph.line_alpha = fluxalph;

  if (binsize > 0) {
    // now do the binning
    const k = 0;
    let curWavelength = minWavelength;
    const wavelengthBins = [curWavelength];

    while (curWavelength < maxWavelength) {
      curWavelength += binsize * 10;
      wavelengthBins.push(curWavelength);
    }

    const nbins = wavelengthBins.length - 1;
    for (let l = 0; l < nbins; l++) {
      // calculate the flux of the bin
      const flux = [];
      const wavelength = [];
      for (let m = 0; m < fluxsource.get_length(); m++) {
        if (
          fluxsource.data.wavelength[m] < wavelengthBins[l + 1] &&
          fluxsource.data.wavelength[m] >= wavelengthBins[l]
        ) {
          flux.push(fluxsource.data.flux[m]);
          wavelength.push(fluxsource.data.wavelength[m]);
        }
      }

      const myflux = flux.reduce((a, b) => a + b, 0) / flux.length;
      const mywavelength =
        wavelength.reduce((a, b) => a + b, 0) / wavelength.length;

      binsource.data.wavelength.push(mywavelength);
      binsource.data.flux.push(myflux);
      binsource.data.id.push(fluxsource.data.id[0]);
      binsource.data.instrument.push(fluxsource.data.instrument[0]);
      binsource.data.telescope.push(fluxsource.data.telescope[0]);
      binsource.data.date_observed.push(fluxsource.data.date_observed[0]);
      binsource.data.pi.push(fluxsource.data.pi[0]);
      binsource.data.origin.push(fluxsource.data.origin[0]);
      binsource.data.altdata.push(fluxsource.data.altdata[0]);
    }
  }

  fluxsource.change.emit();
  binsource.change.emit();
}
