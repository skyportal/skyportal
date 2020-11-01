import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import embed from "vega-embed";
import dayjs from "dayjs";

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
        parse: { time: "number" },
      },
    },
    encoding: {
      y: {
        type: "quantitative",
        scale: {
          reverse: true,
          domain: [1, 4],
        },
        axis: {
          grid: true,
        },
      },
      x: {
        scale: {
          type: "utc",
          domain: [ephemeris.sunset_unix_ms, ephemeris.sunrise_unix_ms],
        },
        type: "temporal",
        title: "time (UT)",
        axis: {
          grid: true,
        },
      },
    },
    transform: [
      {
        calculate: "utcFormat(datum.time, '%Y-%m-%dT%H:%M:%S.%L')",
        as: "formattedDate",
      },
    ],
    layer: [
      {
        mark: "rect",
        encoding: {
          x: {
            datum: ephemeris.sunset_unix_ms,
          },
          x2: {
            datum: ephemeris.twilight_evening_nautical_unix_ms,
          },
          color: { value: "#000ccf" },
          opacity: { value: 0.5 },
          tooltip: { datum: "Civil Twilight" },
        },
      },
      {
        mark: "rect",
        encoding: {
          x: {
            datum: ephemeris.twilight_evening_nautical_unix_ms,
          },
          x2: {
            datum: ephemeris.twilight_evening_astronomical_unix_ms,
          },
          color: { value: "#00014d" },
          opacity: { value: 0.2 },
          tooltip: { datum: "Nautical Twilight" },
        },
      },
      {
        mark: "rect",
        encoding: {
          x: {
            datum: ephemeris.twilight_evening_astronomical_unix_ms,
          },
          x2: {
            datum: ephemeris.twilight_morning_astronomical_unix_ms,
          },
          color: { value: "#000000" },
          opacity: { value: 0.0 },
          tooltip: { datum: "Night" },
        },
      },
      {
        mark: "rect",
        encoding: {
          x: {
            datum: ephemeris.twilight_morning_astronomical_unix_ms,
          },
          x2: {
            datum: ephemeris.twilight_morning_nautical_unix_ms,
          },
          color: { value: "#00014d" },
          opacity: { value: 0.2 },
          tooltip: { datum: "Nautical Twilight" },
        },
      },
      {
        mark: "rect",
        encoding: {
          x: {
            datum: ephemeris.twilight_morning_nautical_unix_ms,
          },
          x2: {
            datum: ephemeris.sunrise_unix_ms,
          },
          color: { value: "#000ccf" },
          opacity: { value: 0.5 },
          tooltip: { datum: "Civil Twilight" },
        },
      },
      {
        mark: { type: "line", clip: true, point: true },
        encoding: {
          x: { field: "time" },
          y: { field: "airmass" },
          tooltip: [
            { field: "formattedDate", title: "time (UT)" },
            { field: "airmass", type: "quantitative" },
          ],
        },
      },
      {
        mark: { type: "rule", strokeWidth: 2, clip: true },
        encoding: {
          x: {
            datum: dayjs().unix() * 1000,
          },
          color: { value: "#35ff1f" },
          tooltip: { datum: "Now" },
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
    twilight_evening_astronomical_unix_ms: PropTypes.number,
    twilight_morning_astronomical_unix_ms: PropTypes.number,
    twilight_evening_nautical_unix_ms: PropTypes.number,
    twilight_morning_nautical_unix_ms: PropTypes.number,
    sunset_unix_ms: PropTypes.number,
    sunrise_unix_ms: PropTypes.number,
  }).isRequired,
};

AirMassPlotWithEphemURL.dispayName = "AirmassPlotFromPromise";
AirmassPlot.displayName = "AirmassPlot";

export default AirmassPlot;
