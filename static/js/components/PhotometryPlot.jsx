import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import Slider from "@mui/material/Slider";
import MuiInput from "@mui/material/Input";
import Typography from "@mui/material/Typography";
import SaveAsIcon from "@mui/icons-material/SaveAs";

import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { useSelector, useDispatch } from "react-redux";

import { IconButton } from "@mui/material";

import { showNotification } from "baselayer/components/Notifications";
import { addAnnotation } from "../ducks/source";
import Button from "./Button";

import { smoothing_func } from "./SpectraPlot";

const Plot = createPlotlyComponent(Plotly);

function ModifiedJulianDateFromUnixTime(t) {
  return t / 86400000 + 40587;
}

function ModifiedJulianDateNow() {
  return ModifiedJulianDateFromUnixTime(new Date().getTime());
}

const PhotometryPlot = ({
  obj_id,
  photometry,
  annotations = [],
  mode = "desktop",
}) => {
  const dispatch = useDispatch();

  const [data, setData] = useState(null);
  const [binnedData, setBinnedData] = useState(null);
  const [plotData, setPlotData] = useState(null);
  const [markerSize, setMarkerSize] = useState(6);
  const [tabIndex, setTabIndex] = useState(0);
  const [period, setPeriod] = useState(1);
  const [binSize, setBinSize] = useState(0);
  const [smoothing, setSmoothing] = useState(0);
  const [phase, setPhase] = useState(1);

  const [dialogOpen, setDialogOpen] = useState(false);

  const filter2color = useSelector(
    (state) => state.config.bandpassesColors || {}
  );
  const groups = useSelector((state) => state.groups.userAccessible);

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

  // tab 0 is mag, tab 1 is flux, tab 2 is period

  const preparePhotometry = (photometryData) => {
    const now = ModifiedJulianDateNow();
    photometryData.forEach((point) => {
      point.days_ago = now - point.mjd;
    });

    // iterate over all the points and calculate the flux and fluxerr
    photometryData.forEach((point) => {
      if (point.mag !== null) {
        point.flux = 10 ** (-0.4 * (point.mag - 25));
        point.fluxerr = (point.magerr / (2.5 / Math.log(10))) * point.flux;
      } else {
        point.flux = 10 ** (-0.4 * (point.limiting_mag - 25));
        point.fluxerr = 0;
      }
    });

    return photometryData;
  };

  const groupPhotometry = (photometryData) => {
    const groupedPhotometry = photometryData.reduce((acc, point) => {
      let key = `${point.filter}/${point.instrument_name}`;
      if (
        point?.origin !== "None" &&
        point.origin !== "" &&
        point.origin !== null
      ) {
        key += `/${point.origin}`;
      }
      if (!acc[key]) {
        acc[key] = [];
      }
      acc[key].push(point);
      return acc;
    }, {});

    return groupedPhotometry;
  };

  const createTraces = (
    groupedPhotometry,
    tabValue,
    periodValue,
    smoothingValue,
    phaseValue
  ) => {
    // if the tabValue is 0 or 1
    if (tabValue in [0, 1] === true) {
      const newPlotData = Object.keys(groupedPhotometry)
        .map((key) => {
          const detections = groupedPhotometry[key].filter(
            (point) => point.mag !== null
          );
          const upperLimits = groupedPhotometry[key].filter(
            (point) => point.mag === null
          );

          // TEMPORARY: until we have a mapper for each sncosmo filter, we force the color to be black
          const colorRGB = filter2color[groupedPhotometry[key][0].filter] || [
            0, 0, 0,
          ];
          const colorBorder = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 1)`;
          const colorInterior = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 0.5)`;
          const colorError = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 0.5)`;

          const upperLimitsTrace = {
            x: upperLimits.map((point) => point.days_ago),
            y: upperLimits.map((point) =>
              tabValue === 0 ? point.limiting_mag : point.flux
            ),
            mode: "markers",
            type: "scatter",
            name: key,
            legendgroup: key,
            marker: {
              line: {
                width: 1,
                color: colorBorder,
              },
              color: colorInterior,
              opacity: 1,
              size: markerSize,
              symbol: "triangle-down",
            },
            visible: true,
          };

          const detectionsTrace = {
            x: detections.map((point) => point.days_ago),
            y: detections.map((point) =>
              tabValue === 0 ? point.mag : point.flux
            ),
            error_y: {
              type: "data",
              array: detections.map((point) =>
                tabValue === 0 ? point.magerr : point.fluxerr
              ),
              visible: true,
              color: colorError,
              width: 1,
              thickness: 1,
            },
            mode: "markers",
            type: "scatter",
            name: key,
            legendgroup: key,
            marker: {
              line: {
                width: 1,
                color: colorBorder,
              },
              color: colorInterior,
              size: markerSize,
            },
            visible: true,
          };

          if (detections.length > 0) {
            upperLimitsTrace.showlegend = false;
          } else {
            detectionsTrace.showlegend = false;
          }

          return [detectionsTrace, upperLimitsTrace];
        })
        .flat();

      return newPlotData;
    }
    if (tabValue === 2) {
      const newPlotData = Object.keys(groupedPhotometry).map((key) => {
        // using the period state variable, calculate the phase of each point
        // and then plot the phase vs mag
        // we only keep the detections here
        const detections = groupedPhotometry[key].filter(
          (point) => point.mag !== null
        );

        const colorRGB = filter2color[groupedPhotometry[key][0].filter];
        const colorBorder = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 1)`;
        const colorInterior = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 0.5)`;

        const phases = detections.map(
          (point) => (point.mjd % periodValue) / periodValue
        );

        let y = detections.map((point) => point.mag);
        // reorder the points in y by increasing phase
        // to do so, we need to create an array of indices
        let indices = [];
        for (let i = 0; i < phases.length; i += 1) {
          indices.push(i);
        }
        indices = indices.sort((a, b) => phases[a] - phases[b]);
        y = indices.map((i) => y[i]);
        let x = indices.map((i) => phases[i]);

        if (smoothingValue > 0) {
          y = smoothing_func(y, smoothingValue);
        }

        if (phaseValue === 2) {
          x = x.concat(x.map((p) => p + 1));
          y = y.concat(y);
        }

        const detectionsTrace = {
          x,
          y,
          mode: "markers",
          type: "scatter",
          name: key,
          legendgroup: key,
          marker: {
            line: {
              width: 1,
              color: colorBorder,
            },
            color: colorInterior,
            size: markerSize,
          },
          visible: true,
        };
        return detectionsTrace;
      });

      return newPlotData;
    }
    return null;
  };

  useEffect(() => {
    if (annotations !== null) {
      // each annotation has a data key, which is an object with key value pairs
      // try to find keys named 'period'
      // for each, get its value and the created_at value of the annotation
      // then set the period state variable to the value of the most recent period annotation
      const periodAnnotations = annotations.filter(
        (annotation) => annotation.data.period !== undefined
      );
      if (periodAnnotations.length > 0) {
        let mostRecentPeriod = periodAnnotations[0].data.period;
        let mostRecentPeriodCreatedAt = new Date(
          periodAnnotations[0].created_at
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
  }, [annotations]);

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
    const newBinSize = parseInt(binSize, 10);
    if (
      data !== null &&
      tabIndex in [0, 1] === true &&
      Number.isNaN(newBinSize) === false
    ) {
      if (newBinSize < 0) {
        setBinSize(0);
        return;
      }
      if (newBinSize === 0) {
        setBinnedData(null);
        return;
      }
      // here we will bin the photometry data by binSize if binSize is > 1
      // we store the results in data

      const newPhotometry = preparePhotometry(photometry);
      const groupedPhotometry = groupPhotometry(newPhotometry);

      const nbKeys = Object.keys(groupedPhotometry).length;
      const keys = Object.keys(groupedPhotometry);

      for (let index = 0; index < nbKeys; index += 1) {
        const detectionsAndUpperLimits = [
          groupedPhotometry[keys[index]].filter((point) => point.mag !== null),
          groupedPhotometry[keys[index]].filter((point) => point.mag === null),
        ];

        // run the code below on detections and upper limits separately
        const binnedPhotometry = detectionsAndUpperLimits
          .map((phot) => {
            const min_mjd = Math.min(...phot.map((point) => point.mjd));
            const max_mjd = Math.max(...phot.map((point) => point.mjd));

            const binEdges = [];
            for (let i = min_mjd; i < max_mjd; i += newBinSize) {
              binEdges.push(i);
            }

            const binnedPhot = [];
            for (let i = 0; i < binEdges.length - 1; i += 1) {
              const binStart = binEdges[i];
              const binEnd = binEdges[i + 1];
              const binCenter = (binStart + binEnd) / 2;
              const binPoints = phot.filter(
                (point) => point.mjd >= binStart && point.mjd < binEnd
              );
              if (binPoints.length > 0) {
                const existingPoint = binPoints[0];
                if (existingPoint.mag === null) {
                  const binLimitingMag =
                    binPoints.reduce(
                      (acc, point) => acc + point.limiting_mag,
                      0
                    ) / binPoints.length;
                  const binFlux =
                    binPoints.reduce((acc, point) => acc + point.flux, 0) /
                    binPoints.length;

                  const binPoint = {
                    ...existingPoint,
                    mjd: binCenter,
                    limiting_mag: binLimitingMag,
                    flux: binFlux,
                  };
                  binnedPhot.push(binPoint);
                } else {
                  const binMag =
                    binPoints.reduce((acc, point) => acc + point.mag, 0) /
                    binPoints.length;
                  const binMagerr =
                    binPoints.reduce((acc, point) => acc + point.magerr, 0) /
                    binPoints.length;
                  const binFlux =
                    binPoints.reduce((acc, point) => acc + point.flux, 0) /
                    binPoints.length;
                  const binFluxerr =
                    binPoints.reduce((acc, point) => acc + point.fluxerr, 0) /
                    binPoints.length;
                  const binPoint = {
                    ...existingPoint,
                    mjd: binCenter,
                    mag: binMag,
                    magerr: binMagerr,
                    flux: binFlux,
                    fluxerr: binFluxerr,
                  };
                  binnedPhot.push(binPoint);
                }
              }
            }
            return binnedPhot;
          })
          .flat();

        groupedPhotometry[keys[index]] = binnedPhotometry;
      }

      setBinnedData(groupedPhotometry);
    }
  }, [binSize]);

  useEffect(() => {
    // get the current plot data and update the x and y values
    if (plotData !== null) {
      const newPlotData = plotData.map((trace) => {
        const key = trace.name;
        const group = data[key];
        const groupBinned = binnedData !== null ? binnedData[key] || [] : [];
        const newTrace = { ...trace };
        // if the symbol is a triangle, then we are dealing with upper limits
        // we also look at the name to get the key for the groupedPhotometry object

        if (newTrace.marker.symbol === "triangle-down") {
          const upperLimits = group.filter((point) => point.mag === null);
          const upperLimitsBinned = group.filter((point) => point.mag === null);
          const x = upperLimits
            .map((point) => point.days_ago)
            .concat(upperLimitsBinned.map((point) => point.days_ago));
          const y = upperLimits
            .map((point) => (tabIndex === 0 ? point.limiting_mag : point.flux))
            .concat(
              upperLimitsBinned.map((point) =>
                tabIndex === 0 ? point.limiting_mag : point.flux
              )
            );
          newTrace.x = x;
          newTrace.y = y;
        } else {
          const detections = group.filter((point) => point.mag !== null);
          const detectionsBinned = groupBinned.filter(
            (point) => point.mag !== null
          );
          const x = detections
            .map((point) => point.days_ago)
            .concat(detectionsBinned.map((point) => point.days_ago));
          const y = detections
            .map((point) => (tabIndex === 0 ? point.mag : point.flux))
            .concat(
              detectionsBinned.map((point) =>
                tabIndex === 0 ? point.mag : point.flux
              )
            );
          const error_y = detections
            .map((point) => (tabIndex === 0 ? point.magerr : point.fluxerr))
            .concat(
              detectionsBinned.map((point) =>
                tabIndex === 0 ? point.magerr : point.fluxerr
              )
            );
          newTrace.x = x;
          newTrace.y = y;
          newTrace.error_y.array = error_y;
        }
        return newTrace;
      });

      setPlotData(newPlotData);
    }
  }, [binnedData]);

  useEffect(() => {
    const newPeriod = parseFloat(period, 10);
    if (
      plotData !== null &&
      tabIndex === 2 &&
      Number.isNaN(newPeriod) === false
    ) {
      const newPlotData = [];
      // get the number of keys in data
      const nbKeys = Object.keys(data).length;
      const keys = Object.keys(data);
      for (let index = 0; index < nbKeys; index += 1) {
        const detections = data[keys[index]].filter(
          (point) => point.mag !== null
        );
        if (detections.length > 0) {
          const phases = detections.map(
            (point) => (point.mjd % period) / period
          );
          const newTrace = { ...plotData[index] };
          let y = detections.map((point) => point.mag);
          // reorder the points in y by increasing phase
          // to do so, we need to create an array of indices
          let indices = [];
          for (let i = 0; i < phases.length; i += 1) {
            indices.push(i);
          }
          indices = indices.sort((a, b) => phases[a] - phases[b]);
          y = indices.map((i) => y[i]);
          let x = indices.map((i) => phases[i]);

          if (smoothing > 0) {
            y = smoothing_func(y, smoothing);
          }

          if (phase === 2) {
            x = x.concat(x.map((p) => p + 1));
            y = y.concat(y);
          }
          newTrace.x = x;
          newTrace.y = y;
          newPlotData.push(newTrace);
        }
      }

      setPlotData(newPlotData);
    }
  }, [period, smoothing, phase]);

  useEffect(() => {
    // photometry is an array of objects
    // each object has mjd, mag, magerr, limiting_mag, filter, instrument_name, and optional origin

    // we want to group points by filter, instrument name and origin if it exists (or isnt an empty string, or null)
    // the grouping is used to determine the color of the points, and for the legend
    // points with null mag are upper limits, plotted as inverted triangles
    // points with mag are plotted as circles

    // first iterate over the points and add a 'days_ago' field
    // this is the current date in mjd minus the mjd of the point
    const newPhotometry = preparePhotometry(photometry);
    const groupedPhotometry = groupPhotometry(newPhotometry);

    setData(groupedPhotometry);

    const traces = createTraces(
      groupedPhotometry,
      tabIndex,
      period,
      smoothing,
      phase
    );
    setPlotData(traces);
  }, [photometry]);

  const ShowOrHideAllPhotometry = (showOrHide) => {
    if (plotData !== null) {
      const newPlotData = plotData.map((trace) => {
        const newTrace = { ...trace };
        if (showOrHide === "hide") {
          newTrace.visible = "legendonly";
        } else if (showOrHide === "show") {
          newTrace.visible = true;
        }
        return newTrace;
      });
      setPlotData(newPlotData);
    }
  };

  const handleChangeTab = (event, newValue) => {
    const traces = createTraces(data, newValue, period, smoothing, phase);
    setPlotData(traces);
    setTabIndex(newValue);
    setBinSize(0);
  };

  return (
    <div style={{ width: "100%", height: "100%" }}>
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
        <Tab label="Mag" />
        <Tab label="Flux" />
        <Tab label="Period" />
      </Tabs>

      {tabIndex === 0 && (
        <div style={{ width: "100%", height: "60vh", overflowX: "scroll" }}>
          <Plot
            data={plotData}
            layout={{
              xaxis: {
                title: "Days Ago",
                autorange: "reversed",
              },
              yaxis: {
                title: "AB Mag",
                autorange: "reversed",
              },
              legend: {
                orientation: mode === "desktop" ? "v" : "h",
                yanchor: "top",
                y: mode === "desktop" ? 1 : -0.15,
              },
              showlegend: true,
              autosize: true,
              margin: {
                l: 60,
                r: 15,
                b: 50,
                t: 30,
              },
              // plot_bgcolor: '#EFF2F5',
              // paper_bgcolor: '#EFF2F5'
            }}
            config={{
              // scrollZoom: true,
              displaylogo: false,
            }}
            useResizeHandler
            style={{ width: "100%", height: "100%" }}
          />
        </div>
      )}
      {tabIndex === 1 && (
        <div style={{ width: "100%", height: "60vh", overflowX: "scroll" }}>
          <Plot
            data={plotData}
            layout={{
              xaxis: {
                title: "Days Ago",
                autorange: "reversed",
              },
              yaxis: {
                title: "Flux",
              },
              legend: {
                orientation: mode === "desktop" ? "v" : "h",
                yanchor: "top",
                y: mode === "desktop" ? 1 : -0.15,
              },
              showlegend: true,
              autosize: true,
              margin: {
                l: 60,
                r: 15,
                b: 50,
                t: 30,
              },
              // plot_bgcolor: '#EFF2F5',
              // paper_bgcolor: '#EFF2F5'
            }}
            config={{
              // scrollZoom: true,
              displaylogo: false,
            }}
            useResizeHandler
            style={{ width: "100%", height: "100%" }}
          />
        </div>
      )}
      {tabIndex === 2 && (
        <div style={{ width: "100%", height: "60vh", overflowX: "scroll" }}>
          <Plot
            data={plotData}
            layout={{
              xaxis: {
                title: "Phase",
                range: [0, phase],
              },
              yaxis: {
                title: "AB Mag",
                autorange: "reversed",
              },
              legend: {
                orientation: mode === "desktop" ? "v" : "h",
                yanchor: "top",
                y: mode === "desktop" ? 1 : -0.15,
              },
              showlegend: true,
              autosize: true,
              margin: {
                l: 60,
                r: 15,
                b: 50,
                t: 30,
              },
              // plot_bgcolor: '#EFF2F5',
              // paper_bgcolor: '#EFF2F5'
            }}
            config={{
              // scrollZoom: true,
              displaylogo: false,
            }}
            useResizeHandler
            style={{ width: "100%", height: "100%" }}
          />
        </div>
      )}
      <div
        style={{
          minHeight: "2rem",
          display: "flex",
          flexDirection: "row",
          justifyContent: "flex-start",
          alignItems: "center",
          gap: "0.5rem",
          width: "100%",
          marginTop: "1rem",
          marginBottom: "1rem",
        }}
      >
        <Button
          onClick={() => ShowOrHideAllPhotometry("show")}
          variant="contained"
          color="primary"
          size="small"
        >
          Show All
        </Button>
        <Button
          onClick={() => ShowOrHideAllPhotometry("hide")}
          variant="contained"
          color="primary"
          size="small"
        >
          Hide All
        </Button>
      </div>
      <div
        style={{
          display: "grid",
          gridAutoFlow: "row",
          gridTemplateColumns: "repeat(2, 1fr)",
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
          }}
        >
          <Typography id="input-slider">Marker Size</Typography>
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
              value={markerSize}
              onChange={(e, newValue) => setMarkerSize(newValue)}
              aria-labelledby="input-slider"
              valueLabelDisplay="auto"
              step={1}
              min={1}
              max={20}
            />
            <MuiInput
              value={markerSize}
              onChange={(e) => setMarkerSize(e.target.value)}
              margin="dense"
              inputProps={{
                step: 1,
                min: 1,
                max: 20,
                type: "number",
                "aria-labelledby": "input-slider",
              }}
              style={{ width: "7rem" }}
            />
          </div>
        </div>
        {tabIndex in [0, 1] === true && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "flex-start",
              alignItems: "left",
              gap: 0,
              width: "100%",
            }}
          >
            <Typography id="input-slider">Bin Size (days)</Typography>
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
                value={binSize}
                onChange={(e, newValue) => setBinSize(newValue)}
                aria-labelledby="input-slider"
                valueLabelDisplay="auto"
                step={1}
                min={0}
                max={365}
              />
              <MuiInput
                value={binSize}
                onChange={(e) => setBinSize(e.target.value)}
                margin="dense"
                inputProps={{
                  step: 1,
                  min: 0,
                  max: 365,
                  type: "number",
                  "aria-labelledby": "input-slider",
                }}
                style={{ width: "7rem" }}
              />
            </div>
          </div>
        )}
        {tabIndex === 2 && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "flex-start",
              alignItems: "left",
              gap: 0,
              width: "100%",
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
                value={smoothing}
                onChange={(e, newValue) => setSmoothing(newValue)}
                aria-labelledby="input-slider"
                valueLabelDisplay="auto"
                step={1}
                min={0}
                max={100}
              />
              <MuiInput
                value={smoothing}
                onChange={(e) => setSmoothing(e.target.value)}
                margin="dense"
                inputProps={{
                  step: 1,
                  min: 0,
                  max: 100,
                  type: "number",
                  "aria-labelledby": "input-slider",
                }}
                style={{ width: "7rem" }}
              />
            </div>
          </div>
        )}
        {tabIndex === 2 && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "flex-start",
              alignItems: "left",
              gap: 0,
              width: "100%",
            }}
          >
            <Typography id="input-slider">Period</Typography>
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
              <MuiInput
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                margin="dense"
                inputProps={{
                  step: 0.1,
                  min: 0,
                  max: 365,
                  type: "number",
                  "aria-labelledby": "input-slider",
                }}
                style={{ width: "10rem" }}
              />
              <Button
                onClick={() => setPeriod(period * 2)}
                variant="contained"
                color="primary"
                size="small"
              >
                x2
              </Button>
              <Button
                onClick={() => setPeriod(period / 2)}
                variant="contained"
                color="primary"
                size="small"
              >
                /2
              </Button>
              <IconButton
                onClick={() => setDialogOpen(true)}
                size="small"
                color="primary"
              >
                <SaveAsIcon />
              </IconButton>
            </div>
          </div>
        )}
        {tabIndex === 2 && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "flex-start",
              alignItems: "left",
              gap: 0,
              width: "100%",
            }}
          >
            <Typography id="input-slider">Phase</Typography>
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
              <Button
                onClick={() => setPhase(1)}
                variant="contained"
                color={phase === 1 ? "primary" : "secondary"}
                size="small"
              >
                1
              </Button>
              <Button
                onClick={() => setPhase(2)}
                variant="contained"
                color={phase === 2 ? "primary" : "secondary"}
                size="small"
              >
                2
              </Button>
            </div>
          </div>
        )}
      </div>
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
    </div>
  );
};

PhotometryPlot.propTypes = {
  obj_id: PropTypes.string.isRequired,
  photometry: PropTypes.arrayOf(
    PropTypes.shape({
      mjd: PropTypes.number.isRequired,
      mag: PropTypes.number,
      magerr: PropTypes.number,
      limiting_mag: PropTypes.number,
      filter: PropTypes.string.isRequired,
      instrument_name: PropTypes.string.isRequired,
      origin: PropTypes.string,
    })
  ).isRequired,
  annotations: PropTypes.arrayOf(
    PropTypes.shape({
      data: PropTypes.shape({}),
      created_at: PropTypes.string.isRequired,
    })
  ),
  mode: PropTypes.string,
};

PhotometryPlot.defaultProps = {
  annotations: [],
  mode: "desktop",
};

export default PhotometryPlot;
