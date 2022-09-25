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

  if (binsize > 1) {
    var j;
    var k;

    var alist = [];
    for (j = 0; j < folda.data.mjd_folda.length; j++) {
      alist.push({
        index: j,
        mjd_folda: folda.data.mjd_folda[j],
        mag: folda.data.mag[j],
      });
    }
    alist.sort(function (a, b) {
      return a.mjd_folda < b.mjd_folda
        ? -1
        : a.mjd_folda == b.mjd_folda
        ? 0
        : 1;
    });
    const amag_sort = [];
    for (j = 0; j < alist.length; j++) {
      amag_sort[j] = alist[j].mag;
    }
    const amag_sort_smooth = smoothing_func(amag_sort, binsize);
    const amag_sort_smooth_reordered = [];
    for (var j = 0; j < folda.data.mjd_folda.length; j++) {
      for (var k = 0; k < folda.data.mjd_folda.length; k++) {
        if (j == alist[k].index) {
          amag_sort_smooth_reordered.push(amag_sort_smooth[k]);
          foldaerr.data.ys[j] = [amag_sort_smooth[k], amag_sort_smooth[k]];
          break;
        }
      }
    }
    folda.data.mag = amag_sort_smooth_reordered;

    var blist = [];
    for (j = 0; j < folda.data.mjd_folda.length; j++) {
      blist.push({
        index: j,
        mjd_foldb: foldb.data.mjd_foldb[j],
        mag: foldb.data.mag[j],
      });
    }
    blist.sort(function (a, b) {
      return a.mjd_foldb < b.mjd_foldb
        ? -1
        : a.mjd_foldb == b.mjd_foldb
        ? 0
        : 1;
    });
    const bmag_sort = [];
    for (j = 0; j < blist.length; j++) {
      bmag_sort[j] = blist[j].mag;
    }
    const bmag_sort_smooth = smoothing_func(bmag_sort, binsize);
    const bmag_sort_smooth_reordered = [];
    for (j = 0; j < foldb.data.mjd_folda.length; j++) {
      for (k = 0; k < foldb.data.mjd_folda.length; k++) {
        if (j == blist[k].index) {
          bmag_sort_smooth_reordered.push(bmag_sort_smooth[k]);
          foldberr.data.ys[j] = [bmag_sort_smooth[k], bmag_sort_smooth[k]];
          break;
        }
      }
    }
    foldb.data.mag = bmag_sort_smooth_reordered;
  }

  folda.change.emit();
  foldaerr.change.emit();
  foldb.change.emit();
  foldberr.change.emit();
}
