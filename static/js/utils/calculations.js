function median(values) {
  if (values.length === 0) throw new Error("No inputs");

  const sorted = [...values].sort((a, b) => a - b);
  const half = Math.floor(sorted.length / 2);

  if (sorted.length % 2) return sorted[half];
  return (sorted[half - 1] + sorted[half]) / 2.0;
}

function mean(values) {
  if (values.length === 0) throw new Error("No inputs");
  return values.reduce((a, b) => a + b) / values.length;
}

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

function colorScaleRainbow(index, rangeMax) {
  return `hsl(${Math.round(240 - (index / rangeMax) * 240)}, 90%, 50%)`;
}

const rgba = (rgb, alpha) => `rgba(${rgb[0]},${rgb[1]},${rgb[2]}, ${alpha})`;

function unix2mjd(t) {
  return t / 86400000 + 40587;
}

function mjdnow() {
  return unix2mjd(new Date().getTime());
}

export {
  median,
  mean,
  smoothing_func,
  rgba,
  unix2mjd,
  mjdnow,
  colorScaleRainbow,
};
