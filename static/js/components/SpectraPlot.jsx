import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import Slider from "@mui/material/Slider";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import Button from "./Button";

import {
  BASE_LAYOUT,
  C,
  LINES,
  median,
  mean,
  smoothing_func,
  hsl,
} from "../utils";

const Plot = createPlotlyComponent(Plotly);

const SpectraPlot = ({ spectra, redshift, mode, plotStyle }) => {
  const [data, setData] = useState(null);
  const [plotData, setPlotData] = useState(null);

  const [selectedLines, setSelectedLines] = useState([]);

  const [vExpInput, setVExpInput] = useState(0);
  const [redshiftInput, setRedshiftInput] = useState(redshift || 0);
  const [smoothingInput, setSmoothingInput] = useState(0);
  const [customWavelengthInput, setCustomWavelengthInput] = useState(0);

  const [specStats, setSpecStats] = useState(null);
  const [layouts, setLayouts] = useState({});

  const [layoutReset, setLayoutReset] = useState(false);

  const { preferences } = useSelector((state) => state.profile);

  // the user preferences' spectroscopyButtons is an object with the name of the button as the key, and the value is an object with the color and the wavelengths
  // transform that into a list of objects with the name, color and wavelengths
  const userCustomLines = Object.keys(
    preferences?.spectroscopyButtons || {},
  ).map((key) => ({
    name: key,
    color: preferences?.spectroscopyButtons[key].color,
    x: preferences?.spectroscopyButtons[key].wavelengths,
  }));

  const [types, setTypes] = useState([]);
  const [tabIndex, setTabIndex] = useState(0);

  const findTypes = (spectraData) => {
    let spectrumTypes = [];
    spectraData.forEach((spectrum) => {
      if (
        spectrum.type &&
        spectrum.type !== "" &&
        !(spectrum.type in spectrumTypes)
      ) {
        spectrumTypes.push(spectrum.type);
      }
    });
    // remove duplicates
    spectrumTypes = [...new Set(spectrumTypes)];

    // sort by alphabetical order descending
    spectrumTypes.sort((a, b) => {
      if (a < b) {
        return 1;
      }
      return -1;
    });
    return spectrumTypes;
  };

  const prepareSpectra = (spectraData, spectrumTypes) => {
    const stats = {};
    spectrumTypes.forEach((type) => {
      stats[type] = {
        flux: {
          min: 0,
          max: 0,
          maxLines: 0,
          range: [0, 1],
        },
        wavelength: {
          min: 100000,
          max: 0,
          range: [0, 100000],
        },
      };
    });

    const newSpectra = spectraData.map((spectrum) => {
      const newSpectrum = { ...spectrum };
      let normfac = Math.abs(median(newSpectrum.fluxes));
      normfac = normfac !== 0.0 ? normfac : 1e-20;
      newSpectrum.fluxes_normed = newSpectrum.fluxes.map(
        (flux) => flux / normfac,
      );
      newSpectrum.text = newSpectrum.wavelengths.map(
        (wavelength, index) =>
          `Wavelength: ${wavelength.toFixed(3)}
          <br>Flux: ${newSpectrum.fluxes_normed[index].toFixed(3)}
          <br>Telescope: ${newSpectrum.telescope_name}
          <br>Instrument: ${newSpectrum.instrument_name}
          <br>Observed at (UTC): ${newSpectrum.observed_at}
          <br>PI: ${newSpectrum.pi || ""}
          <br>Origin: ${newSpectrum.origin || ""}
          `,
      );

      stats[spectrum.type].wavelength.min = Math.min(
        stats[spectrum.type].wavelength.min,
        Math.min(...newSpectrum.wavelengths),
      );
      stats[spectrum.type].wavelength.max = Math.max(
        stats[spectrum.type].wavelength.max,
        Math.max(...newSpectrum.wavelengths),
      );

      // it happens that some spectra have a few ridiculously large flux peaks, and that messes up the plot
      // the problem here is that we use the max of the fluxes to set the range of the y axis
      // so when a spectrum's max value is > 10 times the median or the mean,
      // we'll use the upper fence of the interquartile range to set the max flux
      const medianFlux = median(newSpectrum.fluxes_normed);
      const meanFlux = mean(newSpectrum.fluxes_normed);
      const maxFlux = Math.max(...newSpectrum.fluxes_normed);

      if (maxFlux > 10 * medianFlux || maxFlux > 10 * meanFlux) {
        const sortedFluxes = [...newSpectrum.fluxes_normed].sort(
          (a, b) => a - b,
        );
        // set negative fluxes to 0
        sortedFluxes.forEach((flux, index) => {
          if (flux < 0) {
            sortedFluxes[index] = 0;
          }
        });
        const q1 = sortedFluxes[Math.floor(sortedFluxes.length * 0.25)];
        const q3 = sortedFluxes[Math.floor(sortedFluxes.length * 0.75)];
        const iqr = q3 - q1;
        const upperFence = q3 + 1.5 * iqr;
        stats[spectrum.type].flux.max = Math.max(
          stats[spectrum.type].flux.max,
          upperFence,
        );
      } else {
        stats[spectrum.type].flux.max = Math.max(
          stats[spectrum.type].flux.max,
          maxFlux,
        );
      }
      // for the lines we show on top of the plot, we want to use the max flux of all spectra
      stats[spectrum.type].flux.maxLines = Math.max(
        stats[spectrum.type].flux.maxLines,
        maxFlux,
      );

      return newSpectrum;
    });

    spectrumTypes.forEach((type) => {
      stats[type].wavelength.range = [
        stats[type].wavelength.min - 100,
        stats[type].wavelength.max + 100,
      ];
      stats[type].flux.range = [0, stats[type].flux.max * 1.05];
    });

    return [newSpectra, stats];
  };

  const createTraces = (
    spectraData,
    spectrumTypes,
    tabValue,
    smoothingValue = 0,
  ) => {
    // for now (testing), we just grab the first spectrum

    if (spectraData !== null && specStats !== null) {
      const spectraFiltered = spectraData.filter((spectrum) => {
        if (spectrum.type === spectrumTypes[tabValue]) {
          return true;
        }
        return false;
      });

      const traces = spectraFiltered.map((spectrum, index) => {
        const name = `${spectrum.instrument_name}/${
          spectrum.observed_at.split("T")[0]
        }`;
        const trace = {
          mode: "lines",
          type: "scatter",
          dataType: "Spectrum",
          x: spectrum.wavelengths,
          y:
            smoothingValue === 0
              ? spectrum.fluxes_normed
              : smoothing_func([...spectrum.fluxes_normed], smoothingValue),
          text: spectrum.text,
          name,
          legendgroup: `${spectrum.instrument_name}/${spectrum.observed_at}`,
          line: {
            shape: "hvh",
            width: 0.8,
            color: hsl(0, spectraFiltered.length - 1, index),
          },
          hoverlabel: {
            bgcolor: "white",
            font: { size: 14 },
            align: "left",
          },
          visible: true,
          hovertemplate: "%{text}<extra></extra>",
        };

        return trace;
      });

      // reverse the order to have most recent spectra on top
      traces.reverse();

      const secondaryAxisX = {
        x: [
          specStats[spectrumTypes[tabValue]].wavelength.min /
            (1 + redshift || 0),
          specStats[spectrumTypes[tabValue]].wavelength.max /
            (1 + redshift || 0),
        ],
        y: [
          specStats[spectrumTypes[tabValue]].flux.min,
          specStats[spectrumTypes[tabValue]].flux.max,
        ],
        mode: "markers",
        type: "scatter",
        name: "secondaryAxisX",
        dataType: "secondaryAxisX",
        legendgroup: "secondaryAxisX",
        marker: {
          line: {
            width: 1,
          },
          opacity: 0,
        },
        visible: true,
        showlegend: false,
        xaxis: "x2",
        hoverinfo: "skip",
      };
      return traces.concat([secondaryAxisX]);
    }
    return [];
  };

  const createLayouts = (spectrumType, specStats_value, redshift_value) => {
    const newLayouts = {
      xaxis: {
        title: "Wavelength (Å)",
        side: "bottom",
        range: [...specStats_value[spectrumType].wavelength.range],
        tickformat: ".6~f",
        ...BASE_LAYOUT,
      },
      yaxis: {
        title: "Flux",
        side: "left",
        range: [...specStats_value[spectrumType].flux.range],
        ...BASE_LAYOUT,
      },
      xaxis2: {
        title: "Rest Wavelength (Å)",
        side: "top",
        overlaying: "x",
        showgrid: false,
        range: specStats_value[spectrumType].wavelength.range.map(
          (w) => w / (1 + (redshift_value || 0)),
        ),
        tickformat: ".6~f",
        ...BASE_LAYOUT,
      },
    };

    return newLayouts;
  };

  useEffect(() => {
    const spectrumTypes = findTypes(spectra);
    setTypes(spectrumTypes);
    const [newSpectra, newSpecStats] = prepareSpectra(spectra, spectrumTypes);
    setSpecStats(newSpecStats);
    setData(newSpectra);
    const traces = createTraces(newSpectra, spectrumTypes, 0, smoothingInput);
    setPlotData(traces);
  }, [spectra]);

  useEffect(() => {
    if (data !== null && types?.length > 0 && specStats !== null) {
      if (!layoutReset) {
        const traces = createTraces(data, types, tabIndex, smoothingInput);
        setPlotData(traces);
      }

      const newLayouts = createLayouts(types[tabIndex], specStats, redshift);
      setLayouts(newLayouts);
      if (layoutReset) {
        setLayoutReset(false);
      }
    }
  }, [
    data,
    types,
    tabIndex,
    specStats,
    layoutReset,
    tabIndex,
    redshift,
    smoothingInput,
  ]);

  const handleChangeTab = (event, newValue) => {
    setTabIndex(newValue);
  };

  const lineTraces = selectedLines
    .map((line_name) => {
      const line = LINES.concat(userCustomLines).find(
        (l) => l.name === line_name,
      );
      return line.x.map((x) => {
        const shiftedX =
          (x * (1 + parseFloat(redshiftInput, 10))) /
          (1 + parseFloat(vExpInput, 10) / C);
        return {
          type: "scatter",
          mode: "lines",
          dataType: "spectraLine",
          x: [...Array(100).keys()].map((i) => shiftedX), // eslint-disable-line no-unused-vars
          y: [...Array(100).keys()].map(
            (i) =>
              (specStats[types[tabIndex]].flux.maxLines * 1.05 || 1.05) *
              (i / 99),
          ),
          line: {
            color: line.color,
            width: 1,
          },
          hovertemplate: `Name: ${line.name}<br>Wavelength: ${x.toFixed(
            3,
          )}<extra></extra>`,
          name: line.name,
          legendgroup: line.name,
          showlegend: false,
          visible: true,
        };
      });
    })
    .flat()
    .concat(
      customWavelengthInput > 0
        ? [
            {
              type: "scatter",
              mode: "lines",
              dataType: "spectraLine",
              x: [...Array(100).keys()].map(
                (
                  i, // eslint-disable-line no-unused-vars
                ) =>
                  (parseFloat(customWavelengthInput, 10) *
                    (1 + parseFloat(redshiftInput, 10))) /
                  (1 + parseFloat(vExpInput, 10) / C),
              ),
              y: [...Array(100).keys()].map(
                (i) =>
                  (specStats[types[tabIndex]].flux.maxLines * 1.05 || 1.05) *
                  (i / 99),
              ),
              line: {
                color: "#000000",
                width: 1,
              },
              hovertemplate: `Name: Custom Wavelength<br>Wavelength: ${parseFloat(
                customWavelengthInput,
                10,
              ).toFixed(3)}<extra></extra>`,
              name: "Custom Wavelength",
              legendgroup: "Custom Wavelength",
              showlegend: false,
              visible: true,
            },
          ]
        : [],
    );

  return (
    <div style={{ width: "100%", height: "100%" }}>
      {types?.length > 0 && (
        <Tabs
          value={tabIndex}
          onChange={handleChangeTab}
          aria-label="gcn_tabs"
          variant="scrollable"
          xs={12}
          sx={{
            display: {
              maxWidth: "95vw",
              width: "100&",
              "& > button": { lineHeight: "1.5rem" },
            },
          }}
        >
          {types.map((type) => (
            <Tab label={type} key={type} />
          ))}
        </Tabs>
      )}
      <div
        style={{
          width: "100%",
          height: plotStyle?.height || "55vh",
          overflowX: "scroll",
        }}
      >
        <Plot
          data={(plotData || []).concat(lineTraces || [])}
          layout={{
            ...layouts,
            legend: {
              orientation: mode === "desktop" ? "v" : "h",
              yanchor: "top",
              y: mode === "desktop" ? 1 : -0.3,
              x: mode === "desktop" ? 1.02 : 0,
              traceorder: "reversed",
            },
            showlegend: true,
            autosize: true,
            automargin: true,
          }}
          config={{
            displaylogo: false,
            // the native autoScale2d and resetScale2d buttons are not working
            // as they are not resetting to the specified ranges
            // so, we remove them and add our own
            modeBarButtonsToRemove: [
              "autoScale2d",
              "resetScale2d",
              "select2d",
              "lasso2d",
            ],
            modeBarButtonsToAdd: [
              {
                name: "Reset",
                icon: Plotly.Icons.home,
                click: () => {
                  setLayoutReset(true);
                },
              },
            ],
          }}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
          onDoubleClick={() => setLayoutReset(true)}
          onLegendDoubleClick={(e) => {
            // e contains a curveNumber and a data object (plotting data)
            // we customize the legend double click behavior
            const visibleTraces = e.data.filter(
              (trace) =>
                trace.dataType === "Spectrum" && trace.visible === true,
            ).length;
            const visibleTraceIndex = e.data.findIndex(
              (trace) =>
                trace.dataType === "Spectrum" && trace.visible === true,
            );
            e.data.forEach((trace, index) => {
              if (
                ["secondaryAxisX", "spectraLine"].includes(trace.name) ||
                index === e.curveNumber
              ) {
                // if its a marker or secondary axis, always visible
                trace.visible = true;
              } else if (
                (visibleTraces === 1 && e.curveNumber === visibleTraceIndex) ||
                visibleTraces === 0
              ) {
                // if we already isolated a single trace and we double click on it, or if there are no traces visible, show all
                trace.visible = true;
              } else {
                // otherwise, hide all
                trace.visible = "legendonly";
              }
            });
            setPlotData(e.data);
            return false;
          }}
        />
      </div>
      <div
        style={{
          display: "grid",
          gridAutoFlow: "row",
          gridTemplateColumns: "repeat(auto-fit, minmax(5rem, auto))",
          gap: "0.5rem",
          width: "100%",
          padding: "0.5rem",
        }}
      >
        {/* we want to display a grid with buttons to toggle each of the lines */}
        {/* the buttons should have a rectangle of the color of the lines, and then the button itself with the name of the line */}
        {LINES.concat(userCustomLines).map((line) => (
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "flex-start",
              alignItems: "center",
              width: "fit-content",
              gridColumn: line.name.length > 8 ? "span 2" : "span 1",
            }}
            key={line.name}
          >
            <div
              style={{
                width: "0.6rem",
                height: "1.4rem",
                backgroundColor: line.color,
                marginRight: "0.5rem",
              }}
            />
            <Button
              key={line.wavelength}
              onClick={() => {
                if (selectedLines.includes(line.name)) {
                  setSelectedLines(
                    selectedLines.filter((l) => l !== line.name),
                  );
                } else {
                  setSelectedLines([...selectedLines, line.name]);
                }
              }}
              variant="contained"
              secondary
              size="small"
              style={{
                whiteSpace: "nowrap",
                maxHeight: "1.4rem",
                backgroundColor: selectedLines.includes(line.name)
                  ? line.color
                  : "#ffffff",
                color: selectedLines.includes(line.name)
                  ? "#ffffff"
                  : "#000000",
              }}
            >
              {line.name}
            </Button>
          </div>
        ))}
      </div>
      <div
        style={{
          display: "grid",
          gridAutoFlow: "row",
          // we want to display a grid with divs that contain a slider and an input
          // each of the columns should be 12rem wide, and we want to have as many columns as possible
          gridTemplateColumns: "repeat(auto-fit, minmax(16rem, 1fr))",
          rowGap: "0.5rem",
          columnGap: "2rem",
          width: "100%",
          padding: "0.5rem",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            alignItems: "left",
            gap: 0,
            width: "100%",
            margin: "0.5rem",
            marginBottom: 0,
          }}
        >
          <Typography id="input-slider">Velocity Expansion (km/s)</Typography>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "flex-start",
              alignItems: "center",
              gap: "1rem",
              width: "100%",
            }}
          >
            <Slider
              value={vExpInput}
              onChange={(e, newValue) => setVExpInput(newValue)}
              aria-labelledby="input-slider"
              valueLabelDisplay="auto"
              step={1}
              min={0}
              max={30000}
            />
            <TextField
              value={vExpInput}
              onChange={(e) => setVExpInput(e.target.value)}
              margin="dense"
              type="number"
              inputProps={{
                step: 1,
                min: 0,
                max: 30000,
                "aria-labelledby": "input-slider",
              }}
              style={{ width: "8.5rem" }}
              size="small"
            />
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            alignItems: "left",
            gap: 0,
            width: "100%",
            margin: "0.5rem",
            marginBottom: 0,
          }}
        >
          <Typography id="input-slider">Redshift</Typography>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "flex-start",
              alignItems: "center",
              gap: "1rem",
              width: "100%",
            }}
          >
            <Slider
              value={redshiftInput}
              onChange={(e, newValue) => setRedshiftInput(newValue)}
              aria-labelledby="input-slider"
              valueLabelDisplay="auto"
              step={0.0001}
              min={0}
              max={3}
            />
            <TextField
              value={redshiftInput}
              onChange={(e) => setRedshiftInput(e.target.value)}
              margin="dense"
              type="number"
              inputProps={{
                step: 0.0001,
                min: 0,
                max: 3.0,
                "aria-labelledby": "input-slider",
              }}
              style={{ width: "8.5rem" }}
              size="small"
            />
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            alignItems: "left",
            gap: 0,
            width: "100%",
            margin: "0.5rem",
            marginBottom: 0,
          }}
        >
          <Typography id="input-slider">Smoothing</Typography>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "flex-start",
              alignItems: "center",
              gap: "1rem",
              width: "100%",
            }}
          >
            <Slider
              value={smoothingInput}
              onChange={(e, newValue) => setSmoothingInput(newValue)}
              aria-labelledby="input-slider"
              valueLabelDisplay="auto"
              step={1}
              min={0}
              max={100}
            />
            <TextField
              value={smoothingInput}
              onChange={(e) => setSmoothingInput(e.target.value)}
              margin="dense"
              type="number"
              inputProps={{
                step: 1,
                min: 0,
                max: 100,
                "aria-labelledby": "input-slider",
              }}
              style={{ width: "8.5rem" }}
              size="small"
            />
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            alignItems: "left",
            gap: 0,
            width: "100%",
            margin: "0.5rem",
            marginBottom: 0,
          }}
        >
          <Typography id="input-slider">Custom Wavelength</Typography>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "flex-start",
              alignItems: "center",
              gap: "1rem",
              width: "100%",
            }}
          >
            <Slider
              value={customWavelengthInput}
              onChange={(e, newValue) => setCustomWavelengthInput(newValue)}
              aria-labelledby="input-slider"
              valueLabelDisplay="auto"
              step={1}
              min={0}
              max={50000}
            />
            <TextField
              value={customWavelengthInput}
              onChange={(e) => setCustomWavelengthInput(e.target.value)}
              margin="dense"
              type="number"
              inputProps={{
                step: 1,
                min: 0,
                max: 50000,
                "aria-labelledby": "input-slider",
              }}
              style={{ width: "8.5rem" }}
              size="small"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

SpectraPlot.propTypes = {
  spectra: PropTypes.arrayOf(
    PropTypes.shape({
      observed_at: PropTypes.string,
      instrument_name: PropTypes.string,
      wavelengths: PropTypes.arrayOf(PropTypes.number),
      fluxes: PropTypes.arrayOf(PropTypes.number),
    }),
  ).isRequired,
  redshift: PropTypes.number,
  mode: PropTypes.string,
  plotStyle: PropTypes.shape({
    height: PropTypes.string,
  }),
};

SpectraPlot.defaultProps = {
  redshift: 0,
  mode: "desktop",
  plotStyle: {
    height: "55vh",
  },
};

export default SpectraPlot;
