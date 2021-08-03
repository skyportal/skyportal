/* eslint no-undef: "off" */
if (numphases.active === 1) {
  /* two phases */
  p.x_range.end = 2.01;
} else {
  p.x_range.end = 1.01;
}
const period = parseFloat(textinput.value);
for (let i = 0; i < n_labels; i += 1) {
  const folda = model_dict[`folda${i}`].data_source;
  const foldaerr = model_dict[`foldaerr${i}`].data_source;
  const foldb = model_dict[`foldb${i}`].data_source;
  const foldberr = model_dict[`foldberr${i}`].data_source;
  const { mjd } = folda.data;
  for (let m = 0; m < mjd.length; m += 1) {
    folda.data.mjd_folda[m] = (mjd[m] % period) / period;
    foldaerr.data.xs[m] = [folda.data.mjd_folda[m], folda.data.mjd_folda[m]];
    foldb.data.mjd_foldb[m] = folda.data.mjd_folda[m] + 1;
    foldberr.data.xs[m] = [foldb.data.mjd_foldb[m], foldb.data.mjd_foldb[m]];
  }
  folda.change.emit();
  foldaerr.change.emit();
  foldb.change.emit();
  foldberr.change.emit();
}
