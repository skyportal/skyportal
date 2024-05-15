/* global Plotly */
function ModifiedJulianDateFromUnixTime(t) {
  return t / 86400000 + 40587;
}

function ModifiedJulianDateNow() {
  return ModifiedJulianDateFromUnixTime(new Date().getTime());
}

/* eslint-disable no-unused-vars */
function plot_lc(photometry_data, div_id, filters_used_mapper) {
  const filters_mapper = JSON.parse(filters_used_mapper);
  const photometry = JSON.parse(photometry_data);
  const now = ModifiedJulianDateNow();
  const names_already_seen = [];
  const plot_data = [];
  const filterToColor = (filter) => filters_mapper[filter] || "blue";

  photometry.forEach((element) => {
    let name = `${element.instrument_name}/${element.filter}`;
    if (element.origin !== "None") {
      name = `${name}/${element.origin}`;
    }
    const data = {
      x: [now - element.mjd],
      y: element.mag === null ? [element.limiting_mag] : [element.mag],
      name,
      error_y: {
        type: "data",
        array: [element.magerr],
        visible: true,
        color: filterToColor[element.filter],
        width: 2,
        thickness: 0.8,
        opacity: 0.5,
      },
      legendgroup: name,
      marker: {
        symbol: element.mag === null ? "triangle-down" : "circle",
        color: filterToColor(element.filter),
        opacity: 0.8,
        size: 8,
      },
      line: {
        color: filterToColor(element.filter),
        width: 2,
        opacity: 0.8,
      },
      mode: "markers+lines",
      // use a hover template to display:
      // - mjd
      // - mag
      // - magerr
      // - filter
      // - limiting_mag
      // - instrument_id
      text: `mjd: ${element.mjd.toFixed(6)}<br>mag: ${
        element.mag ? element.mag.toFixed(4) : element.mag
      }<br>magerr: ${
        element.magerr ? element.magerr.toFixed(4) : element.magerr
      }<br>filter: ${element.filter}<br>limmag: ${
        element.limiting_mag
          ? element.limiting_mag.toFixed(4)
          : element.limiting_mag
      }<br>instrument: ${element.instrument_name}`,
    };
    data.showlegend = !names_already_seen.includes(name);
    plot_data.push(data);
    names_already_seen.push(name);
  });
  const layout = {
    autosize: true,
    xaxis: { title: "Days ago", autorange: "reversed" },
    yaxis: { title: "AB Mag", autorange: "reversed" },
    margin: { l: 50, r: 50, b: 30, t: 30, pad: 1 },
  };
  const config = { responsive: true };

  Plotly.newPlot(document.getElementById(div_id), plot_data, layout, config);
}
