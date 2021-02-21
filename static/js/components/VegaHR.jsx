import React from "react";
import PropTypes from "prop-types";
import embed from "vega-embed";

const spec = (magG, color, width = 300, height = 300) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  width,
  height,
  padding: 5,
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
    filled: "true",
    from: { data: "count" },
    update: {
      fill: { scale: "color", field: "count" },
    },
    tooltip: true,
  },
});

const VegaHR = React.memo((props) => {
  const { magG, color, width, height } = props;
  return (
    <div
      ref={(node) => {
        if (node) {
          embed(node, spec(magG, color, width, height), {
            actions: false,
          });
        }
      }}
    />
  );
});

VegaHR.propTypes = {
  magG: PropTypes.number.isRequired,
  color: PropTypes.number.isRequired,
  width: PropTypes.number,
  height: PropTypes.number,
};

VegaHR.defaultProps = {
  width: 250,
  height: 250,
};

VegaHR.displayName = "VegaHR";

export default VegaHR;
