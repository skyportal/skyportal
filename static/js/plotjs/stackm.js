/* eslint no-undef: "off" */
const binsize = slider.value;
const fluxalph = binsize === 0 ? 1.0 : 0.1;

for (let i = 0; i < n_labels; i += 1) {
  const fluxsource = model_dict[`obs${i}`].data_source;
  const binsource = model_dict[`bin${i}`].data_source;

  const fluxerrsource = model_dict[`obserr${i}`].data_source;
  const binerrsource = model_dict[`binerr${i}`].data_source;

  const unobssource = model_dict[`unobs${i}`].data_source;
  const unobsbinsource = model_dict[`unobsbin${i}`].data_source;

  const boldsource = model_dict[`bold${i}`];
  const allsource = model_dict[`all${i}`];

  const minmjd = Math.min(...fluxsource.data.mjd) - 15;
  const maxmjd = Math.max(...fluxsource.data.mjd) + 15;

  boldsource.data.flux = [];
  boldsource.data.fluxerr = [];
  boldsource.data.mjd = [];
  boldsource.data.filter = [];
  boldsource.data.mag = [];
  boldsource.data.magerr = [];
  boldsource.data.lim_mag = [];
  boldsource.data.zp = [];
  boldsource.data.magsys = [];
  boldsource.data.stacked = [];

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

  unobsbinsource.data.mjd = [];
  unobsbinsource.data.lim_mag = [];
  unobsbinsource.data.color = [];
  unobsbinsource.data.flux = [];
  unobsbinsource.data.fluxerr = [];
  unobsbinsource.data.mag = [];
  unobsbinsource.data.magerr = [];
  unobsbinsource.data.filter = [];
  unobsbinsource.data.stacked = [];
  unobsbinsource.data.instrument = [];

  if (binsize === 0) {
    for (let j = 0; j < allsource.get_length(); j += 1) {
      boldsource.data.flux.push(allsource.data.flux[j]);
      boldsource.data.fluxerr.push(allsource.data.fluxerr[j]);
      boldsource.data.mjd.push(allsource.data.mjd[j]);
      boldsource.data.filter.push(allsource.data.filter[j]);
      boldsource.data.mag.push(allsource.data.mag[j]);
      boldsource.data.magerr.push(allsource.data.magerr[j]);
      boldsource.data.lim_mag.push(allsource.data.lim_mag[j]);
      boldsource.data.zp.push(allsource.data.zp[j]);
      boldsource.data.magsys.push(allsource.data.magsys[j]);
      boldsource.data.stacked.push(false);
    }
  }

  for (let j = 0; j < fluxsource.get_length(); j += 1) {
    fluxsource.data.alpha[j] = fluxalph;
    fluxerrsource.data.alpha[j] = fluxalph;
  }

  for (let j = 0; j < unobssource.get_length(); j += 1) {
    if (Number.isFinite(unobssource.data.flux[j])) {
      unobssource.data.alpha[j] = fluxalph;
    } else if (binsize > 0) {
      boldsource.data.flux.push(unobssource.data.flux[j]);
      boldsource.data.fluxerr.push(unobssource.data.fluxerr[j]);
      boldsource.data.mjd.push(unobssource.data.mjd[j]);
      boldsource.data.filter.push(unobssource.data.filter[j]);
      boldsource.data.mag.push(unobssource.data.mag[j]);
      boldsource.data.magerr.push(unobssource.data.magerr[j]);
      boldsource.data.lim_mag.push(unobssource.data.lim_mag[j]);
      boldsource.data.zp.push(unobssource.data.zp[j]);
      boldsource.data.magsys.push(unobssource.data.magsys[j]);
      boldsource.data.stacked.push(false);
    }
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

      for (let m = 0; m < allsource.get_length(); m += 1) {
        if (
          allsource.data.mjd[m] < mjdbins[l + 1] &&
          allsource.data.mjd[m] >= mjdbins[l] &&
          Number.isFinite(allsource.data.flux[m])
        ) {
          const fluxvar = allsource.data.fluxerr[m] * allsource.data.fluxerr[m];
          const ivar = 1 / fluxvar;

          weight.push(ivar);
          flux.push(allsource.data.flux[m]);
          mjd.push(allsource.data.mjd[m]);
          limmag.push(allsource.data.lim_mag[m]);
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
        const obs = myflux / myfluxerr > detect_thresh;

        let mysource;
        let mymag;
        let mymagerr;
        let mymaglim;
        if (obs) {
          mymag = -2.5 * Math.log10(myflux) + default_zp;
          mymagerr = Math.abs((-2.5 * myfluxerr) / myflux / Math.log(10));
          mysource = binsource;

          binerrsource.data.xs.push([mymjd, mymjd]);
          binerrsource.data.ys.push([mymag - mymagerr, mymag + mymagerr]);
          binerrsource.data.color.push(allsource.data.color[0]);
        } else {
          mymag = null;
          mymagerr = null;
          mysource = unobsbinsource;
        }

        if (weight.length > 1) {
          mymaglim = -2.5 * Math.log10(detect_thresh * myfluxerr) + default_zp;
        } else {
          [mymaglim] = limmag;
        }

        mysource.data.mjd.push(mymjd);
        mysource.data.flux.push(myflux);
        mysource.data.fluxerr.push(myfluxerr);
        mysource.data.filter.push(allsource.data.filter[0]);
        mysource.data.color.push(allsource.data.color[0]);
        mysource.data.mag.push(mymag);
        mysource.data.magerr.push(mymagerr);
        mysource.data.lim_mag.push(mymaglim);
        mysource.data.stacked.push(true);
        mysource.data.instrument.push(allsource.data.instrument[0]);

        boldsource.data.flux.push(myflux);
        boldsource.data.fluxerr.push(myfluxerr);
        boldsource.data.mjd.push(mymjd);
        boldsource.data.filter.push(allsource.data.filter[0]);
        boldsource.data.mag.push(mymag);
        boldsource.data.magerr.push(mymagerr);
        boldsource.data.lim_mag.push(mymaglim);
        boldsource.data.zp.push(default_zp);
        boldsource.data.magsys.push("ab");
        boldsource.data.stacked.push(true);
      }
    }

    // Remove Brokeh-generated 'index' column from converting Pandas DataFrame
    // The indices will have no meaning once data is binned and is unused
    delete boldsource.data.index;
  }

  fluxsource.change.emit();
  binsource.change.emit();

  fluxerrsource.change.emit();
  binerrsource.change.emit();

  unobssource.change.emit();
  unobsbinsource.change.emit();

  boldsource.change.emit();
}
