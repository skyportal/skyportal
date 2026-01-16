import React, {
  useEffect,
  useState,
  useMemo,
  useRef,
  useCallback,
} from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import Slider from "@mui/material/Slider";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import { makeStyles } from "@mui/styles";

import Button from "../Button";

import {
  BASE_LAYOUT,
  C,
  colorScaleRainbow,
  LINES,
  mean,
  median,
  smoothing_func,
} from "../../utils";

const Plot = createPlotlyComponent(Plotly);

const useStyles = makeStyles(() => ({
  gridContainerLines: {
    display: "grid",
    gridAutoFlow: "row",
    gridTemplateColumns: "repeat(auto-fit, minmax(5rem, auto))",
    gap: "0.5rem",
    width: "100%",
    padding: "0.5rem 1rem 0 1rem",
  },
  gridItemLines: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-start",
    alignItems: "center",
    width: "fit-content",
  },
  gridContainer: {
    display: "grid",
    gridAutoFlow: "row",
    gridTemplateColumns: "repeat(auto-fit, minmax(16rem, 1fr))",
    rowGap: "0.5rem",
    columnGap: "2rem",
    width: "100%",
    padding: "1rem 1rem 0 1rem",
  },
  gridItem: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "flex-start",
    alignItems: "left",
    gap: 0,
    width: "100%",
  },
  sliderContainer: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-start",
    alignItems: "center",
    gap: "1rem",
    width: "100%",
    paddingLeft: "0.5rem",
    "& > .MuiTextField-root": {
      width: "8.5rem",
      marginTop: 0,
      marginBottom: 0,
    },
  },
  lineColor: {
    width: "0.8rem",
    height: "1.4rem",
    borderRadius: "0.25rem 0 0 0.25rem",
    marginRight: "-0.25rem",
    zIndex: 1,
  },
}));

