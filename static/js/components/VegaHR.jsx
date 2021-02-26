import React from "react";
import PropTypes from "prop-types";
import embed from "vega-embed";

const spec = (data, width = 200, height = 200) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  width,
  height,
  padding: 5,
  layer: [
    // draw the GAIA data for main sequence etc.
    {
      data: {
        url: "static/HR_density.json",
        property: "data",
        format: {
          type: "json",
        },
      },
      background: "transparent",
      encoding: {
        x: {
          field: "color",
          type: "quantitative",
          axis: {
            title: "Bp-Rp",
            grid: false,
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
            title: "mag G",
            grid: false,
          },
        },
        color: {
          name: "count",
          field: "count",
          type: "quantitative",
          legend: null,
        },
      },
      mark: {
        type: "point",
        shape: "circle",
        size: 2,
        filled: "true",
        from: { data: "count" },
        update: {
          fill: { scale: "color", field: "count" },
        },
        tooltip: true,
      },
    },

    // make the point for the current object
    {
      data: { values: data },
      selection: {
        filterPoints: {
          type: "multi",
          fields: ["origin"],
          bind: "legend",
        },
      },
      encoding: {
        x: {
          field: "color",
          type: "quantitative",
          axis: {
            title: "Bp-Rp",
            grid: false,
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
            title: "mag G",
            grid: false,
          },
        },
        color: {
          field: "origin",
          type: "nominal",
        },
        opacity: {
          condition: { selection: "filterPoints", value: 1 },
          value: 0.2,
        },
      },
      mark: {
        type: "point",
        shape: "circle",
        size: 50,
        filled: true,
        tooltip: true,
      },
    },

    // make the cross around the point
    {
      data: { values: data },
      selection: {
        filterCrosses: {
          type: "multi",
          fields: ["origin"],
          bind: "legend",
        },
      },
      encoding: {
        x: {
          field: "color",
          type: "quantitative",
          axis: {
            title: "Bp-Rp",
            grid: false,
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
            title: "mag G",
            grid: false,
          },
        },
        color: {
          field: "origin",
          type: "nominal",
          legend: null,
        },
        opacity: {
          condition: { selection: "filterCrosses", value: 1 },
          value: 0.2,
        },
      },
      mark: {
        type: "point",
        shape: "cross",
        size: 300,
        angle: 45,
        filled: false,
        tooltip: true,
      },
    },
  ],
});

const VegaHR = React.memo((props) => {
  const { data, width, height } = props;
  return (
    <div
      ref={(node) => {
        if (node) {
          embed(node, spec(data, width, height), {
            actions: false,
          });
        }
      }}
    />
  );
});

VegaHR.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      mag: PropTypes.number.isRequired,
      color: PropTypes.number.isRequired,
      origin: PropTypes.string.isRequired,
    })
  ).isRequired,
  width: PropTypes.number,
  height: PropTypes.number,
};

VegaHR.defaultProps = {
  width: 200,
  height: 200,
};

VegaHR.displayName = "VegaHR";

export default VegaHR;
