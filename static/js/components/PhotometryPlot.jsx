import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import Slider from "@mui/material/Slider";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import SaveAsIcon from "@mui/icons-material/SaveAs";
import IconButton from "@mui/material/IconButton";
import Switch from "@mui/material/Switch";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import makeStyles from "@mui/styles/makeStyles";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";

import { addAnnotation } from "../ducks/source";
import { BASE_LAYOUT, PHOT_ZP, smoothing_func, mjdnow, rgba } from "../utils";

const Plot = createPlotlyComponent(Plotly);

const useStyles = makeStyles(() => ({
  gridContainer: {
    display: "grid",
    gridAutoFlow: "row",
    gridTemplateColumns: "repeat(3, 1fr)",
    rowGap: "0.5rem",
    columnGap: "2rem",
    width: "100%",
    padding: "0.5rem 1rem 0 1rem",
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
      width: "7rem",
      marginTop: 0,
      marginBottom: 0,
    },
  },
  switchContainer: {
    minHeight: "2rem",
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-start",
    alignItems: "center",
    gap: "0.5rem",
    width: "100%",
  },
  doubleSwitch: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    gap: "0.5rem",
  },
}));

const PeriodAnnotationDialog = ({ obj_id, period }) => {
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);

  const [dialogOpen, setDialogOpen] = useState(false);
  // to save a period as an annotation, we'll need the user to provide an origin
  // and also to pick groups to save the annotation to
  const schema = {
    type: "object",
    properties: {
      period: { type: "number", title: "Period", default: period },
      origin: { type: "string", title: "Origin" },
      groupIDs: {
        type: "array",
        items: {
          type: "string",
          enum: groups?.map((group) => group.id.toString()),
          enumNames: groups?.map((group) => group.name),
        },
        uniqueItems: true,
      },
    },
    required: ["period", "origin", "groupIDs"],
  };

  const validate = (formData, errors) => {
    if (formData.period <= 0) {
      errors.period.addError("Period must be greater than 0");
    }
    if (formData.origin?.replaceAll(" ", "") === "") {
      errors.origin.addError("Origin must not be empty");
    }
    if (formData.groupIDs?.length === 0) {
      errors.groupIDs.addError("Must select at least one group");
    }
    return errors;
  };

  const submitPeriodAnnotation = async ({ formData }) => {
    const periodData = {
      obj_id,
      origin: formData.origin,
      data: {
        period: formData.period,
      },
      groups: formData.groupIDs,
    };
    dispatch(addAnnotation(obj_id, periodData)).then((result) => {
      if (result.status === "success") {
        setDialogOpen(false);
        dispatch(showNotification("Period saved as annotation"));
      } else {
        dispatch(showNotification("Failed to save period as annotation"));
      }
    });
  };

  return (
    <>
      <Tooltip title="Save period as annotation">
        <IconButton onClick={() => setDialogOpen(true)} size="small">
          <SaveAsIcon />
        </IconButton>
      </Tooltip>

      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        style={{ position: "fixed" }}
        maxWidth="lg"
      >
        <DialogTitle>Save Period as Annotation</DialogTitle>
        <DialogContent>
          <Form
            schema={schema}
            validator={validator}
            customValidate={validate}
            onSubmit={submitPeriodAnnotation}
          />
        </DialogContent>
      </Dialog>
    </>
  );
};

PeriodAnnotationDialog.propTypes = {
  obj_id: PropTypes.string.isRequired,
  period: PropTypes.number.isRequired,
};

