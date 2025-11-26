import React from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import { Marker } from "react-simple-maps";
import CircularProgress from "@mui/material/CircularProgress";
import { CustomMap } from "../CustomMap";

function normalizeLongitudeDiff(alpha, beta) {
  return 180 - Math.abs(Math.abs(alpha - beta) - 180);
}

function normalizeLatitudeDiff(alpha, beta) {
  return Math.abs(alpha - beta);
}

const EarthquakeMap = ({ earthquakes }) => {
  let dispatch = useDispatch();

  if (!earthquakes) return <CircularProgress />;

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
              <Marker
                key={`${nestedEarthquake.lon},${nestedEarthquake.lat}`}
                coordinates={[nestedEarthquake.lon, nestedEarthquake.lat]}
                onClick={() =>
                  dispatch({
                    type: "skyportal/CURRENT_EARTHQUAKES_AND_MENU",
                    data: {
                      currentEarthquakes: nestedEarthquake,
                      currentEarthquakeMenu: "Earthquake List",
                    },
                  })
                }
              >
                <circle
                  r={6.5 / position.k}
                  fill={
                    nestedEarthquake.status === "canceled"
                      ? "#0c1445"
                      : "#f9d71c"
                  }
                />
                <text
                  textAnchor="middle"
                  fontSize={10 / position.k}
                  y={-10 / position.k}
                >
                  {nestedEarthquake.earthquakes
                    .map((e) => e.event_id)
                    .join(" / ")}
                </text>
              </Marker>
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

export default EarthquakeMap;
