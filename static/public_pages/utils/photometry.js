/* global Plotly */
const baseLayout = {
  zeroline: false,
  automargin: true,
  showline: true,
  autorange: "reversed",
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

/* eslint-disable */
function getHoverText(point) {
  return (
    `MJD: ${point.mjd.toFixed(6)}<br>` +
    (point.mag !== null ? `Mag: ${point.mag.toFixed(4)}<br>` : "") +
    (point.magerr !== null ? `Magerr: ${point.magerr.toFixed(4)}<br>` : "") +
    (point.limiting_mag !== null
      ? `Limiting Mag: ${point.limiting_mag.toFixed(4)}<br>`
      : "") +
    `Filter: ${point.filter}<br>Instrument: ${point.instrument_name}`
  );
}

function getTrace(data, isDetection, key, color, isMobile) {
  const now = new Date().getTime() / 86400000 + 40587;
  const rgba = (rgb, alpha) => `rgba(${rgb[0]},${rgb[1]},${rgb[2]}, ${alpha})`;
  const dataType = isDetection ? "detections" : "upperLimits";
  return {
    dataType,
    x: data.map((point) => now - point.mjd),
    y: data.map((point) => (isDetection ? point.mag : point.limiting_mag)),
    ...(isDetection
      ? {
          error_y: {
            type: "data",
            array: data.map((point) => point.magerr),
            visible: true,
            color: rgba(color, 0.5),
            width: 1,
            thickness: 2,
          },
        }
      : {}),
    text: data.map((point) => getHoverText(point)),
    mode: "markers",
    type: "scatter",
    name: key + (isDetection ? "" : " (UL)"),
    legendgroup: key + dataType,
    marker: {
      line: {
        width: 1,
        color: rgba(color, 1),
      },
      color: isDetection ? rgba(color, 0.3) : rgba(color, 0.1),
      size: isMobile ? 6 : 9,
      symbol: isDetection ? "circle" : "triangle-down",
    },
    hoverlabel: {
      bgcolor: "white",
      font: { size: 14 },
      align: "left",
    },
    hovertemplate: "%{text}<extra></extra>",
  };
}

function getLayoutGraphPart() {
  return {
    autosize: true,
    xaxis: {
      title: {
        text: "Days Ago",
      },
      overlaying: "x",
      side: "bottom",
      tickformat: ".6~f",
      ...baseLayout,
    },
    yaxis: {
      title: {
        text: "AB Mag",
      },
      ...baseLayout,
    },
    margin: {
      b: 75,
      l: 70,
      pad: 0,
      r: 30,
      t: 80,
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
    showlegend: true,
    hovermode: "closest",
  };
}

function getLayoutLegendPart(isMobile) {
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

function getLayout(isMobile) {
  return {
    ...getLayoutGraphPart(),
    ...getLayoutLegendPart(isMobile),
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
        icon: Plotly.Icons.home,
        click: () => {
          Plotly.relayout(
            document.getElementsByClassName("plotly")[0].parentElement,
            getLayoutGraphPart(),
          );
        },
      },
    ],
  };
}

function getGroupedPhotometry(photometry) {
  return photometry.reduce((acc, point) => {
    const key = `${point.instrument_name}/${point.filter}${
      point.origin !== "None" ? `/${point.origin}` : ""
    }`;
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(point);
    return acc;
  }, {});
}

function adjustLegend(isMobile) {
  const plotDiv = document.getElementsByClassName("plotly")[0].parentElement;
  Plotly.relayout(plotDiv, getLayoutLegendPart(isMobile));
  Plotly.restyle(plotDiv, { "marker.size": isMobile ? 6 : 9 });
}

/* eslint-disable no-unused-vars */
function plotLc(photometry_data, div_id, filters_used_mapper, isMobile) {
  const photometry = JSON.parse(photometry_data);
  const mapper = JSON.parse(filters_used_mapper);
  const plotData = [];

  const groupedPhotometry = getGroupedPhotometry(photometry);
  Object.keys(groupedPhotometry).forEach((key) => {
    const photometry = groupedPhotometry[key];
    const color = mapper[photometry[0].filter] || [0, 0, 0];
    const { detections, upperLimits } = photometry.reduce(
      (acc, point) => {
        point.mag !== null
          ? acc.detections.push(point)
          : acc.upperLimits.push(point);
        return acc;
      },
      { detections: [], upperLimits: [] },
    );
    const detectionsTrace = getTrace(detections, true, key, color, isMobile);
    const upperLimitsTrace = getTrace(upperLimits, false, key, color, isMobile);
    plotData.push(detectionsTrace, upperLimitsTrace);
  });
  Plotly.newPlot(
    document.getElementById(div_id),
    plotData,
    getLayout(isMobile),
    getConfig(),
  );
}
