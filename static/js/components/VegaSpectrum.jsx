import React, { Suspense, useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import PropTypes from "prop-types";
import embed from "vega-embed";
import { useTheme } from "@mui/material/styles";
import * as spectraActions from "../ducks/spectra";

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

const VegaSpectrum = (props) => {
  const { sourceId, dataUrl, width, height, legendOrient } = props;
  const theme = useTheme();
  const dispatch = useDispatch();
  const spectra = useSelector((state) => state.spectra[sourceId]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchSpectra() {
      if (!spectra && !loading) {
        setLoading(true);
        await dispatch(spectraActions.fetchSourceSpectra(sourceId));
        setLoading(false);
      }
    }
    fetchSpectra();
  }, [sourceId, spectra, dispatch]);

  if (loading) {
    return <CircularProgress color="secondary" />;
  }

  if ((!spectra || spectra?.length === 0) && !loading) {
    return <div>No spectra found.</div>;
  }

  return (
    <Suspense
      fallback={
        <div>
          <CircularProgress color="secondary" />
        </div>
      }
    >
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
    </Suspense>
  );
};

VegaSpectrum.propTypes = {
  sourceId: PropTypes.string.isRequired,
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
