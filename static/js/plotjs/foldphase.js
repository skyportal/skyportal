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

const sort_and_smooth = (list, binsize) => {
  let l;
  let k;

  list.sort((a, b) =>
    // eslint-disable-next-line no-nested-ternary
    a.mjd_fold < b.mjd_fold ? -1 : a.mjd_fold === b.mjd_fold ? 0 : 1,
  );
  const mag_sort = list.map((a) => a.mag);
  const mag_sort_smooth = smoothing_func(mag_sort, binsize);
  const mag_sort_smooth_reordered = [];
  for (l = 0; l < list.length; l += 1) {
    for (k = 0; k < list.length; k += 1) {
      if (l === list[k].index) {
        mag_sort_smooth_reordered.push(mag_sort_smooth[k]);
        break;
      }
    }
  }

  return mag_sort_smooth_reordered;
};

// callback inputs: model_dict, n_labels, checkbox, input, slider
slider.value = input.value;

let binsize = 0;
if (0 in checkbox.active) {
  binsize = input.value;
}

/* eslint-disable */
if (numphases.active == 1) {
  /* two phases */
  p.x_range.end = 2.01;
} else {
  p.x_range.end = 1.01;
}
const period = parseFloat(textinput.value);
for (let i = 0; i < n_labels; i++) {
  const folda = eval(`folda${i}`).data_source;
  const foldaerr = eval(`foldaerr${i}`).data_source;
  const foldb = eval(`foldb${i}`).data_source;
  const foldberr = eval(`foldberr${i}`).data_source;
  const mjd = folda.data.mjd;
  for (let m = 0; m < mjd.length; m++) {
    folda.data.mjd_folda[m] = (mjd[m] % period) / period;
    foldaerr.data.xs[m] = [folda.data.mjd_folda[m], folda.data.mjd_folda[m]];
    foldb.data.mjd_foldb[m] = folda.data.mjd_folda[m] + 1;
    foldberr.data.xs[m] = [foldb.data.mjd_foldb[m], foldb.data.mjd_foldb[m]];
  }

  var j;
  if (binsize > 1) {
    var alist = [];
    for (j = 0; j < folda.data.mjd_folda.length; j++) {
      alist.push({
        index: j,
        mjd_fold: folda.data.mjd_folda[j],
        mag: folda.data.mag_unsmoothed[j],
      });
    }
    folda.data.mag = sort_and_smooth(alist, binsize);
    var blist = [];
    for (j = 0; j < foldb.data.mjd_foldb.length; j++) {
      blist.push({
        index: j,
        mjd_fold: foldb.data.mjd_foldb[j],
        mag: foldb.data.mag_unsmoothed[j],
      });
    }
    foldb.data.mag = sort_and_smooth(blist, binsize);
  } else {
    folda.data.mag = folda.data.mag_unsmoothed;
    foldb.data.mag = foldb.data.mag_unsmoothed;
  }

  for (j = 0; j < folda.data.mag.length; j++) {
    foldaerr.data.ys[j] = [
      folda.data.mag[j] - folda.data.magerr[j],
      folda.data.mag[j] + folda.data.magerr[j],
    ];
  }
  for (j = 0; j < foldb.data.mag.length; j++) {
    foldberr.data.ys[j] = [
      foldb.data.mag[j] - foldb.data.magerr[j],
      foldb.data.mag[j] + foldb.data.magerr[j],
    ];
  }

  folda.change.emit();
  foldaerr.change.emit();
  foldb.change.emit();
  foldberr.change.emit();
}
