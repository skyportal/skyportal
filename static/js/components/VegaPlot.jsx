import React from "react";
import { isMobileOnly } from "react-device-detect";
import PropTypes from "prop-types";
import embed from "vega-embed";
import { useTheme } from "@material-ui/core/styles";

const mjdNow = Date.now() / 86400000.0 + 40587.0;

const spec = (url, colorScale, titleFontSize, labelFontSize) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v5.2.0.json",
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
        { calculate: `${mjdNow} - datum.mjd`, as: "daysAgo" },
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
            titleFontSize,
            labelFontSize,
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
            titleFontSize,
            labelFontSize,
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
          { field: "mjd", type: "quantitative" },
          { field: "daysAgo", type: "quantitative" },
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
        { calculate: `${mjdNow} - datum.mjd`, as: "daysAgo" },
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
            titleFontSize,
            labelFontSize,
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
            titleFontSize,
            labelFontSize,
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
      transform: [
        { filter: "datum.mag == null" },
        { calculate: `${mjdNow} - datum.mjd`, as: "daysAgo" },
      ],
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
          field: "daysAgo",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
          axis: {
            title: "days ago",
            titleFontSize,
            labelFontSize,
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

const VegaPlot = React.memo((props) => {
  const { dataUrl, colorScale } = props;
  const theme = useTheme();
  return (
    <div
      ref={(node) => {
        if (node) {
          embed(
            node,
            spec(
              dataUrl,
              colorScale,
              theme.plotFontSizes.titleFontSize,
              theme.plotFontSizes.labelFontSize
            ),
            {
              actions: false,
            }
          );
        }
      }}
    />
  );
});

VegaPlot.propTypes = {
  dataUrl: PropTypes.string.isRequired,
  colorScale: PropTypes.shape({
    domain: PropTypes.arrayOf(PropTypes.string),
    range: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
};

VegaPlot.displayName = "VegaPlot";

export default VegaPlot;