const SpectraPlot = ({ spectra, redshift, mode, plotStyle }) => {
  const classes = useStyles();
  const plotRef = useRef(null);
  const singleClickTimerRef = useRef(null);
  const [data, setData] = useState(null);
  const [plotData, setPlotData] = useState(null);

  const [selectedLines, setSelectedLines] = useState([]);

  const [vExpInput, setVExpInput] = useState(0);
  const [redshiftInput, setRedshiftInput] = useState(redshift || 0);
  const [smoothingInput, setSmoothingInput] = useState(0);
  const [customWavelengthInput, setCustomWavelengthInput] = useState(0);

  const [specStats, setSpecStats] = useState(null);

  const [layoutReset, setLayoutReset] = useState(1);
  const lastKnownXRangeRef = useRef(null);
  const isSyncingRef = useRef(false);

  const { preferences } = useSelector((state) => state.profile);

  // Memoize user custom lines to avoid recreating on every render
  const userCustomLines = useMemo(() => {
    return Object.entries(preferences.spectroscopyButtons || {}).map(
      ([name, { color, wavelengths }]) => ({
        name,
        color,
        x: wavelengths,
      }),
    );
  }, [preferences?.spectroscopyButtons]);

  // Memoize the combined lines array to avoid recreating on every render
  const allLines = useMemo(
    () => LINES.concat(userCustomLines),
    [userCustomLines],
  );

  const [types, setTypes] = useState([]);
  const [tabIndex, setTabIndex] = useState(0);

  // Memoize helper functions that don't depend on state
  const findTypes = useCallback((spectraData) => {
    const spectrumTypes = new Set();
    spectraData.forEach((spectrum) => {
      if (spectrum.type && spectrum.type !== "") {
        spectrumTypes.add(spectrum.type);
      }
    });
    // Sort by alphabetical order descending
    return Array.from(spectrumTypes).sort((a, b) => (a < b ? 1 : -1));
  }, []);

  const prepareSpectra = useCallback((spectraData, spectrumTypes) => {
    const stats = {};
    spectrumTypes.forEach((type) => {
      stats[type] = {
        flux: { min: 0, max: 0, maxLines: 0, range: [0, 1] },
        wavelength: { min: 100000, max: 0, range: [0, 100000] },
      };
    });

    const newSpectra = spectraData
      .map((spectrum) => {
        let normfac = Math.abs(median(spectrum.fluxes));
        normfac = normfac !== 0.0 ? normfac : 1e-20;

        const fluxes_normed = spectrum.fluxes.map((flux) => flux / normfac);

        // Filter out NaN values efficiently
        const validIndices = [];
        for (let i = 0; i < fluxes_normed.length; i++) {
          if (
            fluxes_normed[i] != null &&
            spectrum.wavelengths[i] != null &&
            !Number.isNaN(fluxes_normed[i]) &&
            !Number.isNaN(spectrum.wavelengths[i])
          ) {
            validIndices.push(i);
          }
        }

        if (validIndices.length === 0) return null;

        const wavelengths = validIndices.map((i) => spectrum.wavelengths[i]);
        const fluxes = validIndices.map((i) => fluxes_normed[i]);

        // Pre-compute hover text
        const text = wavelengths.map(
          (wavelength, index) =>
            `Wavelength: ${wavelength?.toFixed(3)}<br>Flux: ${fluxes[
              index
            ]?.toFixed(3)}<br>Telescope: ${
              spectrum.telescope_name
            }<br>Instrument: ${
              spectrum.instrument_name
            }<br>Observed at (UTC): ${spectrum.observed_at}<br>PI: ${
              spectrum.pi || ""
            }<br>Origin: ${spectrum.origin || ""}`,
        );

        // Update stats
        const minWavelength = Math.min(...wavelengths);
        const maxWavelength = Math.max(...wavelengths);
        stats[spectrum.type].wavelength.min = Math.min(
          stats[spectrum.type].wavelength.min,
          minWavelength,
        );
        stats[spectrum.type].wavelength.max = Math.max(
          stats[spectrum.type].wavelength.max,
          maxWavelength,
        );

        // Handle outlier flux peaks
        const medianFlux = median(fluxes);
        const meanFlux = mean(fluxes);
        const maxFlux = Math.max(...fluxes);

        if (maxFlux > 10 * medianFlux || maxFlux > 10 * meanFlux) {
          const sortedFluxes = fluxes
            .filter((f) => f >= 0)
            .sort((a, b) => a - b);
          const q1 = sortedFluxes[Math.floor(sortedFluxes.length * 0.25)];
          const q3 = sortedFluxes[Math.floor(sortedFluxes.length * 0.75)];
          const upperFence = q3 + 1.5 * (q3 - q1);
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

        stats[spectrum.type].flux.maxLines = Math.max(
          stats[spectrum.type].flux.maxLines,
          maxFlux,
        );

        return {
          ...spectrum,
          fluxes_normed: fluxes,
          wavelengths,
          text,
        };
      })
      .filter(Boolean);

    // Finalize stats ranges
    spectrumTypes.forEach((type) => {
      stats[type].wavelength.range = [
        stats[type].wavelength.min - 100,
        stats[type].wavelength.max + 100,
      ];
      stats[type].flux.range = [0, stats[type].flux.max * 1.05];
    });

    return [newSpectra, stats];
  }, []);

  const createTraces = (
    spectraData,
    spectrumTypes,
    tabValue,
    smoothingValue = 0,
    existingPlotData,
  ) => {
    if (spectraData !== null && specStats !== null) {
      const spectraFiltered = spectraData.filter(
        (spectrum) => spectrum.type === spectrumTypes[tabValue],
      );

      const existingTracesVisibilities = {};
      if (existingPlotData) {
        existingPlotData.forEach((trace) => {
          if (trace.dataType === "Spectrum") {
            existingTracesVisibilities[trace.spectrumId] = trace.visible;
          }
        });
      }

      // Helper to format date once per spectrum
      const formatTraceName = (spectrum) => {
        const date = spectrum.observed_at.split("T")[0].split("-");
        return `${spectrum.instrument_name} (${date[1]}/${date[2].slice(
          -2,
        )}/${date[0].slice(-2)})`;
      };

      const traces = spectraFiltered.map((spectrum, index) => {
        const name = formatTraceName(spectrum);
        const existingTraceVisibility = existingPlotData
          ? existingTracesVisibilities[spectrum.id]
          : true;

        const trace = {
          mode: "lines",
          type: "scatter",
          dataType: "Spectrum",
          spectrumId: spectrum.id,
          x: spectrum.wavelengths,
          y:
            smoothingValue === 0
              ? spectrum.fluxes_normed
              : smoothing_func([...spectrum.fluxes_normed], smoothingValue),
          text: spectrum.text,
          name,
          legendgroup: `${spectrum.id}`,
          line: {
            shape: "hvh",
            width: 0.85,
            color: colorScaleRainbow(index, spectraFiltered.length - 1),
          },
          hoverlabel: {
            bgcolor: "white",
            font: { size: 14 },
            align: "left",
          },
          visible: existingTraceVisibility,
          hovertemplate: "%{text}<extra></extra>",
        };

        return trace;
      });

      // Always create the original (unsmoothed) traces in the background
      // They start as invisible and only show when smoothing > 0
      const tracesOriginal = spectraFiltered.map((spectrum) => {
        const name = formatTraceName(spectrum);
        const existingTraceVisibility = existingPlotData
          ? existingTracesVisibilities[spectrum.id]
          : true;

        const trace = {
          mode: "lines",
          type: "scatter",
          dataType: "SpectrumNoSmooth",
          spectrumId: spectrum.id,
          x: spectrum.wavelengths,
          y: spectrum.fluxes_normed,
          name,
          legendgroup: `${spectrum.id}`,
          line: {
            shape: "hvh",
            width: 0.85,
            color: `rgba(100, 100, 100, 0.2)`,
          },
          hoverinfo: "skip",
          visible: smoothingValue > 0 ? existingTraceVisibility : false,
          showlegend: false,
        };
        return trace;
      });

      const allTraces = [...traces, ...tracesOriginal];

      const redshift_value = parseFloat(redshiftInput, 10) || 0;
      const denom = 1 + redshift_value;
      const secondaryAxisX = {
        x: [
          specStats[spectrumTypes[tabValue]].wavelength.min / denom,
          specStats[spectrumTypes[tabValue]].wavelength.max / denom,
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
      return [...allTraces, secondaryAxisX];
    }
    return [];
  };

  const createLineTraces = () => {
    // Pre-create the y-axis array once instead of recreating it for each line
    const maxFlux = specStats[types[tabIndex]].flux.maxLines * 1.05 || 1.05;
    const yArray = Array.from({ length: 100 }, (_, i) => maxFlux * (i / 99));

    const lineTraces = allLines
      .map((line) => {
        const isVisible = selectedLines.includes(line.name);
        return line.x.map((x) => {
          const redshiftedX =
            line?.fixed === true
              ? x
              : x * (1 + (parseFloat(redshiftInput, 10) || 0));
          const shiftedX =
            line?.fixed === true
              ? x
              : redshiftedX / (1 + (parseFloat(vExpInput, 10) || 0) / C);
          return {
            type: "scatter",
            mode: "lines",
            dataType: "spectraLine",
            lineIdentifier: `${line.name}_${x}`, // unique identifier for this specific line
            x: Array(100).fill(shiftedX),
            y: yArray,
            line: {
              color: line.color,
              width: 1,
            },
            hovertemplate: `Name: ${line.name}<br>Rest Wavelength: ${x?.toFixed(
              3,
            )} Å<br>Wavelength: ${redshiftedX?.toFixed(3)} Å<extra></extra>`,
            name: line.name,
            legendgroup: line.name,
            showlegend: false,
            visible: isVisible,
          };
        });
      })
      .flat();

    // add a placeholder for the customWavelengthInput
    let value = parseFloat(customWavelengthInput, 10) || 0;
    const redshiftedX = value * (1 + (parseFloat(redshiftInput, 10) || 0));
    const shiftedX = redshiftedX / (1 + (parseFloat(vExpInput, 10) || 0) / C);

    lineTraces.push({
      type: "scatter",
      mode: "lines",
      dataType: "spectraLine",
      lineIdentifier: `Custom_Wavelength_${customWavelengthInput}`, // unique identifier for this specific line
      x: Array(100).fill(shiftedX),
      y: yArray,
      line: {
        color: "purple",
        width: 1,
        dash: "dot",
      },
      hovertemplate: `Name: Custom Wavelength<br>Wavelength: ${value?.toFixed(
        3,
      )} Å<br>Redshifted Wavelength: ${(
        value *
        (1 + (parseFloat(redshiftInput, 10) || 0))
      )?.toFixed(3)} Å<extra></extra>`,
      name: "Custom Wavelength",
      legendgroup: "Custom Wavelength",
      showlegend: false,
      visible: value !== 0,
    });
    return lineTraces;
  };

  useEffect(() => {
    const spectrumTypes = findTypes(spectra);
    setTypes(spectrumTypes);
    const [newSpectra, newSpecStats] = prepareSpectra(spectra, spectrumTypes);
    setSpecStats(newSpecStats);
    setData(newSpectra);
  }, [spectra, findTypes, prepareSpectra]);

  // Effect for updating spectrum traces and line traces (full recreation)
  useEffect(() => {
    if (data !== null && types?.length > 0 && specStats !== null) {
      const traces = createTraces(
        data,
        types,
        tabIndex,
        smoothingInput,
        plotData,
      );
      const lineTraces = createLineTraces();
      setPlotData([...traces, ...lineTraces]);
    }
  }, [data, types, specStats, selectedLines, tabIndex, allLines]);

  // Effect for updating only smoothing (update y-values in place)
  useEffect(() => {
    if (plotData !== null && data !== null) {
      const smoothingValue = parseFloat(smoothingInput, 10) || 0;
      const shouldSmooth = smoothingValue > 0;

      // Create a Map for O(1) spectrum lookup instead of repeated O(n) find calls
      const spectrumMap = new Map(data.map((s) => [s.id, s]));

      const updatedPlotData = plotData.map((trace) => {
        if (trace.dataType === "Spectrum") {
          const spectrum = spectrumMap.get(trace.spectrumId);
          if (spectrum) {
            return {
              ...trace,
              y: shouldSmooth
                ? smoothing_func([...spectrum.fluxes_normed], smoothingValue)
                : spectrum.fluxes_normed,
            };
          }
        } else if (trace.dataType === "SpectrumNoSmooth") {
          // Find the corresponding main spectrum trace to check visibility
          const mainTrace = plotData.find(
            (t) =>
              t.dataType === "Spectrum" && t.spectrumId === trace.spectrumId,
          );
          return {
            ...trace,
            visible:
              shouldSmooth &&
              mainTrace?.visible !== "legendonly" &&
              mainTrace?.visible !== false,
          };
        }
        return trace;
      });
      setPlotData(updatedPlotData);
    }
  }, [smoothingInput, data]);

  // Effect for updating only line positions when redshift/vExp/customWavelength changes
  useEffect(() => {
    if (plotData !== null && specStats !== null && types?.length > 0) {
      const redshift_val = parseFloat(redshiftInput, 10) || 0;
      const vExp_val = parseFloat(vExpInput, 10) || 0;

      const updatedPlotData = plotData.map((trace) => {
        if (trace.dataType !== "spectraLine") return trace;

        if (trace.name === "Custom Wavelength") {
          let value = parseFloat(customWavelengthInput, 10) || 0;
          const redshiftedX = value * (1 + redshift_val);
          const shiftedX = redshiftedX / (1 + vExp_val / C);

          return {
            ...trace,
            x: Array(100).fill(shiftedX),
            visible: value !== 0,
            hovertemplate: `Name: Custom Wavelength<br>Wavelength: ${value?.toFixed(
              3,
            )} Å<br>Redshifted Wavelength: ${(
              value *
              (1 + redshift_val)
            )?.toFixed(3)} Å<extra></extra>`,
          };
        }

        const originalLine = allLines.find((line) => trace.name === line.name);
        if (originalLine) {
          const wavelength = parseFloat(trace.lineIdentifier.split("_").pop());
          const redshiftedX =
            originalLine?.fixed === true
              ? wavelength
              : wavelength * (1 + redshift_val);
          const shiftedX =
            originalLine?.fixed === true
              ? wavelength
              : redshiftedX / (1 + vExp_val / C);

          return {
            ...trace,
            x: Array(100).fill(shiftedX),
            hovertemplate: `Name: ${
              originalLine.name
            }<br>Rest Wavelength: ${wavelength?.toFixed(
              3,
            )} Å<br>Wavelength: ${redshiftedX?.toFixed(3)} Å<extra></extra>`,
          };
        }

        return trace;
      });
      setPlotData(updatedPlotData);
    }
  }, [vExpInput, redshiftInput, customWavelengthInput, specStats, types]);

  const handleChangeTab = useCallback((event, newValue) => {
    setTabIndex(newValue);
    // Reset the layout when changing tabs to reset zoom
    setLayoutReset((prev) => prev + 1);
  }, []);

  // Memoize the line toggle handler to prevent creating new functions on each render
  const toggleLine = useCallback((lineName) => {
    setSelectedLines((prev) =>
      prev.includes(lineName)
        ? prev.filter((l) => l !== lineName)
        : [...prev, lineName],
    );
  }, []);

  // Memoize the plot layout to prevent re-renders when unrelated state changes
  // We DON'T include redshiftInput in dependencies - instead we update xaxis2 via Plotly.relayout
  // to preserve zoom state. This is intentional to avoid layout recreation on redshift changes.
  /* eslint-disable react-hooks/exhaustive-deps */
  const plotLayout = useMemo(() => {
    if (!specStats || !types[tabIndex]) {
      return {};
    }

    const spectrumType = types[tabIndex];
    const redshift_value = parseFloat(redshiftInput, 10) || 0;
    const denom = 1 + redshift_value;

    return {
      uirevision: layoutReset, // Use the number directly instead of string template
      xaxis: {
        title: { text: "Wavelength (Å)" },
        side: "bottom",
        range: [...specStats[spectrumType].wavelength.range],
        tickformat: ".6~f",
        zeroline: false,
        ...BASE_LAYOUT,
      },
      yaxis: {
        title: { text: "Flux" },
        side: "left",
        range: [...specStats[spectrumType].flux.range],
        ...BASE_LAYOUT,
      },
      xaxis2: {
        title: { text: "Rest Wavelength (Å)" },
        side: "top",
        overlaying: "x",
        showgrid: false,
        range: specStats[spectrumType].wavelength.range.map((w) => w / denom),
        tickformat: ".6~f",
        zeroline: false,
        ...BASE_LAYOUT,
      },
      legend: {
        orientation: mode === "desktop" ? "v" : "h",
        yanchor: "top",
        y: mode === "desktop" ? 1 : plotData?.length > 10 ? -0.4 : -0.3,
        x: mode === "desktop" ? 1.02 : 0,
        font: { size: 14 },
        tracegroupgap: 0,
      },
      showlegend: true,
      autosize: true,
      margin: {
        l: 70,
        r: 20,
        b: 75,
        t: 80,
        pad: 0,
      },
      shapes: [
        {
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
    };
  }, [types, tabIndex, specStats, mode, plotData?.length, layoutReset]);
  /* eslint-enable react-hooks/exhaustive-deps */

  // Use Plotly.relayout to update only the secondary axis when redshift changes
  // This avoids recreating the entire layout object and preserves zoom
  useEffect(() => {
    if (plotRef.current?.el && specStats && types[tabIndex] && plotData) {
      const redshift_value = parseFloat(redshiftInput, 10) || 0;
      const spectrumType = types[tabIndex];
      const denom = 1 + redshift_value;
      // If user is zoomed, sync x2 to the current primary x range; else use full mapped range
      const plotElement = plotRef.current.el;
      const currentXRange =
        plotElement?._fullLayout?.xaxis?.range ||
        specStats[spectrumType].wavelength.range;
      const newRange = [currentXRange[0] / denom, currentXRange[1] / denom];

      // Check that the element has been initialized by Plotly with _fullLayout
      if (plotElement._fullLayout?.xaxis2) {
        try {
          // Use Plotly.relayout to update only the secondary axis range
          const currentX2 = plotElement?._fullLayout?.xaxis2?.range;
          if (
            currentX2 &&
            currentX2[0] === newRange[0] &&
            currentX2[1] === newRange[1]
          ) {
            // already in sync; no-op
          } else {
            isSyncingRef.current = true;
            Plotly.relayout(plotElement, { "xaxis2.range": newRange })
              .catch(() => {})
              .finally(() => {
                isSyncingRef.current = false;
              });
          }
          lastKnownXRangeRef.current =
            plotElement?._fullLayout?.xaxis?.range || null;
        } catch (err) {
          // Silently catch errors during initial render
          console.warn("Plotly relayout error:", err);
        }
      }
    }
  }, [redshiftInput, specStats, types, tabIndex, plotData]);

  // Keep secondary axis in sync with primary on any zoom/pan/relayout
  const handleRelayout = useCallback(
    (e) => {
      const plotElement = plotRef.current?.el;
      if (!plotElement) return;

      if (isSyncingRef.current) return; // prevent re-entrant loops

      const redshift_value = parseFloat(redshiftInput, 10) || 0;
      const denom = 1 + redshift_value;

      // Determine the new primary x range from the event or from the layout
      let x0;
      let x1;
      if (e["xaxis.range[0]"] != null && e["xaxis.range[1]"] != null) {
        x0 = e["xaxis.range[0]"];
        x1 = e["xaxis.range[1]"];
      } else if (plotElement?._fullLayout?.xaxis?.range) {
        [x0, x1] = plotElement._fullLayout.xaxis.range;
      }

      if (x0 != null && x1 != null) {
        lastKnownXRangeRef.current = [x0, x1];
        try {
          const target = [x0 / denom, x1 / denom];
          const currentX2 = plotElement?._fullLayout?.xaxis2?.range;
          if (
            currentX2 &&
            currentX2[0] === target[0] &&
            currentX2[1] === target[1]
          ) {
            return;
          }
          isSyncingRef.current = true;
          Plotly.relayout(plotElement, {
            "xaxis2.range": target,
          })
            .catch(() => {})
            .finally(() => {
              isSyncingRef.current = false;
            });
        } catch (err) {
          console.warn("Plotly relayout sync error:", err);
        }
      }
    },
    [redshiftInput],
  );

  // After traces change (e.g., toggling lines), resync x2 to current x range
  useEffect(() => {
    const plotElement = plotRef.current?.el;
    if (!plotElement) return;
    const redshift_value = parseFloat(redshiftInput, 10) || 0;
    const denom = 1 + redshift_value;

    // Defer until after Plotly processes the new data
    const id = window.requestAnimationFrame(() => {
      const range =
        plotElement?._fullLayout?.xaxis?.range || lastKnownXRangeRef.current;
      if (range && plotElement?._fullLayout?.xaxis2) {
        try {
          const target = [range[0] / denom, range[1] / denom];
          const currentX2 = plotElement?._fullLayout?.xaxis2?.range;
          if (
            currentX2 &&
            currentX2[0] === target[0] &&
            currentX2[1] === target[1]
          ) {
            return;
          }
          isSyncingRef.current = true;
          Plotly.relayout(plotElement, {
            "xaxis2.range": target,
          })
            .catch(() => {})
            .finally(() => {
              isSyncingRef.current = false;
            });
        } catch (err) {
          // noop
        }
      }
    });
    return () => window.cancelAnimationFrame(id);
  }, [plotData, redshiftInput]);

  // Memoize the plot config to prevent re-renders
  const plotConfig = useMemo(
    () => ({
      displaylogo: false,
      // the native autoScale2d and resetScale2d buttons are not working
      // as they are not resetting to the specified ranges
      // so, we remove them and add our own
      showAxisDragHandles: false,
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
            setLayoutReset((prev) => prev + 1);
          },
        },
      ],
    }),
    [],
  );

  // Memoize event handlers to prevent re-renders
  const handleDoubleClick = useCallback(() => {
    setLayoutReset((prev) => prev + 1);
  }, []);

  const handleLegendDoubleClick = (e) => {
    // e contains a curveNumber and a data object (plotting data)
    // we customize the legend double click behavior
    const nbAvailableTraces = e.data.filter(
      (trace) => trace.dataType === "Spectrum",
    ).length;
    if (nbAvailableTraces <= 1) {
      // if there's only one trace, do nothing
      return false;
    }
    const visibleTraces = e.data.filter(
      (trace) => trace.dataType === "Spectrum" && trace.visible === true,
    ).length;
    const visibleTraceIndex = e.data.findIndex(
      (trace) => trace.dataType === "Spectrum" && trace.visible === true,
    );

    // let's create a mapper of spectrum id to main trace visibility
    let spectrumVisibilityMap = {};

    // First pass: update Spectrum traces visibility
    let newTraces = e.data.map((trace, index) => {
      if (trace.dataType !== "Spectrum") {
        return trace;
      }
      let newVisible;
      if (
        // if none are visible, show all
        visibleTraces === 0 ||
        // if one is visible and it's the clicked one, show all
        (visibleTraces === 1 && e.curveNumber === visibleTraceIndex) ||
        // otherwise (multiple visible, or one but not the clicked one),
        // then hide all but the clicked one
        index === e.curveNumber
      ) {
        // show all
        newVisible = true;
      } else {
        // hide all others
        newVisible = "legendonly";
      }
      spectrumVisibilityMap[trace.spectrumId] = newVisible;
      return { ...trace, visible: newVisible };
    });

    // Second pass: update SpectrumNoSmooth traces based on updated Spectrum traces
    // (we only need to perform an update here IF smoothing is active)
    const smoothingValue = parseFloat(smoothingInput, 10) || 0;
    if (smoothingValue > 0) {
      newTraces.forEach((trace) => {
        if (trace.dataType === "SpectrumNoSmooth") {
          const newVisible =
            spectrumVisibilityMap[trace.spectrumId] !== "legendonly" &&
            spectrumVisibilityMap[trace.spectrumId] !== false;
          trace.visible = newVisible;
        }
      });
    }
    setPlotData(newTraces);
    // we prevent the default behavior by returning false (otherwise would reset layout)
    return false;
  };

  const handleLegendSingleClick = (e) => {
    // reverse the visibility of the clicked trace
    let spectrumId = e.data[e.curveNumber].spectrumId;
    let newVisible;
    let newTraces = e.data.map((trace, index) => {
      if (index === e.curveNumber) {
        // if its true, set to legend only. if legendonly, set to false. if false, set to true.
        if (trace.visible === true) {
          newVisible = "legendonly";
        } else {
          newVisible = true;
        }
        return { ...trace, visible: newVisible };
      }
      return trace;
    });

    // if smoothing is active, we need to update the associated unsmoothed traces as well
    const smoothingValue = parseFloat(smoothingInput, 10) || 0;
    if (smoothingValue > 0) {
      newTraces.forEach((trace) => {
        if (
          trace.dataType === "SpectrumNoSmooth" &&
          trace.spectrumId === spectrumId
        ) {
          // keep the unsmoothed version in sync with the main trace
          trace.visible = newVisible === true;
        }
      });
    }
    setPlotData(newTraces);
    // prevent default behavior
    return false;
  };

  return (
    <div style={{ width: "100%", height: "100%" }} id="spectroscopy-plot">
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
              width: "100%",
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
          ref={plotRef}
          data={plotData || []}
          layout={plotLayout}
          config={plotConfig}
          revision={layoutReset}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
          onDoubleClick={handleDoubleClick}
          onLegendDoubleClick={handleLegendDoubleClick}
          onLegendClick={handleLegendSingleClick}
          onRelayout={handleRelayout}
        />
      </div>
      <div className={classes.gridContainerLines}>
        {/* we want to display a grid with buttons to toggle each of the lines */}
        {/* the buttons should have a rectangle of the color of the lines, and then the button itself with the name of the line */}
        {allLines.map((line) => (
          <div
            className={classes.gridItemLines}
            style={{ gridColumn: line.name.length > 8 ? "span 2" : "span 1" }}
            key={line.name}
          >
            <div
              className={classes.lineColor}
              style={{ backgroundColor: line.color }}
            />
            <Button
              key={line.wavelength}
              onClick={(e) => {
                e.stopPropagation();
                e.preventDefault();
                toggleLine(line.name);
              }}
              variant="contained"
              secondary
              size="small"
              style={{
                textTransform: "none",
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
      <div className={classes.gridContainer}>
        <div className={classes.gridItem}>
          <Typography id="input-slider">Velocity Expansion (km/s)</Typography>
          <div className={classes.sliderContainer}>
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
              size="small"
            />
          </div>
        </div>
        <div className={classes.gridItem}>
          <Typography id="input-slider">Redshift</Typography>
          <div className={classes.sliderContainer}>
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
              size="small"
            />
          </div>
        </div>
        <div className={classes.gridItem}>
          <Typography id="input-slider">Smoothing</Typography>
          <div className={classes.sliderContainer}>
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
              size="small"
            />
          </div>
        </div>
        <div className={classes.gridItem}>
          <Typography id="input-slider">Custom Wavelength</Typography>
          <div className={classes.sliderContainer}>
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
