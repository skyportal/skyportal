/* eslint-disable */
const period = parseFloat(textinput.value);
for (let i = 0; i < toggle.labels.length; i++) {
  const folda = eval(`folda${i}`).data_source;
  const foldb = eval(`foldb${i}`).data_source;
  const foldaerr = eval(`foldaerr${i}`).data_source;
  const foldberr = eval(`foldberr${i}`).data_source;
  const mjd = folda.data.mjd;
  for (let m = 0; m < mjd.length; m++) {
    folda.data.mjd_folda[m] = (mjd[m] % period) / period;
    foldb.data.mjd_foldb[m] = folda.data.mjd_folda[m] + 1;
    foldaerr.data.xs[m] = [folda.data.mjd_folda[m], folda.data.mjd_folda[m]];
    foldberr.data.xs[m] = [foldb.data.mjd_foldb[m], foldb.data.mjd_foldb[m]];
  }
  folda.change.emit();
  foldb.change.emit();
  foldaerr.change.emit();
  foldberr.change.emit();
}
