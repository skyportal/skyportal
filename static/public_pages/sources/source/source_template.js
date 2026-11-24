/* eslint-disable no-undef */

window.isMobile = window.matchMedia("(max-width: 900px)").matches;
// Move the legend and change marker size when the window is in mobile size
window.addEventListener("resize", () => {
  const isActualMobile = window.matchMedia("(max-width: 900px)").matches;
  if (window.isMobile !== isActualMobile) {
    window.isMobile = isActualMobile;
    Array.from(document.getElementsByClassName("plotly")).forEach((plotDiv) => {
      Plotly.relayout(plotDiv.parentElement, {
        legend: {
          orientation: isActualMobile ? "h" : "v",
          y: isActualMobile ? -0.5 : 1,
          x: isActualMobile ? 0 : 1,
        },
      });
      Plotly.restyle(plotDiv.parentElement, {
        "marker.size": isActualMobile ? 6 : 9,
      });
    });
  }
});

const FETCHED_CUTOUT_TYPES = ["sdss", "ls"];
const CUTOUT_TIMEOUT_MS = 15000;

function showCutout(cutout, src) {
  const image = cutout.querySelector(".cutoutImage");
  image.onload = () => cutout.classList.add("loaded");
  image.onerror = () => cutout.classList.add("unavailable");
  image.src = src;
}

async function fetchCutout(cutout, src, type) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), CUTOUT_TIMEOUT_MS);
  try {
    const response = await fetch(src, { signal: controller.signal });
    const blob = response.ok ? await response.blob() : null;
    // Legacy Survey answers outside its footprint with a small grey placeholder.
    if (!blob || (type === "ls" && blob.size < 1500)) {
      cutout.remove();
    } else {
      showCutout(cutout, URL.createObjectURL(blob));
    }
  } catch {
    cutout.remove();
  } finally {
    clearTimeout(timeout);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".sexagesimal").forEach((element) => {
    element.textContent = radec_hhmmss(
      Number(element.dataset.ra),
      Number(element.dataset.dec),
    );
  });
  document.querySelectorAll(".cutout").forEach((cutout) => {
    const { type, src } = cutout.dataset;
    if (FETCHED_CUTOUT_TYPES.includes(type)) {
      fetchCutout(cutout, src, type);
    } else {
      showCutout(cutout, src);
    }
  });
});

const ra_to_hours = (ra, sep = null) => {
  const ra_h = String(Math.floor(ra / 15)).padStart(2, "0");
  const ra_m = String(Math.floor((ra % 15) * 4)).padStart(2, "0");
  const ra_s = String(((((ra % 15) * 4) % 1) * 60).toFixed(2)).padStart(5, "0");
  if (sep !== null) {
    return `${ra_h}${sep}${ra_m}${sep}${ra_s}`;
  }
  return `${ra_h}h${ra_m}m${ra_s}s`;
};

const dec_to_dms = (deci, sep = null, signed = true) => {
  const dec = Math.abs(deci);
  const deg = String(Math.floor(dec)).padStart(2, "0");
  const min = String(Math.floor((dec - deg) * 60)).padStart(2, "0");
  const sec = ((dec - deg - min / 60) * 3600).toFixed(2).padStart(5, "0");

  // this is for the case where the '+' sign needs to be omitted
  let sign = "";
  if (signed) {
    sign = deci < 0 ? "-" : "+";
  }

  if (!(sep == null)) {
    return `${sign}${deg}${sep}${min}${sep}${sec}`;
  }
  return `${sign}${deg}d${min}m${sec}s`;
};

const radec_hhmmss = (ra, dec) =>
  `${ra_to_hours(ra, ":")} ${dec_to_dms(dec, ":")}`;
