import React from "react";
import PropTypes from "prop-types";
import embed from "vega-embed";
import { isMobileOnly } from "react-device-detect";

const spec = (url) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  data: {
    url,
    format: {
      type: "json",
      property: "data", // where on the JSON does the data live
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
            "join([format(datum.mag, '.2f'), ' ± ', format(datum.magerr, '.2f'), ' (', datum.magsys, ')'], '')",
          as: "magAndErr",
        },
      ],
      encoding: {
        x: {
          field: "phase",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: false,
          },
          axis: {
            title: "Phase",
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
        },
        tooltip: [
          { field: "magAndErr", title: "mag", type: "nominal" },
          { field: "filter", type: "ordinal" },
          { field: "mjd", type: "quantitative" },
          { field: "phase", type: "quantitative" },
          { field: "limiting_mag", type: "quantitative", format: ".2f" },
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
      ],
      mark: {
        type: "rule",
        size: 0.5,
      },
      encoding: {
        x: {
          field: "phase",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: false,
          },
          axis: {
            title: "Phase",
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

    // Render limiting mags
    {
      transform: [{ filter: "datum.mag == null" }],
      selection: {
        filterLimitingMags: {
          type: "multi",
          fields: ["filter"],
          bind: "legend",
        },
      },
      mark: {
        type: "point",
        shape: "triangle-down",
      },
      encoding: {
        x: {
          field: "phase",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: false,
          },
          axis: {
            title: "Phase",
          },
        },
        y: {
          field: "limiting_mag",
          type: "quantitative",
        },
        color: {
          field: "filter",
          type: "nominal",
        },
        opacity: {
          condition: { selection: "filterLimitingMags", value: 0.3 },
          value: 0,
        },
      },
    },
  ],
});

const VegaFoldedPlot = React.memo((props) => {
  const { dataUrl } = props;
  return (
    <div
      ref={(node) => {
        if (node) {
          embed(node, spec(dataUrl), {
            actions: false,
          });
        }
      }}
    />
  );
});

VegaFoldedPlot.propTypes = {
  dataUrl: PropTypes.string.isRequired,
};

VegaFoldedPlot.displayName = "VegaFoldedPlot";

export default VegaFoldedPlot;
