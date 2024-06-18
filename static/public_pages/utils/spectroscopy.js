/* eslint-disable no-unused-vars */
function getLayoutGraphPartSpectroscopy() {
  return {
    autosize: true,
    xaxis: {
      title: "Wavelength (Å)",
      side: "bottom",
      tickformat: ".6~f",
      zeroline: false,
      // eslint-disable-next-line no-undef
      ...BASE_LAYOUT,
    },
    yaxis: {
      title: "Flux",
      side: "left",
      // eslint-disable-next-line no-undef
      ...BASE_LAYOUT,
    },
    margin: {
      l: 70,
      r: 20,
      b: 75,
      t: 80,
      pad: 0,
    },
    shapes: [
      {
        // we use a shape to draw a box around the plot to add borders to it
        type: "rect",
        xref: "paper",
        yref: "paper",
        x0: 0,
        y0: 0,
        x1: 1,
        y1: 1,
        line: {
          color: "black",
          width: 1,
        },
      },
    ],
    showlegend: true,
  };
}

function getLayoutLegendPartSpectroscopy(isMobile) {
  return {
    legend: {
      font: { size: 14 },
      tracegroupgap: 0,
      orientation: isMobile ? "h" : "v",
      y: isMobile ? -0.5 : 1,
      x: isMobile ? 0 : 1,
    },
  };
}

function getLayoutSpectroscopy(isMobile) {
  return {
    ...getLayoutGraphPartSpectroscopy(),
    ...getLayoutLegendPartSpectroscopy(isMobile),
  };
}

/* eslint-disable no-unused-vars */
function getConfigSpectroscopy() {
  return {
    responsive: true,
    displaylogo: false,
    showAxisDragHandles: false,
    modeBarButtonsToRemove: [
      "autoScale2d",
      "resetScale2d",
      "select2d",
      "lasso2d",
      "toggleSpikelines",
      "hoverClosestCartesian",
      "hoverCompareCartesian",
    ],
    modeBarButtonsToAdd: [
      {
        name: "Reset",
        // eslint-disable-next-line no-undef
        icon: Plotly.Icons.home,
        click: () => {
          // eslint-disable-next-line no-undef
          Plotly.relayout(
            document.getElementsByClassName("plotly")[0].parentElement,
            getLayoutGraphPartSpectroscopy(),
          );
        },
      },
    ],
  };
}

/* eslint-disable no-unused-vars */
function getHoverSpectroscopy(spectroscopy) {
  return spectroscopy.wavelengths.map(
    (wavelength, index) =>
      `Wavelengths: ${wavelength}<br>` +
      `Flux: ${spectroscopy.fluxes[index]}<br>` +
      `Telescope: ${spectroscopy.telescope}<br>` +
      `Instrument: ${spectroscopy.instrument}<br>` +
      `PI: ${spectroscopy.pi.length ? spectroscopy.pi[index] : ""}<br>` +
      `Origin: ${spectroscopy.origin}`,
  );
}

/* eslint-disable no-unused-vars */
function spectroscopyPlot(spectroscopy_data, div_id, isMobile) {
  const spectroscopy_tab = JSON.parse(spectroscopy_data);
  const plotData = [];
  spectroscopy_tab.forEach((spectroscopy) => {
    plotData.push({
      mode: "lines",
      type: "scatter",
      dataType: "Spectrum",
      spectrumId: spectroscopy.id,
      x: spectroscopy.wavelengths,
      y: spectroscopy.fluxes.map((flux) => flux),
      text: getHoverSpectroscopy(spectroscopy),
      name: spectroscopy.instrument,
      legendgroup: spectroscopy.id,
      line: {
        shape: "hvh",
        width: 0.85,
        color: "blue",
      },
      hoverlabel: {
        bgcolor: "white",
        font: { size: 14 },
        align: "left",
      },
      hovertemplate: "%{text}<extra></extra>",
    });
  });

  // eslint-disable-next-line no-undef
  Plotly.newPlot(
    document.getElementById(div_id),
    plotData,
    getLayoutSpectroscopy(isMobile),
    getConfigSpectroscopy(),
  );
}
