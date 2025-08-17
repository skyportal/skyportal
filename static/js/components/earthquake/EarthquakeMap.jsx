import React from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import { Marker } from "react-simple-maps";
import CircularProgress from "@mui/material/CircularProgress";
import { CustomMap } from "../CustomMap";

let dispatch;

function setCurrentEarthquakes(currentEarthquakes) {
  const currentEarthquakeMenu = "Earthquake List";
  dispatch({
    type: "skyportal/CURRENT_EARTHQUAKES_AND_MENU",
    data: { currentEarthquakes, currentEarthquakeMenu },
  });
}

function earthquakelabel(nestedEarthquake) {
  return nestedEarthquake.earthquakes
    .map((earthquake) => earthquake.event_id)
    .join(" / ");
}

function earthquakeStatus(nestedEarthquake) {
  let color = "#f9d71c";
  if (nestedEarthquake.status === "canceled") {
    color = "#0c1445";
  }
  return color;
}

function EarthquakeMarker({ nestedEarthquake, position }) {
  return (
    <Marker
      id="earthquake_marker"
      key={`${nestedEarthquake.lon},${nestedEarthquake.lat}`}
      coordinates={[nestedEarthquake.lon, nestedEarthquake.lat]}
      onClick={() => setCurrentEarthquakes(nestedEarthquake)}
    >
      <circle r={6.5 / position.k} fill={earthquakeStatus(nestedEarthquake)} />
      <text
        id="earthquakes_label"
        textAnchor="middle"
        fontSize={10 / position.k}
        y={-10 / position.k}
      >
        {earthquakelabel(nestedEarthquake)}
      </text>
    </Marker>
  );
}

function normalizeLongitudeDiff(alpha, beta) {
  return 180 - Math.abs(Math.abs(alpha - beta) - 180);
}

function normalizeLatitudeDiff(alpha, beta) {
  return Math.abs(alpha - beta);
}

const EarthquakeMap = ({ earthquakes }) => {
  dispatch = useDispatch();

  if (!earthquakes) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const nestedEarthquakes = [];
  let cnt = 0;
  for (let i = 0; i < earthquakes.length; i += 1) {
    if (earthquakes[i].notices) {
      if (cnt === 0) {
        nestedEarthquakes.push({
          lat: earthquakes[i].notices[0].lat,
          lon: earthquakes[i].notices[0].lon,
          earthquakes: [earthquakes[i]],
        });
        cnt = 1;
      } else {
        for (let j = 0; j < nestedEarthquakes.length; j += 1) {
          if (
            Math.abs(
              normalizeLatitudeDiff(
                earthquakes[i].notices[0].lat,
                nestedEarthquakes[j].lat,
              ),
            ) < 1 &&
            Math.abs(
              normalizeLongitudeDiff(
                earthquakes[i].notices[0].lon,
                nestedEarthquakes[j].lon,
              ),
            ) < 2
          ) {
            nestedEarthquakes[j].earthquakes.push(earthquakes[i]);
            break;
          } else if (j === nestedEarthquakes.length - 1) {
            nestedEarthquakes.push({
              lat: earthquakes[i].notices[0].lat,
              lon: earthquakes[i].notices[0].lon,
              earthquakes: [earthquakes[i]],
            });
            break;
          }
        }
      }
    }
  }

  return (
    <CustomMap>
      {(position) =>
        nestedEarthquakes.map(
          (nestedEarthquake) =>
            nestedEarthquake.lon &&
            nestedEarthquake.lat && (
              <EarthquakeMarker
                key={`${nestedEarthquake.lon},${nestedEarthquake.lat}`}
                nestedEarthquake={nestedEarthquake}
                position={position}
              />
            ),
        )
      }
    </CustomMap>
  );
};

EarthquakeMap.propTypes = {
  earthquakes: PropTypes.arrayOf(
    PropTypes.shape({
      event_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
        .isRequired,
      notices: PropTypes.arrayOf(
        PropTypes.shape({
          lat: PropTypes.number,
          lon: PropTypes.number,
          depth: PropTypes.number,
        }),
      ),
    }),
  ).isRequired,
};

EarthquakeMarker.propTypes = {
  nestedEarthquake: PropTypes.shape({
    lat: PropTypes.number.isRequired,
    lon: PropTypes.number.isRequired,
    earthquakes: PropTypes.arrayOf(
      PropTypes.shape({
        event_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
          .isRequired,
        lat: PropTypes.number,
        lon: PropTypes.number,
        depth: PropTypes.number,
      }),
    ),
  }).isRequired,
  position: PropTypes.shape({
    k: PropTypes.number,
  }).isRequired,
};

export default EarthquakeMap;
