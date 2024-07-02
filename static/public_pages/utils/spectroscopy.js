function spectroscopyPlot(spectroscopy_data, div_id, isMobile) {
  const spectroscopy_tab = JSON.parse(spectroscopy_data);
  const plotData = [];

  // Data processing
  spectroscopy_tab.forEach((spectroscopy, index) => {
    const updateFluxes = [];
    const updateWavelengths = [];

    const getNormFactor = (val) => {
      const sorted = val.slice().sort((a, b) => a - b);
      const half = Math.floor(val.length / 2);
      const median =
        val.length % 2 !== 0
          ? sorted[half]
          : (sorted[half - 1] + sorted[half]) / 2.0;
      return Math.abs(median) || 1e-20;
    };
    const normFactor = getNormFactor(spectroscopy.fluxes);

    const isNullOrNaN = (val) => val === null || isNaN(val);
    spectroscopy.fluxes.forEach((flux, index) => {
      let wavelength = spectroscopy.wavelengths[index];
      let normedFlux = flux / normFactor;
      if (!isNullOrNaN(normedFlux) && !isNullOrNaN(wavelength)) {
        updateFluxes.push(normedFlux);
        updateWavelengths.push(wavelength);
      }
    });
    spectroscopy.fluxes = updateFluxes;
    spectroscopy.wavelengths = updateWavelengths;
    if (spectroscopy.fluxes.length === 0) return;

    plotData.push({
      mode: "lines",
      type: "scatter",
      dataType: "Spectrum",
      spectrumId: spectroscopy.id,
      x: spectroscopy.wavelengths,
      y: spectroscopy.fluxes,
      text: getHoverTexts(spectroscopy),
      name: spectroscopy.instrument,
      legendgroup: spectroscopy.id,
      line: {
        shape: "hvh",
        width: 0.85,
        color: `hsl(${Math.round(
          240 - (index / spectroscopy.length - 1) * 240,
        )}, 90%, 50%)`,
      },
      hoverlabel: {
        bgcolor: "white",
        font: { size: 14 },
        align: "left",
      },
      hovertemplate: "%{text}<extra></extra>",
    });
  });

  // Plot configuration
  const baseLayout = {
    zeroline: false,
    automargin: true,
    showline: true,
    titlefont: { size: 18 },
    tickfont: { size: 14 },
    ticklen: 12,
    ticks: "outside",
    nticks: 8,
    minor: {
      ticks: "outside",
      ticklen: 6,
      tickcolor: "black",
    },
  };

  const layoutGraphPart = {
    autosize: true,
    xaxis: {
      title: "Wavelength (Å)",
      side: "bottom",
      tickformat: ".6~f",
      zeroline: false,
      range: [
        Math.min(
          ...spectroscopy_tab.map((spectroscopy) =>
            Math.min(...spectroscopy.wavelengths),
          ),
        ) - 100,
        Math.max(
          ...spectroscopy_tab.map((spectroscopy) =>
            Math.max(...spectroscopy.wavelengths),
          ),
        ) + 100,
      ],
      ...baseLayout,
    },
    yaxis: {
      title: "Flux",
      side: "left",
      range: [
        0,
        Math.max(
          ...spectroscopy_tab.map((spectroscopy) =>
            Math.max(...spectroscopy.fluxes),
          ),
        ) * 1.05,
      ],
      ...baseLayout,
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

  const layoutLegendPart = {
    legend: {
      font: { size: 14 },
      tracegroupgap: 0,
      orientation: isMobile ? "h" : "v",
      y: isMobile ? -0.5 : 1,
      x: isMobile ? 0 : 1,
    },
  };

  const config = {
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
        icon: Plotly.Icons.home,
        click: () => {
          Plotly.relayout(
            document.getElementsByClassName("plotly")[0].parentElement,
            layoutGraphPart,
          );
        },
      },
    ],
  };

  function getHoverTexts(spectroscopy) {
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

  Plotly.newPlot(
    document.getElementById(div_id),
    plotData,
    { ...layoutGraphPart, ...layoutLegendPart },
    config,
  );
}
