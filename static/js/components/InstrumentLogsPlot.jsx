import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import { ModifiedJulianDateNow, BASE_LAYOUT } from "./PhotometryPlot";

const Plot = createPlotlyComponent(Plotly);

// we want a color map, that maps the logtype to a color
// we can use the int to map to a color
const LOGTYPE_TO_COLOR = {
  Message_robo: "blue",
  Power_robo: "red",
  Weather_robo: "green",
  Data_robo: "orange",
  VIC_robo: "purple",
  TCS_robo: "brown",
  SPEC_robo: "pink",
  Queue_robo: "gray",
  FITS_robo: "cyan",
  Filter_robo: "magenta",
  Control: "yellow",
  Motion_robo: "black",
  BestFocus: "darkblue",
  reset_server: "darkred",
  Other: "darkgreen",
};

const checkLogtype = (logtype) => {
  let type = Object.keys(LOGTYPE_TO_COLOR).map((key) => {
    if (logtype.includes(key)) {
      return key;
    }
    return undefined;
  });
  // check if there is anything that is not undefined
  if (type.some((element) => element !== undefined)) {
    [type] = type.filter((element) => element !== undefined);
  } else {
    type = "Other";
  }

  return type;
};

const InstrumentLogsPlot = ({ instrument_logs }) => {
  const [logStats, setLogStats] = useState(null);
  const [data, setData] = useState(null);
  const [plotData, setPlotData] = useState([]);
  const [layouts, setLayouts] = useState({});

  const [layoutReset, setLayoutReset] = useState(false);

  const prepareInstrumentLogs = (instrumentLogs) => {
    if (instrumentLogs === null) {
      return null;
    }
    return instrumentLogs.map((log) => log?.log?.logs || []).flat();
  };

  const getLogStats = (instrumentLogs) => {
    if (instrumentLogs !== null) {
      const minMJD = Math.min(...instrumentLogs.map((entry) => entry.mjd));
      const maxMJD = Math.max(...instrumentLogs.map((entry) => entry.mjd));

      const now = ModifiedJulianDateNow();
      // days ago is now - mjd, so its a reversed axis
      const daysAgoMin = now - maxMJD;
      const daysAgoMax = now - minMJD;

      return {
        minMJD,
        maxMJD,
        daysAgoMin,
        daysAgoMax,
      };
    }
    return null;
  };

  const createTraces = (instrumentLogs, stats) => {
    if (instrumentLogs !== null) {
      const traces = {};
      Object.keys(LOGTYPE_TO_COLOR).forEach((key) => {
        traces[key] = {
          x: [],
          y: [],
          text: [],
          type: "scatter",
          mode: "markers",
          marker: {
            color: LOGTYPE_TO_COLOR[key],
            size: 8,
          },
          name: key,
        };
      });

      instrumentLogs.forEach((entry) => {
        const logtype = checkLogtype(entry.type);
        traces[logtype].x.push(entry.mjd);
        traces[logtype].y.push(logtype);
        traces[logtype].text.push(entry.message);
      });

      // we create a secondary xaxis that will be on top of the plot, showing 'Days ago'
      const secondaryAxisX = {
        x: [stats.daysAgoMax, stats.daysAgoMin],
        y: ["Message_robo", "Message_robo"],
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

      return Object.keys(traces)
        .map((key) => traces[key])
        .concat(secondaryAxisX);
    }
    return [];
  };

  const createLayouts = (stats) => {
    // compute a 10% margin for time axes
    const margin = (stats ? stats.maxMJD - stats.minMJD : 1) * 0.1;
    return {
      xaxis: {
        title: "MJD",
        range: stats ? [stats.minMJD - margin, stats.maxMJD + margin] : [0, 1],
        side: "top",
        tickformat: ".6~f",
        ...BASE_LAYOUT,
      },
      yaxis: {
        title: "Log Type",
        ...BASE_LAYOUT,
      },
      xaxis2: {
        title: "Days Ago",
        range: stats
          ? [stats.daysAgoMax - margin, stats.daysAgoMin + margin]
          : [1, 0],
        overlaying: "x",
        side: "bottom",
        showgrid: false,
        tickformat: ".6~f",
        ...BASE_LAYOUT,
      },
      showlegend: false,
      autosize: true,
      automargin: true,
    };
  };

  useEffect(() => {
    const newData = prepareInstrumentLogs(instrument_logs);
    const stats = getLogStats(newData);
    setData(newData);
    setLogStats(stats);
  }, [instrument_logs]);

  useEffect(() => {
    if (logStats !== null && data !== null) {
      if (!layoutReset) {
        const traces = createTraces(data, logStats);
        setPlotData(traces);
      }
      setLayouts(createLayouts(logStats));
    }
  }, [data, layoutReset]);

  return (
    <div style={{ width: "100%", height: "60vh", overflowX: "scroll" }}>
      <Plot
        data={plotData}
        layout={{
          ...layouts,
          showlegend: false,
          autosize: true,
          automargin: true,
        }}
        config={{
          displaylogo: false,
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
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
};

InstrumentLogsPlot.propTypes = {
  instrument_logs: PropTypes.arrayOf(
    PropTypes.shape({
      instrument_id: PropTypes.number,
      log: PropTypes.shape({
        logs: PropTypes.arrayOf(
          PropTypes.shape({
            type: PropTypes.string,
            message: PropTypes.string,
            mjd: PropTypes.number,
          }),
        ),
      }),
    }),
  ).isRequired,
};

export default InstrumentLogsPlot;
