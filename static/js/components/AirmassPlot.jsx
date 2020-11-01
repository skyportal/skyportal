import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import embed from "vega-embed";
import VegaPlot from "./VegaPlot";

import fetchEphemeris from "../ducks/ephemeris";

const airmass_spec = (url, ephemeris) => {
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
                ephemeris.twilight_evening_astronomical_utc,
                ephemeris.twilight_morning_astronomical_utc,
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

export const AirMassPlotWithEphemURL = ({ dataUrl, ephemerisUrl }) => {
  const dispatch = useDispatch();
  const [ephemeris, setEphemeris] = useState(null);
  useEffect(() => {
    const getEphem = async () => {
      const result = await dispatch(fetchEphemeris(ephemerisUrl));
      if (result.status === "success") {
        setEphemeris(result.data);
      }
    };
    getEphem();
  }, [dispatch, ephemerisUrl]);

  if (ephemeris) {
    return <AirmassPlot dataUrl={dataUrl} ephemeris={ephemeris} />;
  }

  return <p>Loading plot...</p>;
};

AirMassPlotWithEphemURL.propTypes = {
  ...VegaPlot.propTypes,
  ephemerisUrl: PropTypes.string.isRequired,
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

AirMassPlotWithEphemURL.dispayName = "AirmassPlotFromPromise";
AirmassPlot.displayName = "AirmassPlot";

export default AirmassPlot;
