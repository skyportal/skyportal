import { useEffect, useState } from "react";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import { BASE_LAYOUT, LOGTYPE_TO_COLOR, mjdnow } from "../../utils";

const Plot = createPlotlyComponent(Plotly);

const checkLogtype = (logtype: string): string => {
  let type: any = Object.keys(LOGTYPE_TO_COLOR).map((key) => {
    if (logtype.includes(key)) {
      return key;
    }
    return undefined;
  });
  if (type.some((element: any) => element !== undefined)) {
    [type] = type.filter((element: any) => element !== undefined);
  } else {
    type = "Other";
  }

  return type;
};

interface InstrumentLog {
  instrument_id?: number;
  log?: {
    logs?: {
      type?: string;
      message?: string;
      mjd?: number;
    }[];
  };
}

interface InstrumentLogsPlotProps {
  instrument_logs: InstrumentLog[];
}

const InstrumentLogsPlot = ({ instrument_logs }: InstrumentLogsPlotProps) => {
  const [logStats, setLogStats] = useState<any>(null);
  const [data, setData] = useState<any>(null);
  const [plotData, setPlotData] = useState<any[]>([]);
  const [layouts, setLayouts] = useState<any>({});

  const [layoutReset, setLayoutReset] = useState(false);

  const prepareInstrumentLogs = (instrumentLogs: InstrumentLog[] | null) => {
    if (instrumentLogs === null) {
      return null;
    }
    return instrumentLogs.map((log) => log?.log?.logs || []).flat();
  };

  const getLogStats = (instrumentLogs: any[] | null) => {
    if (instrumentLogs !== null) {
      const minMJD = Math.min(...instrumentLogs.map((entry) => entry.mjd));
      const maxMJD = Math.max(...instrumentLogs.map((entry) => entry.mjd));

      const now = mjdnow();
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

  const createTraces = (instrumentLogs: any[] | null, stats: any) => {
    if (instrumentLogs !== null) {
      const traces: any = {};
      Object.keys(LOGTYPE_TO_COLOR).forEach((key) => {
        traces[key] = {
          x: [],
          y: [],
          text: [],
          type: "scatter",
          mode: "markers",
          marker: {
            color: (LOGTYPE_TO_COLOR as any)[key],
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

  const createLayouts = (stats: any) => {
    // compute a 10% margin for time axes
    const margin = (stats ? stats.maxMJD - stats.minMJD : 1) * 0.1;
    return {
      xaxis: {
        title: { text: "MJD" },
        range: stats ? [stats.minMJD - margin, stats.maxMJD + margin] : [0, 1],
        side: "top",
        tickformat: ".6~f",
        ...BASE_LAYOUT,
      },
      yaxis: {
        title: { text: "Log Type" },
        ...BASE_LAYOUT,
        nticks: 20,
      },
      xaxis2: {
        title: { text: "Days Ago" },
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
        config={
          {
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
          } as any
        }
        useResizeHandler
        onDoubleClick={() => setLayoutReset(true)}
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
};

export default InstrumentLogsPlot;
