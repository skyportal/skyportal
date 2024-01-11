import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import Slider from "@mui/material/Slider";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import SaveAsIcon from "@mui/icons-material/SaveAs";
import IconButton from "@mui/material/IconButton";
import Switch from "@mui/material/Switch";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";

import { addAnnotation } from "../ducks/source";
import { smoothing_func } from "./SpectraPlot";

const Plot = createPlotlyComponent(Plotly);

function ModifiedJulianDateFromUnixTime(t) {
  return t / 86400000 + 40587;
}

function ModifiedJulianDateNow() {
  return ModifiedJulianDateFromUnixTime(new Date().getTime());
}

const PHOT_ZP = 23.9;
const BASE_LAYOUT = {
  // tickformat: "digits",
  automargin: true,
  ticks: "outside",
  ticklen: 12,
  minor: {
    ticks: "outside",
    ticklen: 6,
    tickcolor: "black",
  },
  showline: true,
  titlefont: { size: 18 },
  tickfont: { size: 14 },
};

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
      <IconButton
        onClick={() => setDialogOpen(true)}
        size="small"
        style={{ marginLeft: "0.5rem" }}
      >
        <SaveAsIcon />
      </IconButton>

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

const PhotometryPlotV2 = ({
  obj_id,
  dm,
  photometry,
  annotations = [],
  mode = "desktop",
}) => {
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
    (state) => state.config.bandpassesColors || {}
  );

  const [layoutReset, setLayoutReset] = useState(false);

  const dm_flux = dm ? 10 ** (-0.4 * (dm - PHOT_ZP)) : null;

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

    const now = ModifiedJulianDateNow();

    photometryData.forEach((point) => {
      point.days_ago = now - point.mjd;
      if (point.mag !== null) {
        point.flux = 10 ** (-0.4 * (point.mag - PHOT_ZP));
        point.fluxerr = (point.magerr / (2.5 / Math.log(10))) * point.flux;
      } else {
        point.flux = 10 ** (-0.4 * (point.limiting_mag - PHOT_ZP));
        point.fluxerr = 0;
      }
      stats.mag.min = Math.min(stats.mag.min, point.mag || point.limiting_mag);
      stats.mag.max = Math.max(stats.mag.max, point.mag || point.limiting_mag);
      stats.mjd.min = Math.min(stats.mjd.min, point.mjd);
      stats.mjd.max = Math.max(stats.mjd.max, point.mjd);
      stats.days_ago.min = Math.min(stats.days_ago.min, point.days_ago);
      stats.days_ago.max = Math.max(stats.days_ago.max, point.days_ago);
      stats.flux.min = Math.min(stats.flux.min, point.flux || point.fluxerr);
      stats.flux.max = Math.max(stats.flux.max, point.flux || point.fluxerr);
    });

    stats.mag.range = [stats.mag.max + 0.2, stats.mag.min - 0.2];
    stats.mjd.range = [stats.mjd.min - 1, stats.mjd.max + 1];
    stats.days_ago.range = [stats.days_ago.max + 1, stats.days_ago.min - 1];
    stats.flux.range = [stats.flux.min - 1, stats.flux.max + 1];

    return [photometryData, stats];
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
    phaseValue
  ) => {
    if (plotType === "mag" || plotType === "flux") {
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
          const colorInteriorNonDet = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 0.1)`;
          const colorInteriorDet = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 0.3)`;
          const colorError = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 0.5)`;

          const upperLimitsTrace = {
            x: upperLimits.map((point) => point.mjd),
            y: upperLimits.map((point) =>
              plotType === "mag" ? point.limiting_mag : point.flux
            ),
            mode: "markers",
            type: "scatter",
            name: key,
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
          };

          const detectionsTrace = {
            x: detections.map((point) => point.mjd),
            y: detections.map((point) =>
              plotType === "mag" ? point.mag : point.flux
            ),
            error_y: {
              type: "data",
              array: detections.map((point) =>
                plotType === "mag" ? point.magerr : point.fluxerr
              ),
              visible: true,
              color: colorError,
              width: 1,
              thickness: 2,
            },
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
          } else if (plotType === "flux" && dm_flux && photStats) {
            secondaryAxisY.y = [
              photStats.flux.max - dm_flux,
              photStats.flux.min - dm_flux,
            ];
          }

          if (
            (photStats && plotType === "mag" && dm) ||
            (plotType === "flux" && dm_flux)
          ) {
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

          const colorRGB = filter2color[groupedPhotometry[key][0].filter];
          const colorBorder = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 1)`;
          const colorInteriorNonDet = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 0.1)`;
          const colorInteriorDet = `rgba(${colorRGB[0]},${colorRGB[1]},${colorRGB[2]}, 0.3)`;

          const phases = groupedPhotometry[key].map(
            (point) => (point.mjd % periodValue) / periodValue
          );

          // split the y in det and non det
          let y = groupedPhotometry[key].map(
            (point) => point.mag || point.limiting_mag
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
          let upperLimitsX = [];
          let upperLimitsY = [];
          for (let i = 0; i < indices.length; i += 1) {
            if (groupedPhotometry[key][indices[i]].mag !== null) {
              detectionsX.push(x[i]);
              detectionsY.push(y[i]);
            } else {
              upperLimitsX.push(x[i]);
              upperLimitsY.push(y[i]);
            }
          }

          if (phaseValue === 2) {
            detectionsX = detectionsX.concat(detectionsX.map((p) => p + 1));
            detectionsY = detectionsY.concat(detectionsY);
            upperLimitsX = upperLimitsX.concat(upperLimitsX.map((p) => p + 1));
            upperLimitsY = upperLimitsY.concat(upperLimitsY);
          }

          const detectionsTrace = {
            x: detectionsX,
            y: detectionsY,
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
          };

          const upperLimitsTrace = {
            x: upperLimitsX,
            y: upperLimitsY,
            mode: "markers",
            type: "scatter",
            name: key,
            legendgroup: key,
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

  const createLayouts = (
    plotType,
    photStats_value,
    dm_value,
    dm_flux_value
  ) => {
    const newLayouts = {};
    if (plotType === "mag" || plotType === "flux") {
      newLayouts.xaxis = {
        title: "MJD",
        side: "top",
        range: [...photStats_value.mjd.range],
        tickformat: "digits",
        ...BASE_LAYOUT,
      };
      newLayouts.xaxis2 = {
        title: "Days Ago",
        range: [...photStats_value.days_ago.range],
        overlaying: "x",
        side: "bottom",
        showgrid: false,
        tickformat: "digits",
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
      if (dm_flux_value && photStats_value) {
        newLayouts.yaxis2 = {
          title: "Flux",
          range: [
            photStats_value.flux.range[0] - dm_flux_value,
            photStats_value.flux.range[1] - dm_flux_value,
          ],
          overlaying: "y",
          side: "right",
          showgrid: false,
          ...BASE_LAYOUT,
        };
      }
    }
    return newLayouts;
  };

  useEffect(() => {
    const [newPhotometry, newPhotStats] = preparePhotometry(photometry);
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
          phase
        );
        setPlotData(traces);
      }

      const newLayouts = createLayouts(
        tabToPlotType(tabIndex),
        photStats,
        dm,
        dm_flux
      );
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
        phase
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
    setTabIndex(newValue);
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

      <div style={{ width: "100%", height: "60vh", overflowX: "scroll" }}>
        <Plot
          data={plotData}
          layout={{
            ...layouts,
            legend: {
              orientation: mode === "desktop" ? "v" : "h",
              yanchor: "top",
              y: mode === "desktop" ? 1 : -0.15,
              x: mode === "desktop" ? 1.15 : 0,
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
        />
      </div>
      <div
        style={{
          display: "grid",
          gridAutoFlow: "row",
          gridTemplateColumns: "repeat(3, 1fr)",
          rowGap: "0.5rem",
          columnGap: "2rem",
          width: "100%",
          padding: "0.5rem",
        }}
      >
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
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            alignItems: "left",
            gap: 0,
            width: "100%",
            gridColumn: "span 2",
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
                style={{ width: "7rem", marginTop: 0, marginBottom: 0 }}
                size="small"
              />
            )}
          </div>
        </div>
        {tabIndex === 2 && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "flex-start",
              alignItems: "left",
              gap: 0,
              width: "100%",
              gridColumn: "span 3",
            }}
          >
            <Typography id="input-slider">Period (days)</Typography>
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
                style={{ width: "10rem", marginTop: 0, marginBottom: 0 }}
                size="small"
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
              <PeriodAnnotationDialog obj_id={obj_id} period={period} />
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
              gridColumn: "span 2",
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
                style={{ width: "7rem", marginTop: 0, marginBottom: 0 }}
                size="small"
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
            <Typography id="input-slider">Phase</Typography>
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
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

PhotometryPlotV2.propTypes = {
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

PhotometryPlotV2.defaultProps = {
  dm: null,
  annotations: [],
  mode: "desktop",
};

export default PhotometryPlotV2;
