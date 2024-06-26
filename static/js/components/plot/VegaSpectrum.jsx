import React, { Suspense, useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import PropTypes from "prop-types";
import embed from "vega-embed";
import { useTheme } from "@mui/material/styles";
import * as spectraActions from "../../ducks/spectra";

const spec = (
  dataUrl,
  values,
  width,
  height,
  legendOrient,
  titleFontSize,
  labelFontSize,
) => {
  const specJSON = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.2.0.json",
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
  };

  if (dataUrl) {
    specJSON.data = {
      url: dataUrl,
      format: {
        type: "json",
        property: "data", // where on the JSON does the data live
      },
    };
  } else {
    specJSON.data = {
      values,
    };
  }
  return specJSON;
};

const VegaSpectrumMemo = React.memo(
  (props) => {
    const { dataUrl, values, width, height, legendOrient } = props;
    const theme = useTheme();

    return (
      <div
        ref={(node) => {
          if (node) {
            embed(
              node,
              spec(
                dataUrl,
                values,
                width,
                height,
                legendOrient,
                theme.plotFontSizes.titleFontSize,
                theme.plotFontSizes.labelFontSize,
              ),
              {
                actions: false,
              },
            );
          }
        }}
      />
    );
  },
  (prevProps, nextProps) => {
    const keys = Object.keys(nextProps);
    for (let i = 0; i < keys.length; i += 1) {
      const key = keys[i];
      if (key === "values") {
        // we simply compare the length of the values array
        if (prevProps.values.length !== nextProps.values.length) {
          return false;
        }
      } else if (prevProps[key] !== nextProps[key]) {
        return false;
      }
    }
    return true;
  },
);

VegaSpectrumMemo.displayName = "VegaSpectrumMemo";

VegaSpectrumMemo.propTypes = {
  dataUrl: PropTypes.string,
  values: PropTypes.arrayOf(PropTypes.object), // eslint-disable-line react/forbid-prop-types
  width: PropTypes.number,
  height: PropTypes.number,
  legendOrient: PropTypes.string,
};

VegaSpectrumMemo.defaultProps = {
  dataUrl: null,
  values: null,
  width: 400,
  height: 200,
  legendOrient: "right",
};

const VegaSpectrum = (props) => {
  const { sourceId, width, height, legendOrient, normalization } = props;
  const theme = useTheme();
  const dispatch = useDispatch();
  const spectra = useSelector((state) => state.spectra[sourceId]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchSpectra() {
      if (!spectra && !loading) {
        setLoading(true);
        await dispatch(
          spectraActions.fetchSourceSpectra(sourceId, normalization),
        );
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
      <VegaSpectrumMemo
        values={spectra}
        width={width}
        height={height}
        legendOrient={legendOrient}
        titleFontSize={theme.plotFontSizes.titleFontSize}
        labelFontSize={theme.plotFontSizes.labelFontSize}
      />
    </Suspense>
  );
};

VegaSpectrum.propTypes = {
  sourceId: PropTypes.string.isRequired,
  width: PropTypes.number,
  height: PropTypes.number,
  legendOrient: PropTypes.string,
  normalization: PropTypes.string,
};

VegaSpectrum.defaultProps = {
  width: 400,
  height: 200,
  legendOrient: "right",
  normalization: "median",
};

export default VegaSpectrum;
