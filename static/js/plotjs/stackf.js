/* eslint no-undef: "off" */
const binsize = slider.value;
const fluxalph = binsize === 0 ? 1.0 : 0.1;

for (let i = 0; i < n_labels; i += 1) {
  const fluxsource = model_dict[`obs${i}`].data_source;
  const binsource = model_dict[`bin${i}`].data_source;

  const fluxerrsource = model_dict[`obserr${i}`].data_source;
  const binerrsource = model_dict[`binerr${i}`].data_source;

  const minmjd = Math.min(...fluxsource.data.mjd) - 15;
  const maxmjd = Math.max(...fluxsource.data.mjd) + 15;

  binsource.data.mjd = [];
  binsource.data.flux = [];
  binsource.data.fluxerr = [];
  binsource.data.filter = [];
  binsource.data.color = [];
  binsource.data.lim_mag = [];
  binsource.data.mag = [];
  binsource.data.magerr = [];
  binsource.data.instrument = [];
  binsource.data.stacked = [];

  binerrsource.data.xs = [];
  binerrsource.data.ys = [];
  binerrsource.data.color = [];

  for (let j = 0; j < fluxsource.get_length(); j += 1) {
    fluxsource.data.alpha[j] = fluxalph;
    fluxerrsource.data.alpha[j] = fluxalph;
  }

  if (binsize > 0) {
    // now do the binning
    let curmjd = minmjd;
    const mjdbins = [curmjd];

    while (curmjd < maxmjd) {
      curmjd += binsize;
      mjdbins.push(curmjd);
    }

    const nbins = mjdbins.length - 1;
    for (let l = 0; l < nbins; l += 1) {
      // calculate the flux, fluxerror, and mjd of the bin
      const flux = [];
      const weight = [];
      const mjd = [];
      const limmag = [];
      let ivarsum = 0;

      for (let m = 0; m < fluxsource.get_length(); m += 1) {
        if (
          fluxsource.data.mjd[m] < mjdbins[l + 1] &&
          fluxsource.data.mjd[m] >= mjdbins[l]
        ) {
          const fluxvar =
            fluxsource.data.fluxerr[m] * fluxsource.data.fluxerr[m];
          const ivar = 1 / fluxvar;

          weight.push(ivar);
          flux.push(fluxsource.data.flux[m]);
          mjd.push(fluxsource.data.mjd[m]);
          limmag.push(fluxsource.data.lim_mag);
          ivarsum += ivar;
        }
      }

      let myflux = 0;
      let mymjd = 0;

      if (weight.length !== 0) {
        for (let n = 0; n < weight.length; n += 1) {
          myflux += (weight[n] * flux[n]) / ivarsum;
          mymjd += (weight[n] * mjd[n]) / ivarsum;
        }

        const myfluxerr = Math.sqrt(1 / ivarsum);

        let mymag;
        let mymagerr;
        if (myflux / myfluxerr > detect_thresh) {
          mymag = -2.5 * Math.log10(myflux) + default_zp;
          mymagerr = Math.abs((-2.5 * myfluxerr) / myflux / Math.log(10));
        } else {
          mymag = NaN;
          mymagerr = NaN;
        }

        const mymaglim =
          -2.5 * Math.log10(detect_thresh * myfluxerr) + default_zp;

        binsource.data.mjd.push(mymjd);
        binsource.data.flux.push(myflux);
        binsource.data.fluxerr.push(myfluxerr);
        binsource.data.filter.push(fluxsource.data.filter[0]);
        binsource.data.color.push(fluxsource.data.color[0]);
        binsource.data.mag.push(mymag);
        binsource.data.magerr.push(mymagerr);
        binsource.data.lim_mag.push(mymaglim);
        binsource.data.instrument.push(fluxsource.data.instrument[0]);
        binsource.data.stacked.push(true);

        binerrsource.data.xs.push([mymjd, mymjd]);
        binerrsource.data.ys.push([myflux - myfluxerr, myflux + myfluxerr]);
        binerrsource.data.color.push(fluxsource.data.color[0]);
      }
    }
  }

  fluxsource.change.emit();
  binsource.change.emit();

  fluxerrsource.change.emit();
  binerrsource.change.emit();
}
