function median(values) {
  const sorted = values.slice().sort((a, b) => a - b);
  const half = Math.floor(values.length / 2);
  return values.length % 2 !== 0
    ? sorted[half]
    : (sorted[half - 1] + sorted[half]) / 2.0;
}

function mean(values) {
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function spectroscopyPlot(spectroscopy_data, div_id, isMobile) {
  const spectroscopy_tab = JSON.parse(spectroscopy_data);
  const plotData = [];

  // Data processing
  spectroscopy_tab.forEach((spectroscopy, index) => {
    const updateFluxes = [];
    const updateWavelengths = [];
    const normFactor = Math.abs(median(spectroscopy.fluxes)) || 1e-20;

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
      name: `${spectroscopy.instrument} (${new Date(
        spectroscopy.observed_at,
      ).toLocaleDateString()})`,
      legendgroup: spectroscopy.id,
      line: {
        shape: "hvh",
        width: 0.85,
        color: `hsl(${Math.round(
          240 - (index / (spectroscopy_tab.length - 1)) * 240,
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
  function getBaseLayout() {
    return {
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
  }

  function getMaxFlux(spectroscopy_tab) {
    let max = 0;
    spectroscopy_tab.forEach((spectroscopy) => {
      let fluxes = spectroscopy.fluxes;
      const maxFlux = Math.max(...fluxes);
      if (maxFlux > 10 * median(fluxes) || maxFlux > 10 * mean(fluxes)) {
        fluxes = fluxes.map((flux) => (flux > 0 ? flux : 0));
        fluxes.sort((a, b) => a - b);
        const q1 = fluxes[Math.floor(fluxes.length * 0.25)];
        const q3 = fluxes[Math.floor(fluxes.length * 0.75)];
        const upperFence = 2.5 * q3 - 1.5 * q1;
        max = Math.max(max, upperFence);
      } else {
        max = Math.max(max, maxFlux);
      }
    });
    return max;
  }

  function getLayoutGraphPart() {
    return {
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
        ...getBaseLayout(),
      },
      yaxis: {
        title: "Flux",
        side: "left",
        range: [0, getMaxFlux(spectroscopy_tab) * 1.05],
        ...getBaseLayout(),
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

  function getLayoutLegendPart() {
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

  function getConfig() {
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
          icon: Plotly.Icons.home, // eslint-disable-line no-undef
          click: (plotElement) => {
            // eslint-disable-next-line no-undef
            Plotly.relayout(plotElement, getLayoutGraphPart());
          },
        },
      ],
    };
  }

  function getHoverTexts(spectroscopy) {
    return spectroscopy.wavelengths.map(
      (wavelength, index) =>
        `Wavelengths: ${wavelength}<br>` +
        `Flux: ${spectroscopy.fluxes[index]}<br>` +
        `Telescope: ${spectroscopy.telescope}<br>` +
        `Instrument: ${spectroscopy.instrument}<br>` +
        `Observed at (UTC): ${spectroscopy.observed_at}<br>` +
        `PI: ${spectroscopy.pi.length ? spectroscopy.pi[index] : ""}<br>` +
        `Origin: ${spectroscopy.origin}`,
    );
  }

  // eslint-disable-next-line no-undef
  Plotly.newPlot(
    document.getElementById(div_id),
    plotData,
    { ...getLayoutGraphPart(), ...getLayoutLegendPart() },
    getConfig(),
  );
}
