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

const PhotometryPlotV2 = ({
  obj_id,
  dm,
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
  const [smoothing, setSmoothing] = useState(0);
  const [phase, setPhase] = useState(1);
  const [photStats, setPhotStats] = useState(null);
  const [layouts, setLayouts] = useState({});

  const [dialogOpen, setDialogOpen] = useState(false);

  const filter2color = useSelector(
    (state) => state.config.bandpassesColors || {}
  );

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
        point.flux = 10 ** (-0.4 * (point.mag - 25));
        point.fluxerr = (point.magerr / (2.5 / Math.log(10))) * point.flux;
      } else {
        point.flux = 10 ** (-0.4 * (point.limiting_mag - 25));
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
            legendgroup: key,
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

          let secondaryAxisY = {};
          if (dm && photStats) {
            if (plotType === "mag") {
              secondaryAxisY = {
                x: [photStats.mjd.min, photStats.mjd.max],
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
          }

          if (detections.length > 0) {
            upperLimitsTrace.showlegend = false;
          } else {
            detectionsTrace.showlegend = false;
          }

          if (dm) {
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
    const [newPhotometry, newPhotStats] = preparePhotometry(photometry);
    const groupedPhotometry = groupPhotometry(newPhotometry);
    setPhotStats(newPhotStats);
    setData(groupedPhotometry);
  }, [photometry]);

  const baseLayout = {
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

  useEffect(() => {
    if (data !== null && filter2color !== null && photStats !== null) {
      const traces = createTraces(
        data,
        tabToPlotType(tabIndex),
        period,
        smoothing,
        phase
      );
      const newLayouts = {
        yaxis: {
          title: "AB Mag",
          range: [...photStats.mag.range],
          ...baseLayout,
        },
        xaxis: {
          title: "MJD",
          side: "top",
          range: [...photStats.mjd.range],
          tickformat: "digits",
          ...baseLayout,
        },
        xaxis2: {
          title: "Days Ago",
          range: [...photStats.days_ago.range],
          overlaying: "x",
          side: "bottom",
          showgrid: false,
          tickformat: "digits",
          ...baseLayout,
        },
      };
      if (dm && photStats) {
        newLayouts.yaxis2 = {
          title: "m - DM",
          range: [photStats.mag.range[0] - dm, photStats.mag.range[1] - dm],
          overlaying: "y",
          side: "right",
          showgrid: false,
          ...baseLayout,
        };
      }
      setLayouts(newLayouts);
      setPlotData(traces);
    }
  }, [data, filter2color, photStats]);

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
    const traces = createTraces(
      data,
      tabToPlotType(newValue),
      period,
      smoothing,
      phase
    );
    if (newValue === 0) {
      const newLayouts = {
        yaxis: {
          title: "AB Mag",
          range: [...photStats.mag.range],
          ...baseLayout,
        },
        xaxis: {
          title: "MJD",
          side: "top",
          range: [...photStats.mjd.range],
          tickformat: "digits",
          ...baseLayout,
        },
        xaxis2: {
          title: "Days Ago",
          range: [...photStats.days_ago.range],
          overlaying: "x",
          side: "bottom",
          showgrid: false,
          tickformat: "digits",
          ...baseLayout,
        },
      };
      if (dm && photStats) {
        newLayouts.yaxis2 = {
          title: "m - DM",
          range: [photStats.mag.range[0] - dm, photStats.mag.range[1] - dm],
          overlaying: "y",
          side: "right",
          showgrid: false,
          ...baseLayout,
        };
      }
      setLayouts(newLayouts);
    }
    setPlotData(traces);
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

      {tabIndex === 0 && (
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
              // legend: {
              //   x: 1,
              //   y: 1,
              // },
              autosize: true,
              automargin: true,
              // margin: {
              //   //l: 60,
              //   r: 400,
              //   //b: 50,
              //   //t: 30,
              // },
            }}
            config={{
              displaylogo: false,
              // the native autoScale2d and resetScale2d buttons are not working
              // as they are not resetting to the specified ranges
              // so, we remove them and add our own
              modeBarButtonsToRemove: ["autoScale2d", "resetScale2d"],
              modeBarButtonsToAdd: [
                {
                  name: "Reset",
                  icon: Plotly.Icons.home,
                  click: () => {
                    // we basically just re-set the layout again to refresh the plot
                    setLayouts({
                      ...layouts,
                      xaxis: {
                        ...layouts.xaxis,
                        range: [...photStats.mjd.range],
                      },
                      yaxis: {
                        ...layouts.yaxis,
                        range: [...photStats.mag.range],
                      },
                      xaxis2: {
                        ...layouts.xaxis2,
                        range: [...photStats.days_ago.range],
                      },
                      yaxis2: {
                        ...layouts.yaxis2,
                        range: [
                          photStats.mag.range[0] - dm,
                          photStats.mag.range[1] - dm,
                        ],
                      },
                    });
                  },
                },
              ],
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
      </div>
    </div>
  );
};

PhotometryPlotV2.propTypes = {
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

PhotometryPlotV2.defaultProps = {
  annotations: [],
  mode: "desktop",
};

export default PhotometryPlotV2;
