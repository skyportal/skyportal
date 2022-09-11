import React from "react";
import PropTypes from "prop-types";
import embed from "vega-embed";
import { isMobileOnly } from "react-device-detect";

const jdNow = Date.now() / 86400000.0 + 40587 + 2400000.5;

const spec = (values, colorScale) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  width: isMobileOnly ? 250 : 500,
  height: isMobileOnly ? 150 : 250,
  data: {
    values,
    format: {
      type: "json",
    },
  },
  background: "transparent",
  layer: [
    {
      selection: {
        filterMags: {
          type: "multi",
          fields: ["filter"],
          bind: "legend",
        },
        grid: {
          type: "interval",
          bind: "scales",
        },
      },
      mark: {
        type: "point",
        shape: "circle",
        filled: "true",
        size: 15,
      },
      transform: [
        {
          calculate:
            "join([format(datum.mag, '.2f'), ' ± ', format(datum.magerr, '.2f')], '')",
          as: "magAndErr",
        },
        { calculate: `${jdNow} - datum.hjd`, as: "daysAgo" },
      ],
      encoding: {
        x: {
          field: "daysAgo",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
          axis: {
            title: "days ago",
          },
        },
        y: {
          field: "mag",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
          axis: {
            title: "mag",
          },
        },
        color: {
          field: "filter",
          type: "nominal",
          scale: colorScale,
        },
        tooltip: [
          { field: "magAndErr", title: "mag", type: "nominal" },
          { field: "filter", type: "ordinal" },
          { field: "hjd", type: "quantitative" },
          { field: "daysAgo", type: "quantitative" },
          { field: "catflags", type: "ordinal" },
          { field: "programid", type: "ordinal" },
          { field: "chi", type: "quantitative" },
          { field: "sharp", type: "quantitative" },
        ],
        opacity: {
          condition: { selection: "filterMags", value: 1 },
          value: 0,
        },
      },
    },

    // Render error bars
    {
      selection: {
        filterErrBars: {
          type: "multi",
          fields: ["filter"],
          bind: "legend",
        },
      },
      transform: [
        { filter: "datum.mag != null && datum.magerr != null" },
        { calculate: "datum.mag - datum.magerr", as: "magMin" },
        { calculate: "datum.mag + datum.magerr", as: "magMax" },
        { calculate: `${jdNow} - datum.hjd`, as: "daysAgo" },
      ],
      mark: {
        type: "rule",
        size: 0.5,
      },
      encoding: {
        x: {
          field: "daysAgo",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
          axis: {
            title: "days ago",
          },
        },
        y: {
          field: "magMin",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
        },
        y2: {
          field: "magMax",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
        },
        color: {
          field: "filter",
          type: "nominal",
          scale: colorScale,
          legend: {
            orient: isMobileOnly ? "bottom" : "right",
          },
        },
        opacity: {
          condition: { selection: "filterErrBars", value: 1 },
          value: 0,
        },
      },
    },
  ],
});

const VegaPlot = React.memo((props) => {
  const { data, colorScale } = props;

  return (
    <div
      ref={(node) => {
        if (node) {
          embed(node, spec(data, colorScale), {
            actions: false,
          });
        }
      }}
    />
  );
});

VegaPlot.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      catflags: PropTypes.number,
      chi: PropTypes.number,
      dec: PropTypes.number,
      expid: PropTypes.number,
      filter: PropTypes.number,
      hjd: PropTypes.number,
      mag: PropTypes.number,
      magerr: PropTypes.number,
      programid: PropTypes.number,
      ra: PropTypes.number,
      sharp: PropTypes.number,
      uexpid: PropTypes.number,
    })
  ).isRequired,
  colorScale: PropTypes.shape({
    domain: PropTypes.arrayOf(PropTypes.number),
    range: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
};

VegaPlot.displayName = "VegaPlot";

export default VegaPlot;