const PhotometryPlot = ({
  obj_id,
  dm,
  photometry,
  annotations,
  spectra,
  gcn_events,
  mode,
  plotStyle,
}) => {
  const classes = useStyles();
  const [data, setData] = useState(null);
  const [plotData, setPlotData] = useState(null);

  const [tabIndex, setTabIndex] = useState(0);
  const [markerSize, setMarkerSize] = useState(6);

  const [period, setPeriod] = useState(1);
  const [phase, setPhase] = useState(2);
  const [smoothing, setSmoothing] = useState(0);

  const [photStats, setPhotStats] = useState(null);
  const [layouts, setLayouts] = useState({});

  const filter2color = useSelector(
    (state) => state.config.bandpassesColors || {},
  );

  const [layoutReset, setLayoutReset] = useState(false);

  const [showNonDetections, setShowNonDetections] = useState(true);

  const preparePhotometry = (photometryData) => {
    const stats = {
      mag: {
        min: 100,
        max: 0,
        range: [100, 0],
      },
      flux: {
        min: 100,
        max: 0,
        range: [0, 100],
      },
      days_ago: {
        min: 100000,
        max: 0,
        extra: [100000, 0],
      },
      mjd: {
        min: 100000,
        max: 0,
        extra: [100000, 0],
      },
    };

    const now = mjdnow();

    const newPhotometryData = photometryData.map((point) => {
      const newPoint = { ...point };
      newPoint.days_ago = now - newPoint.mjd;
      if (newPoint.mag !== null) {
        newPoint.flux = 10 ** (-0.4 * (newPoint.mag - PHOT_ZP));
        newPoint.fluxerr =
          (newPoint.magerr / (2.5 / Math.log(10))) * newPoint.flux;
        newPoint.snr = newPoint.flux / newPoint.fluxerr;
        if (newPoint.snr < 0) {
          newPoint.snr = null;
        }
      } else {
        newPoint.flux = 10 ** (-0.4 * (newPoint.limiting_mag - PHOT_ZP));
        newPoint.fluxerr = 0;
        newPoint.snr = null;
      }
      newPoint.streams = (newPoint.streams || [])
        .map((stream) => stream?.name || stream)
        .filter((value, index, self) => self.indexOf(value) === index);
      // also, we only want to keep the stream names that are not substrings of others
      // for example, if we have a stream called 'ZTF Public', we don't want to keep
      // 'ZTF Public+Partnership' because it's a substring of 'ZTF Public'.
      newPoint.streams = newPoint.streams.filter((name) => {
        const names = newPoint.streams.filter(
          (c) => c !== name && c.includes(name),
        );
        return names.length === 0;
      });
      newPoint.text = `MJD: ${newPoint.mjd.toFixed(6)}`;
      if (newPoint.mag) {
        newPoint.text += `
        <br>Mag: ${newPoint.mag ? newPoint.mag.toFixed(3) : "NaN"}
        <br>Magerr: ${newPoint.magerr ? newPoint.magerr.toFixed(3) : "NaN"}
        `;
      }
      newPoint.text += `
        <br>Limiting Mag: ${
          newPoint.limiting_mag ? newPoint.limiting_mag.toFixed(3) : "NaN"
        }
        <br>Flux: ${newPoint.flux ? newPoint.flux.toFixed(3) : "NaN"}
      `;
      if (newPoint.mag) {
        newPoint.text += `<br>Fluxerr: ${newPoint.fluxerr.toFixed(3) || "NaN"}`;
      }
      newPoint.text += `
        <br>Filter: ${newPoint.filter}
        <br>Instrument: ${newPoint.instrument_name}
      `;
      if ([null, undefined, "", "None"].includes(newPoint.origin) === false) {
        newPoint.text += `<br>Origin: ${newPoint.origin}`;
      }
      if (
        [null, undefined, "", "None", "undefined"].includes(
          newPoint.altdata?.exposure,
        ) === false
      ) {
        newPoint.text += `<br>Exposure: ${newPoint.altdata?.exposure || ""}`;
      }
      if (newPoint.snr) {
        newPoint.text += `<br>SNR: ${newPoint.snr.toFixed(3)}`;
      }
      if (newPoint.streams.length > 0) {
        newPoint.text += `<br>Streams: ${newPoint.streams.join(", ")}`;
      }

      stats.mag.min = Math.min(
        stats.mag.min,
        newPoint.mag || newPoint.limiting_mag,
      );
      stats.mag.max = Math.max(
        stats.mag.max,
        newPoint.mag || newPoint.limiting_mag,
      );
      stats.mjd.min = Math.min(stats.mjd.min, newPoint.mjd);
      stats.mjd.max = Math.max(stats.mjd.max, newPoint.mjd);
      stats.days_ago.min = Math.min(stats.days_ago.min, newPoint.days_ago);
      stats.days_ago.max = Math.max(stats.days_ago.max, newPoint.days_ago);
      stats.flux.min = Math.min(
        stats.flux.min,
        newPoint.flux || newPoint.fluxerr,
      );
      stats.flux.max = Math.max(
        stats.flux.max,
        newPoint.flux || newPoint.fluxerr,
      );

      return newPoint;
    });

    stats.mag.range = [stats.mag.max * 1.02, stats.mag.min * 0.98];
    stats.mjd.range = [stats.mjd.min - 1, stats.mjd.max + 1];
    stats.days_ago.range = [stats.days_ago.max + 1, stats.days_ago.min - 1];
    stats.flux.range = [stats.flux.min - 1, stats.flux.max + 1];

    return [newPhotometryData, stats];
  };

  const groupPhotometry = (photometryData) => {
    // before grouping, we compute the max and min for mag, flux, and days_ago
    // we will use these values to set the range of the plot

    const groupedPhotometry = photometryData.reduce((acc, point) => {
      let key = `${point.instrument_name}/${point.filter}`;
      if (
        point?.origin !== "None" &&
        point.origin !== "" &&
        point.origin !== null
      ) {
        // the origin is less relevant, so we crop it to not have more than 23 characters + 3 x ...
        const remaining = 23 - key.length;
        if (remaining < point.origin.length) {
          key += `/${point.origin.substring(0, Math.max(remaining - 3, 3))}...`;
        } else {
          key += `/${point.origin}`;
        }
      }
      if (!acc[key]) {
        acc[key] = [];
      }
      acc[key].push(point);
      return acc;
    }, {});

    return groupedPhotometry;
  };

  const tabToPlotType = (tabValue) => {
    if (tabValue === 0) {
      return "mag";
    }
    if (tabValue === 1) {
      return "flux";
    }
    if (tabValue === 2) {
      return "period";
    }
    return null;
  };

  const createTraces = (
    groupedPhotometry,
    plotType,
    periodValue,
    smoothingValue,
    phaseValue,
  ) => {
    if (plotType === "mag" || plotType === "flux") {
      const newPlotData = Object.keys(groupedPhotometry)
        .map((key) => {
          const detections = groupedPhotometry[key].filter(
            (point) => point.mag !== null,
          );
          const upperLimits = groupedPhotometry[key].filter(
            (point) => point.mag === null,
          );

          // TEMPORARY: until we have a mapper for each sncosmo filter, we force the color to be black
          const colorRGB = filter2color[groupedPhotometry[key][0].filter] || [
            0, 0, 0,
          ];
          const colorBorder = rgba(colorRGB, 1);
          const colorInteriorNonDet = rgba(colorRGB, 0.1);
          const colorInteriorDet = rgba(colorRGB, 0.3);
          const colorError = rgba(colorRGB, 0.5);

          const upperLimitsTrace = {
            dataType: "upperLimits",
            x: upperLimits.map((point) => point.mjd),
            y: upperLimits.map((point) =>
              plotType === "mag" ? point.limiting_mag : point.flux,
            ),
            text: upperLimits.map((point) => point.text),
            mode: "markers",
            type: "scatter",
            name: `${key} (UL)`,
            legendgroup: `${key}upperLimits`,
            marker: {
              line: {
                width: 1,
                color: colorBorder,
              },
              color: colorInteriorNonDet,
              opacity: 1,
              size: markerSize,
              symbol: "triangle-down",
            },
            visible: true,
            hoverlabel: {
              bgcolor: "white",
              font: { size: 14 },
              align: "left",
            },
            hovertemplate: "%{text}<extra></extra>",
          };

          const detectionsTrace = {
            dataType: "detections",
            x: detections.map((point) => point.mjd),
            y: detections.map((point) =>
              plotType === "mag" ? point.mag : point.flux,
            ),
            error_y: {
              type: "data",
              array: detections.map((point) =>
                plotType === "mag" ? point.magerr : point.fluxerr,
              ),
              visible: true,
              color: colorError,
              width: 1,
              thickness: 2,
            },
            text: detections.map((point) => point.text),
            mode: "markers",
            type: "scatter",
            name: key,
            legendgroup: `${key}detections`,
            marker: {
              line: {
                width: 1,
                color: colorBorder,
              },
              color: colorInteriorDet,
              size: markerSize,
            },
            visible: true,
            hoverlabel: {
              bgcolor: "white",
              font: { size: 14 },
              align: "left",
            },
            hovertemplate: "%{text}<extra></extra>",
          };

          const secondaryAxisX = {
            x: [photStats.days_ago.max, photStats.days_ago.min],
            y: [photStats.mag.max, photStats.mag.min],
            mode: "markers",
            type: "scatter",
            name: "secondaryAxisX",
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

          const secondaryAxisY = {
            x: [photStats.mjd.min, photStats.mjd.max],
            mode: "markers",
            type: "scatter",
            name: "secondaryAxisY",
            legendgroup: "secondaryAxisY",
            marker: {
              line: {
                width: 1,
              },
              opacity: 0,
            },
            visible: true,
            showlegend: false,
            yaxis: "y2",
            hoverinfo: "skip",
          };
          if (plotType === "mag" && dm && photStats) {
            secondaryAxisY.y = [photStats.mag.max - dm, photStats.mag.min - dm];
          }

          if (photStats && plotType === "mag" && dm) {
            return [
              detectionsTrace,
              upperLimitsTrace,
              secondaryAxisX,
              secondaryAxisY,
            ];
          }

          return [detectionsTrace, upperLimitsTrace, secondaryAxisX];
        })
        .flat();

      return newPlotData;
    }
    if (plotType === "period") {
      const newPlotData = Object.keys(groupedPhotometry)
        .map((key) => {
          // using the period state variable, calculate the phase of each point
          // and then plot the phase vs mag
          const colorRGB = filter2color[groupedPhotometry[key][0].filter] || [
            0, 0, 0,
          ];
          const colorBorder = rgba(colorRGB, 1);
          const colorInteriorNonDet = rgba(colorRGB, 0.1);
          const colorInteriorDet = rgba(colorRGB, 0.3);

          const phases = groupedPhotometry[key].map(
            (point) => (point.mjd % periodValue) / periodValue,
          );

          // split the y in det and non det
          let y = groupedPhotometry[key].map(
            (point) => point.mag || point.limiting_mag,
          );

          // reorder the points in y by increasing phase
          // to do so, we need to create an array of indices
          let indices = [];
          for (let i = 0; i < phases.length; i += 1) {
            indices.push(i);
          }
          indices = indices.sort((a, b) => phases[a] - phases[b]);
          y = indices.map((i) => y[i]);
          const x = indices.map((i) => phases[i]);

          if (smoothingValue > 0) {
            y = smoothing_func(y, smoothingValue);
          }

          // split the points into detections and upper limits
          // to do so, use the indices and the groupedPhotometry[key] array to know which index corresponds to a detection or an upper limit
          let detectionsX = [];
          let detectionsY = [];
          let detectionsText = [];
          let upperLimitsX = [];
          let upperLimitsY = [];
          let upperLimitsText = [];

          for (let i = 0; i < indices.length; i += 1) {
            if (groupedPhotometry[key][indices[i]].mag !== null) {
              detectionsX.push(x[i]);
              detectionsY.push(y[i]);
              detectionsText.push(groupedPhotometry[key][indices[i]].text);
            } else {
              upperLimitsX.push(x[i]);
              upperLimitsY.push(y[i]);
              upperLimitsText.push(groupedPhotometry[key][indices[i]].text);
            }
          }

          if (phaseValue === 2) {
            detectionsX = detectionsX.concat(detectionsX.map((p) => p + 1));
            detectionsY = detectionsY.concat(detectionsY);
            detectionsText = detectionsText.concat(detectionsText);
            upperLimitsX = upperLimitsX.concat(upperLimitsX.map((p) => p + 1));
            upperLimitsY = upperLimitsY.concat(upperLimitsY);
            upperLimitsText = upperLimitsText.concat(upperLimitsText);
          }

          const detectionsTrace = {
            dataType: "detections",
            x: detectionsX,
            y: detectionsY,
            text: detectionsText,
            mode: "markers",
            type: "scatter",
            name: key,
            legendgroup: key,
            marker: {
              line: {
                width: 1,
                color: colorBorder,
              },
              color: colorInteriorDet,
              size: markerSize,
            },
            visible: true,
            hoverlabel: {
              bgcolor: "white",
              font: { size: 14 },
              align: "left",
            },
            hovertemplate: "%{text}<extra></extra>",
          };

          const upperLimitsTrace = {
            dataType: "upperLimits",
            x: upperLimitsX,
            y: upperLimitsY,
            text: upperLimitsText,
            mode: "markers",
            type: "scatter",
            name: `${key} (UL)`,
            legendgroup: `${key}upperLimits`,
            marker: {
              line: {
                width: 1,
                color: colorBorder,
              },
              color: colorInteriorNonDet,
              size: markerSize,
              symbol: "triangle-down",
            },
            visible: true,
            hoverlabel: {
              bgcolor: "white",
              font: { size: 14 },
              align: "left",
            },
            hovertemplate: "%{text}<extra></extra>",
          };

          let secondaryAxisY = {};
          if (dm && photStats) {
            secondaryAxisY = {
              x: [0, 1],
              y: [photStats.mag.max - dm, photStats.mag.min - dm],
              mode: "markers",
              type: "scatter",
              name: "secondaryAxisY",
              legendgroup: "secondaryAxisY",
              marker: {
                line: {
                  width: 1,
                },
                opacity: 0,
              },
              visible: true,
              showlegend: false,
              yaxis: "y2",
              hoverinfo: "skip",
            };
          }

          if (dm) {
            return [detectionsTrace, upperLimitsTrace, secondaryAxisY];
          }

          return [detectionsTrace, upperLimitsTrace];
        })
        .flat();

      return newPlotData;
    }
    return null;
  };

  const createLayouts = (plotType, photStats_value, dm_value) => {
    const newLayouts = {};
    if (plotType === "mag" || plotType === "flux") {
      newLayouts.xaxis = {
        title: "MJD",
        side: "top",
        range: [...photStats_value.mjd.range],
        tickformat: ".6~f",
        ...BASE_LAYOUT,
      };
      newLayouts.xaxis2 = {
        title: "Days Ago",
        range: [...photStats_value.days_ago.range],
        overlaying: "x",
        side: "bottom",
        showgrid: false,
        tickformat: ".6~f",
        ...BASE_LAYOUT,
      };
    } else if (plotType === "period") {
      newLayouts.xaxis = {
        title: "Phase",
        side: "bottom",
        range: [0, phase],
        tickformat: ".2f",
        ...BASE_LAYOUT,
      };
    }

    if (plotType === "mag" || plotType === "period") {
      newLayouts.yaxis = {
        title: "AB Mag",
        range: [...photStats_value.mag.range],
        ...BASE_LAYOUT,
      };
      if (dm && photStats_value) {
        newLayouts.yaxis2 = {
          title: "m - DM",
          range: [
            photStats_value.mag.range[0] - dm_value,
            photStats_value.mag.range[1] - dm_value,
          ],
          overlaying: "y",
          side: "right",
          showgrid: false,
          ...BASE_LAYOUT,
        };
      }
    } else if (plotType === "flux") {
      newLayouts.yaxis = {
        title: "Flux",
        range: [...photStats_value.flux.range],
        ...BASE_LAYOUT,
      };
    }
    return newLayouts;
  };

  useEffect(() => {
    const [newPhotometry, newPhotStats] = preparePhotometry([...photometry]);
    const groupedPhotometry = groupPhotometry(newPhotometry);
    setPhotStats(newPhotStats);
    setData(groupedPhotometry);
  }, [photometry]);

  useEffect(() => {
    if (data !== null && filter2color !== null && photStats !== null) {
      if (!layoutReset) {
        const traces = createTraces(
          data,
          tabToPlotType(tabIndex),
          period,
          smoothing,
          phase,
        );
        setPlotData(traces);
      }

      const newLayouts = createLayouts(tabToPlotType(tabIndex), photStats, dm);
      setLayouts(newLayouts);
      if (layoutReset) {
        setLayoutReset(false);
      }
    }
  }, [data, filter2color, photStats, tabIndex, phase, layoutReset]);

  useEffect(() => {
    if (data !== null && filter2color !== null && photStats !== null) {
      const traces = createTraces(
        data,
        tabToPlotType(tabIndex),
        period,
        smoothing,
        phase,
      );
      setPlotData(traces);
    }
  }, [period, smoothing]);

  useEffect(() => {
    if (
      data !== null &&
      filter2color !== null &&
      photStats !== null &&
      annotations !== null
    ) {
      // each annotation has a data key, which is an object with key value pairs
      // try to find keys named 'period'
      // for each, get its value and the created_at value of the annotation
      // then set the period state variable to the value of the most recent period annotation
      const periodAnnotations = annotations.filter(
        (annotation) => annotation.data.period !== undefined,
      );
      if (periodAnnotations.length > 0) {
        let mostRecentPeriod = periodAnnotations[0].data.period;
        let mostRecentPeriodCreatedAt = new Date(
          periodAnnotations[0].created_at,
        );
        periodAnnotations.forEach((annotation) => {
          if (
            new Date(annotation.created_at) > mostRecentPeriodCreatedAt &&
            !Number.isNaN(parseFloat(annotation.data.period, 10))
          ) {
            mostRecentPeriod = annotation.data.period;
            mostRecentPeriodCreatedAt = new Date(annotation.created_at);
          }
        });
        setPeriod(parseFloat(mostRecentPeriod, 10));
      }
    }
  }, [data, filter2color, photStats, annotations]);

  useEffect(() => {
    if (plotData !== null) {
      const newPlotData = plotData.map((trace) => {
        const newTrace = { ...trace };
        newTrace.marker.size = parseInt(markerSize, 10);
        return newTrace;
      });
      setPlotData(newPlotData);
    }
  }, [markerSize]);

  useEffect(() => {
    if (plotData !== null) {
      const newPlotData = plotData.map((trace) => {
        const newTrace = { ...trace };
        if (
          showNonDetections &&
          newTrace.dataType === "upperLimits" &&
          newTrace.visible !== true
        ) {
          newTrace.visible = true;
          newTrace.showlegend = true;
        } else if (
          !showNonDetections &&
          newTrace.dataType === "upperLimits" &&
          newTrace.visible !== false
        ) {
          newTrace.visible = false;
          newTrace.showlegend = false;
        }
        return newTrace;
      });
      setPlotData(newPlotData);
    }
  }, [showNonDetections]);

  const handleChangeTab = (event, newValue) => {
    setTabIndex(newValue);
  };

  const yMarkers = [];
  if (photStats) {
    yMarkers.push(
      ["mag", "period"].includes(tabToPlotType(tabIndex))
        ? photStats.mag.range[1]
        : photStats.flux.range[1],
    );
  }

  const eventMarkers = photStats
    ? spectra
        .map((spectrum) => {
          const hovertext = `<br>Observed at (UTC): ${spectrum.observed_at}
    <br>Observed at (MJD): ${spectrum.observed_at_mjd.toFixed(6)})
    <br>Instrument: ${spectrum.instrument_name}
    <br>Telescope: ${spectrum.telescope_name}
    <br>PI: ${spectrum.pi || ""}
    <br>Origin: ${spectrum.origin || ""}
    <extra></extra>
    `;
          return {
            x: [spectrum.observed_at_mjd],
            y: yMarkers,
            mode: "text",
            type: "scatter",
            name: "Spectrum",
            legendgroup: "Spectrum",
            text: ["S"],
            textposition: "bottom center",
            textfont: { color: "black", size: 16 },
            marker: {
              line: {
                width: 1,
              },
              opacity: 1,
            },
            visible: true,
            showlegend: false,
            hoverlabel: {
              bgcolor: "white",
              font: { size: 14 },
              align: "left",
            },
            hovertemplate: hovertext,
          };
        })
        .concat(
          (gcn_events || []).map((event) => {
            const hovertext = `<br>Dateobs: ${event.dateobs}
    <br>Aliases: ${(event.aliases || []).join(", ")}
    <extra></extra>
    `;
            return {
              x: [event.dateobs_mjd],
              y: yMarkers,
              mode: "text",
              type: "scatter",
              name: "GCN Event",
              legendgroup: "GCN Event",
              text: ["G"],
              textposition: "bottom center",
              textfont: { color: "black", size: 16 },
              marker: {
                line: {
                  width: 1,
                },
                opacity: 1,
              },
              visible: true,
              showlegend: false,
              hoverlabel: {
                bgcolor: "white",
                font: { size: 14 },
                align: "left",
              },
              hovertemplate: hovertext,
            };
          }),
        )
    : [];

  return (
    <div style={{ width: "100%", height: "100%" }} id="photometry-plot">
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
        <Tab label="Mag" />
        <Tab label="Flux" />
        <Tab label="Period" />
      </Tabs>

      <div
        style={{
          width: "100%",
          height: plotStyle?.height || "70vh",
          overflowX: "scroll",
        }}
      >
        <Plot
          data={(plotData || []).concat(eventMarkers || [])}
          layout={{
            ...layouts,
            legend: {
              orientation: mode === "desktop" ? "v" : "h",
              yanchor: "top",
              // on mobile with a lot of legend entries, we need to move the legend down to avoid overlap
              y: mode === "desktop" ? 1 : plotData?.length > 10 ? -0.4 : -0.3, // eslint-disable-line no-nested-ternary
              x: mode === "desktop" ? (dm ? 1.15 : 1) : 0, // eslint-disable-line no-nested-ternary
              font: { size: 14 },
              tracegroupgap: 0,
            },
            showlegend: true,
            autosize: true,
            margin: {
              l: 70,
              r: 30,
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
          }}
          config={{
            responsive: true,
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
          onDoubleClick={() => setLayoutReset(true)}
          onLegendDoubleClick={(e) => {
            // e contains a curveNumber (index of the trace clicked in the legend)
            /// and a data object (plotting data)
            // we customize the legend double click behavior
            const visibleTraces = e.data.filter(
              (trace) =>
                ["detections", "upperLimits"].includes(trace.dataType) &&
                trace.visible === true,
            ).length;
            const visibleTraceIndex = e.data.findIndex(
              (trace) =>
                ["detections", "upperLimits"].includes(trace.dataType) &&
                trace.visible === true,
            );
            e.data.forEach((trace, index) => {
              if (
                [
                  "secondaryAxisX",
                  "secondaryAxisY",
                  "Spectrum",
                  "GCN Event",
                ].includes(trace.name) ||
                index === e.curveNumber
              ) {
                // if its a marker, secondary axis, or the trace that was double clicked, it's always visible
                trace.visible = true;
              } else if (
                !showNonDetections &&
                trace.dataType === "upperLimits"
              ) {
                // if we don't want to show non detections, hide them
                trace.visible = false;
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
          style={{ width: "100%", height: "100%" }}
        />
      </div>
      <div className={classes.gridContainer}>
        <div className={classes.gridItem} style={{ gridColumn: "span 1" }}>
          <Typography id="photometry-show-hide" noWrap>
            Non-Detections
          </Typography>
          <div className={classes.switchContainer}>
            <Switch
              checked={showNonDetections}
              onChange={() => setShowNonDetections(!showNonDetections)}
              inputProps={{ "aria-label": "controlled" }}
            />
          </div>
        </div>
        <div className={classes.gridItem} style={{ gridColumn: "span 2" }}>
          <Typography id="input-slider" noWrap>
            Marker Size
          </Typography>
          <div className={classes.sliderContainer}>
            <Slider
              value={markerSize}
              onChange={(e, newValue) => setMarkerSize(newValue)}
              aria-labelledby="input-slider"
              valueLabelDisplay="auto"
              step={1}
              min={1}
              max={20}
            />
            {mode === "desktop" && (
              <TextField
                value={markerSize}
                onChange={(e) => setMarkerSize(e.target.value)}
                margin="dense"
                type="number"
                inputProps={{
                  step: 1,
                  min: 1,
                  max: 20,
                  "aria-labelledby": "input-slider",
                }}
                size="small"
              />
            )}
          </div>
        </div>
        {tabIndex === 2 && (
          <div className={classes.gridItem} style={{ gridColumn: "span 3" }}>
            <Typography id="input-slider">Period (days)</Typography>
            <div className={classes.sliderContainer}>
              <Slider
                value={period}
                onChange={(e, newValue) => setPeriod(newValue)}
                aria-labelledby="input-slider"
                valueLabelDisplay="auto"
                step={0.1}
                min={0.1}
                max={365}
              />
              <TextField
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                margin="dense"
                type="number"
                inputProps={{
                  step: 0.1,
                  min: 0.1,
                  max: 365,
                  "aria-labelledby": "input-slider",
                }}
                style={{ width: "12rem" }}
                size="small"
              />
              <Button
                onClick={() => setPeriod(period * 2)}
                variant="contained"
                color="primary"
              >
                x2
              </Button>
              <Button
                onClick={() => setPeriod(period / 2)}
                variant="contained"
                color="primary"
              >
                /2
              </Button>
              <PeriodAnnotationDialog obj_id={obj_id} period={period} />
            </div>
          </div>
        )}
        {tabIndex === 2 && (
          <div className={classes.gridItem} style={{ gridColumn: "span 2" }}>
            <Typography id="input-slider">Smoothing</Typography>
            <div className={classes.sliderContainer}>
              <Slider
                value={smoothing}
                onChange={(e, newValue) => setSmoothing(newValue)}
                aria-labelledby="input-slider"
                valueLabelDisplay="auto"
                step={1}
                min={0}
                max={100}
              />
              <TextField
                value={smoothing}
                onChange={(e) => setSmoothing(e.target.value)}
                margin="dense"
                type="number"
                inputProps={{
                  step: 1,
                  min: 0,
                  max: 100,
                  type: "number",
                  "aria-labelledby": "input-slider",
                }}
                size="small"
              />
            </div>
          </div>
        )}
        {tabIndex === 2 && (
          <div className={classes.gridItem} style={{ gridColumn: "span 1" }}>
            <Typography id="input-slider">Phase</Typography>
            <div className={classes.doubleSwitch}>
              <Typography>1</Typography>
              <Switch
                checked={phase === 2}
                onChange={() => setPhase(phase === 2 ? 1 : 2)}
                inputProps={{ "aria-label": "controlled" }}
              />
              <Typography>2</Typography>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

PhotometryPlot.propTypes = {
  obj_id: PropTypes.string.isRequired,
  dm: PropTypes.number,
  photometry: PropTypes.arrayOf(
    PropTypes.shape({
      mjd: PropTypes.number.isRequired,
      mag: PropTypes.number,
      magerr: PropTypes.number,
      limiting_mag: PropTypes.number,
      filter: PropTypes.string.isRequired,
      instrument_name: PropTypes.string.isRequired,
      origin: PropTypes.string,
    }),
  ).isRequired,
  annotations: PropTypes.arrayOf(
    PropTypes.shape({
      data: PropTypes.shape({}),
      created_at: PropTypes.string.isRequired,
    }),
  ),
  spectra: PropTypes.arrayOf(
    PropTypes.shape({
      observed_at: PropTypes.string.isRequired,
      observed_at_mjd: PropTypes.number.isRequired,
      instrument_name: PropTypes.string.isRequired,
      telescope_name: PropTypes.string.isRequired,
      pi: PropTypes.string,
      origin: PropTypes.string,
    }),
  ),
  gcn_events: PropTypes.arrayOf(PropTypes.string),
  mode: PropTypes.string,
  plotStyle: PropTypes.shape({
    height: PropTypes.string,
  }),
};

PhotometryPlot.defaultProps = {
  dm: null,
  annotations: [],
  gcn_events: [],
  spectra: [],
  mode: "desktop",
  plotStyle: {
    height: "65vh",
  },
};

export default PhotometryPlot;
