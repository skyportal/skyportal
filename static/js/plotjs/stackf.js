var binsize = slider.value;
var fluxalph = ((binsize == 0) ? 1. : 0.1);

for (var i = 0; i < toggle.labels.length; i++) {

 var fluxsource = eval("obs" + i).data_source;
 var binsource = eval("bin" + i).data_source;

 var fluxerrsource = eval("obserr" + i).data_source;
 var binerrsource = eval("binerr" + i).data_source;

 var minmjd = Math.min.apply(Math, fluxsource.data['mjd']);

 var date = new Date();     // a new date
 var time = date.getTime(); // the timestamp, not neccessarely using UTC as current time
 var maxmjd = ((time / 86400000) - (date.getTimezoneOffset()/1440) + 40587.);

 binsource.data['mjd'] = [];
 binsource.data['flux'] = [];
 binsource.data['fluxerr'] = [];
 binsource.data['filter'] = [];
 binsource.data['color'] = [];
 binsource.data['lim_mag'] = [];
 binsource.data['mag'] = [];
 binsource.data['magerr'] = [];

 binerrsource.data['xs'] = [];
 binerrsource.data['ys'] = [];
 binerrsource.data['color'] = [];

 for (var j = 0; j < fluxsource.get_length(); j++){
     fluxsource.data['alpha'][j] = fluxalph;
     fluxerrsource.data['alpha'][j] = fluxalph;
 }

 if (binsize > 0){

     // now do the binning
     var k = 0;
     var curmjd = minmjd;
     var mjdbins = [curmjd];

     while (curmjd < maxmjd){
         curmjd += binsize;
         mjdbins.push(curmjd);
     }

     var nbins = mjdbins.length - 1;
     for (var l = 0; l < nbins; l++) {


         // calculate the flux, fluxerror, and mjd of the bin
         var flux = [];
         var weight = [];
         var mjd = [];
         var limmag = [];
         var ivarsum = 0;

         for (var m = 0; m < fluxsource.get_length(); m++){
             if ((fluxsource.data['mjd'][m] < mjdbins[l + 1]) && (fluxsource.data['mjd'][m] >= mjdbins[l])){

                 let fluxvar = fluxsource.data['fluxerr'][m] * fluxsource.data['fluxerr'][m];
                 let ivar = 1 / fluxvar;

                 weight.push(ivar);
                 flux.push(fluxsource.data['flux'][m]);
                 mjd.push(fluxsource.data['mjd'][m]);
                 limmag.push(fluxsource.data['lim_mag']);
                 ivarsum += ivar;
             }
         }

         var myflux = 0;
         var mymjd = 0;

         if (weight.length == 0){
             continue;
         }

         for (var n = 0; n < weight.length; n++){
             myflux += weight[n] * flux[n] / ivarsum;
             mymjd += weight[n] * mjd[n] / ivarsum;
         }

         var myfluxerr = Math.sqrt(1 / ivarsum);


         if (myflux / myfluxerr > 5.){
             var mymag = -2.5 * Math.log10(myflux) + 25;
             var mymagerr = Math.abs(-2.5 * myfluxerr  / myflux / Math.log(10));
         } else {
             var mymag = NaN;
             var mymagerr = NaN;
         }

         var mymaglim = -2.5 * Math.log10(5 * myfluxerr) + 25;

         binsource.data['mjd'].push(mymjd);
         binsource.data['flux'].push(myflux);
         binsource.data['fluxerr'].push(myfluxerr);
         binsource.data['filter'].push(fluxsource.data['filter'][0]);
         binsource.data['color'].push(fluxsource.data['color'][0]);
         binsource.data['mag'].push(mymag);
         binsource.data['magerr'].push(mymagerr);
         binsource.data['lim_mag'].push(mymaglim);

         binerrsource.data['xs'].push([mymjd, mymjd]);
         binerrsource.data['ys'].push([myflux - myfluxerr, myflux + myfluxerr]);
         binerrsource.data['color'].push(fluxsource.data['color'][0]);

     }
 }

 fluxsource.change.emit();
 binsource.change.emit();

 fluxerrsource.change.emit();
 binerrsource.change.emit();
}

