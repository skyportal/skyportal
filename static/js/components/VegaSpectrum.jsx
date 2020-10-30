import React from "react";
import PropTypes from "prop-types";
import embed from "vega-embed";

const spec = (url) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  data: {
    url,
    format: {
      type: "json",
      property: "data", // where on the JSON does the data live
    },
  },
  transform: [
    {
      flatten: ["wavelengths", "fluxes"],
    },
  ],
  scales: [
    {
      name: "wavelengths",
      type: "point",
      range: "width",
      domain: { field: "wavelengths" },
    },
    {
      name: "fluxes",
      type: "linear",
      range: "height",
      nice: true,
      zero: true,
      domain: { data: "table", field: "fluxes" },
    },
    {
      name: "color",
      type: "ordinal",
      range: "category",
      domain: { field: "observed_at" },
    },
  ],
  mark: {
    type: "line",
    interpolate: "linear",
  },
  encoding: {
    x: {
      field: "wavelengths",
      type: "quantitative",
      axis: {
        title: "wavelength [Angstrom]",
      },
    },
    y: {
      field: "fluxes",
      type: "quantitative",
      axis: {
        title: "flux [normalized]",
        format: ".2g",
      },
    },
    color: {
      field: "observed_at",
      type: "nominal",
    },
  },
  width: 400,
  height: 200,
  background: "transparent",
});

const VegaSpectrum = React.memo((props) => {
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

VegaSpectrum.propTypes = {
  dataUrl: PropTypes.string.isRequired,
};

VegaSpectrum.displayName = "VegaSpectrum";

export default VegaSpectrum;
