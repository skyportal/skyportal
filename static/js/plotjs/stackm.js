/* eslint-disable */
const binsize = slider.value;
const fluxalph = ((binsize === 0) ? 1.0 : 0.1);

for (let i = 0; i < toggle.labels.length; i++) {
    const fluxsource = eval(`obs${i}`).data_source;
    const binsource = eval(`bin${i}`).data_source;

    const fluxerrsource = eval(`obserr${i}`).data_source;
    const binerrsource = eval(`binerr${i}`).data_source;

    const unobssource = eval(`unobs${i}`).data_source;
    const unobsbinsource = eval(`unobsbin${i}`).data_source;

    const boldsource = eval(`bold${i}`);
    const allsource = eval(`all${i}`);

    const minmjd = Math.min.apply(Math, fluxsource.data.mjd) - 15;
    const maxmjd = Math.max.apply(Math, fluxsource.data.mjd) + 15;

    boldsource.data.flux = [];
    boldsource.data.fluxerr = [];
    boldsource.data.mjd = [];
    boldsource.data.filter = [];
    boldsource.data.mag = [];
    boldsource.data.magerr = [];
    boldsource.data.lim_mag = [];
    boldsource.data.zp = [];
    boldsource.data.zpsys = [];
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
        for (var j = 0; j < allsource.get_length(); j++) {
            boldsource.data.flux.push(allsource.data.flux[j]);
            boldsource.data.fluxerr.push(allsource.data.fluxerr[j]);
            boldsource.data.mjd.push(allsource.data.mjd[j]);
            boldsource.data.filter.push(allsource.data.filter[j]);
            boldsource.data.mag.push(allsource.data.mag[j]);
            boldsource.data.magerr.push(allsource.data.magerr[j]);
            boldsource.data.lim_mag.push(allsource.data.lim_mag[j]);
            boldsource.data.zp.push(allsource.data.zp[j]);
            boldsource.data.zpsys.push(allsource.data.zpsys[j]);
            boldsource.data.stacked.push(false);

        }
}

    for (var j = 0; j < fluxsource.get_length(); j++) {
        fluxsource.data.alpha[j] = fluxalph;
        fluxerrsource.data.alpha[j] = fluxalph;
    }

    for (var j = 0; j < unobssource.get_length(); j++) {
        if (isFinite(unobssource.data.flux[j])) {
            unobssource.data.alpha[j] = fluxalph;
        } else {
            if (binsize > 0) {
                boldsource.data.flux.push(unobssource.data.flux[j]);
                boldsource.data.fluxerr.push(unobssource.data.fluxerr[j]);
                boldsource.data.mjd.push(unobssource.data.mjd[j]);
                boldsource.data.filter.push(unobssource.data.filter[j]);
                boldsource.data.mag.push(unobssource.data.mag[j]);
                boldsource.data.magerr.push(unobssource.data.magerr[j]);
                boldsource.data.lim_mag.push(unobssource.data.lim_mag[j]);
                boldsource.data.zp.push(unobssource.data.zp[j]);
                boldsource.data.zpsys.push(unobssource.data.zpsys[j]);
                boldsource.data.stacked.push(false);
            }
        }
    }

    if (binsize > 0) {
        // now do the binning
        const k = 0;
        let curmjd = minmjd;
        const mjdbins = [curmjd];

        while (curmjd < maxmjd) {
            curmjd += binsize;
            mjdbins.push(curmjd);
        }

        const nbins = mjdbins.length - 1;
        for (let l = 0; l < nbins; l++) {
            // calculate the flux, fluxerror, and mjd of the bin
            const flux = [];
            const weight = [];
            const mjd = [];
            const limmag = [];
            let ivarsum = 0;

            for (let m = 0; m < allsource.get_length(); m++) {
                if ((allsource.data.mjd[m] < mjdbins[l + 1]) &&
                    (allsource.data.mjd[m] >= mjdbins[l]) &&
                    (isFinite(allsource.data.flux[m]))) {
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

            if (weight.length === 0) {
                continue;
            }

            for (let n = 0; n < weight.length; n++) {
                myflux += weight[n] * flux[n] / ivarsum;
                mymjd += weight[n] * mjd[n] / ivarsum;
            }

            const myfluxerr = Math.sqrt(1 / ivarsum);
            const obs = myflux / myfluxerr > detect_thresh;

            if (obs) {
                var mymag = -2.5 * Math.log10(myflux) + default_zp;
                var mymagerr = Math.abs(-2.5 * myfluxerr / myflux / Math.log(10));
                var mysource = binsource;

                binerrsource.data.xs.push([mymjd, mymjd]);
                binerrsource.data.ys.push([mymag - mymagerr, mymag + mymagerr]);
                binerrsource.data.color.push(allsource.data.color[0]);
            } else {
                var mymag = null;
                var mymagerr = null;
                var mysource = unobsbinsource;
            }

            if (weight.length > 1) {
                var mymaglim = -2.5 * Math.log10(detect_thresh * myfluxerr) + default_zp;
            } else {
                var mymaglim = limmag[0];
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
            boldsource.data.zpsys.push('ab');
            boldsource.data.stacked.push(true);
        }
    }

    fluxsource.change.emit();
    binsource.change.emit();

    fluxerrsource.change.emit();
    binerrsource.change.emit();

    unobssource.change.emit();
    unobsbinsource.change.emit();

    boldsource.change.emit();

}

