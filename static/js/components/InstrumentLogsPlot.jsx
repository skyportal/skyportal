import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

const Plot = createPlotlyComponent(Plotly);

const LOGTYPE_TO_INT = {
  Message_robo: 1,
  Power_robo: 2,
  Weather_robo: 3,
  Data_robo: 4,
  VIC_robo: 5,
  TCS_robo: 6,
  SPEC_robo: 7,
  Queue_robo: 8,
  FITS_robo: 9,
  Filter_robo: 10,
  Control: 11,
  Motion_robo: 12,
  BestFocus: 13,
  reset_server: 14,
  Other: 0,
};

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
  let type = Object.keys(LOGTYPE_TO_INT).map((key) => {
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
  const [plotData, setPlotData] = useState([]);

  const createTraces = (instrumentLogs) => {
    if (instrumentLogs !== null) {
      // the instrumentLogs is a list of instrument logs
      // each instrument logs has a log key, with a logs key. This logs key is a list of log entries
      // each entry has a type, message and mjd
      // we can flatten the instrument logs' log.logs into a single list of log entries
      // and then create a trace for each logtype
      const logEntries = instrumentLogs
        .map((log) => log?.log?.logs || [])
        .flat();

      const traces = {};
      Object.keys(LOGTYPE_TO_INT).forEach((key) => {
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
          name: `${LOGTYPE_TO_INT[key]}: ${key}`,
        };
      });

      logEntries.forEach((entry) => {
        const logtype = checkLogtype(entry.type);
        traces[logtype].x.push(entry.mjd);
        traces[logtype].y.push(LOGTYPE_TO_INT[logtype]);
        traces[logtype].text.push(entry.message);
      });

      return Object.keys(traces).map((key) => traces[key]);
    }
    return [];
  };

  useEffect(() => {
    const traces = createTraces(instrument_logs);
    setPlotData(traces);
  }, [instrument_logs]);

  return (
    <div style={{ width: "100%", height: "60vh", overflowX: "scroll" }}>
      <Plot
        data={plotData}
        layout={{
          xaxis: {
            title: "MJD",
          },
          yaxis: {
            title: "Log Type",
          },
          showlegend: true,
          autosize: true,
        }}
        config={{
          displaylogo: false,
        }}
        useResizeHandler
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
          })
        ),
      }),
    })
  ).isRequired,
};

export default InstrumentLogsPlot;
