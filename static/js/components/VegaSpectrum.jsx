import React from "react";
import PropTypes from "prop-types";
import embed from "vega-embed";
import { useTheme } from "@mui/material/styles";

const spec = (
  url,
  width,
  height,
  legendOrient,
  titleFontSize,
  labelFontSize
) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v5.2.0.json",
  data: {
    url,
    format: {
      type: "json",
      property: "data.spectra", // where on the JSON does the data live
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
        titleFontSize,
        labelFontSize,
      },
    },
    y: {
      field: "fluxes",
      type: "quantitative",
      axis: {
        title: "flux [normalized]",
        format: ".2g",
        titleFontSize,
        labelFontSize,
      },
    },
    color: {
      field: "observed_at",
      type: "nominal",
      legend: {
        orient: legendOrient,
        titleFontSize,
        labelFontSize,
      },
    },
  },
  width,
  height,
  background: "transparent",
});

const VegaSpectrum = React.memo((props) => {
  const { dataUrl, width, height, legendOrient } = props;
  const theme = useTheme();
  return (
    <div
      ref={(node) => {
        if (node) {
          embed(
            node,
            spec(
              dataUrl,
              width,
              height,
              legendOrient,
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

VegaSpectrum.propTypes = {
  dataUrl: PropTypes.string.isRequired,
  width: PropTypes.number,
  height: PropTypes.number,
  legendOrient: PropTypes.string,
};

VegaSpectrum.defaultProps = {
  width: 400,
  height: 200,
  legendOrient: "right",
};

VegaSpectrum.displayName = "VegaSpectrum";

export default VegaSpectrum;
