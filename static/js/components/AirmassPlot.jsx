import React from "react";
import PropTypes from "prop-types";
import embed from "vega-embed";
import VegaPlot from "./VegaPlot";

function isPromise(promise) {
  return !!promise && typeof promise.then === "function";
}

const airmass_spec = (url, ephemeris) => {
  const fulfilledEphem = isPromise(ephemeris)
    ? ephemeris.then((response) => response.json())
    : ephemeris;

  return {
    $schema: "https://vega.github.io/schema/vega-lite/v4.json",
    background: "transparent",
    data: {
      url,
      format: {
        type: "json",
        property: "data", // where on the JSON does the data live
      },
    },
    layer: [
      {
        mark: { type: "line", clip: true },
        encoding: {
          x: {
            field: "time",
            type: "temporal",
            title: "time (UT)",
            scale: {
              domain: [
                fulfilledEphem.twilight_evening_astronomical_utc,
                fulfilledEphem.twilight_morning_astronomical_utc,
              ],
            },
          },
          y: {
            field: "airmass",
            type: "quantitative",
            scale: {
              reverse: true,
              domain: [1, 4],
            },
          },
        },
      },
    ],
  };
};

const AirmassPlot = React.memo((props) => {
  const { dataUrl, ephemeris } = props;
  return (
    <div
      ref={(node) => {
        if (node) {
          embed(node, airmass_spec(dataUrl, ephemeris), {
            actions: false,
          });
        }
      }}
    />
  );
});

export const AirMassPlotFromPromise = (dataUrl, ephemerisPromise) => {
  const ephemeris = ephemerisPromise.then((response) => response.json());
  return <AirmassPlot dataUrl={dataUrl} ephemeris={ephemeris} />;
};

AirMassPlotFromPromise.propTypes = {
  ...VegaPlot.propTypes,
  ephemerisPromise: PropTypes.shape({
    then: PropTypes.func.isRequired,
    catch: PropTypes.func.isRequired,
  }).isRequired,
};

AirmassPlot.propTypes = {
  ...VegaPlot.propTypes,
  ephemeris: PropTypes.shape({
    twilight_evening_astronomical_utc: PropTypes.string,
    twilight_morning_astronomical_utc: PropTypes.string,
    twilight_evening_nautical_utc: PropTypes.string,
    twilight_morning_nautical_utc: PropTypes.string,
    sunset_utc: PropTypes.string,
    sunrise_utc: PropTypes.string,
  }).isRequired,
};

AirMassPlotFromPromise.dispayName = "AirmassPlotFromPromise";
AirmassPlot.displayName = "AirmassPlot";

export default AirmassPlot;
