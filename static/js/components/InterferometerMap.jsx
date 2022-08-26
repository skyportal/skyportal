import React from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  useZoomPan,
} from "react-simple-maps";

import world_map from "../../images/maps/world-110m.json";

let dispatch;
const width = 700;
const height = 475;

function CustomZoomableGroup({ children, ...restProps }) {
  const { mapRef, transformString, position } = useZoomPan(restProps);
  return (
    <g ref={mapRef}>
      <rect width={width} height={height} fill="transparent" />
      <g transform={transformString}>{children(position)}</g>
    </g>
  );
}
function setCurrentInterferometers(currentInterferometers) {
  const currentInterferometerMenu = "Interferometer List";
  dispatch({
    type: "skyportal/CURRENT_TELESCOPES_AND_MENU",
    data: { currentInterferometers, currentInterferometerMenu },
  });
}

function interferometerlabel(nestedInterferometer) {
  return nestedInterferometer.interferometers
    .map((interferometer) => interferometer.nickname)
    .join(" / ");
}

function interferometerCanObserve(nestedInterferometer) {
  let color = "#f9d71c";
  if (nestedInterferometer.is_night_astronomical_at_least_one) {
    color = "#0c1445";
  }
  return color;
}

function InterferometerMarker({ nestedInterferometer, position }) {
  return (
    <Marker
      id="interferometer_marker"
      key={`${nestedInterferometer.lon},${nestedInterferometer.lat}`}
      coordinates={[nestedInterferometer.lon, nestedInterferometer.lat]}
      onClick={() => setCurrentInterferometers(nestedInterferometer)}
    >
      <circle
        r={6.5 / position.k}
        fill={interferometerCanObserve(nestedInterferometer)}
      />
      <text
        id="interferometers_label"
        textAnchor="middle"
        fontSize={10 / position.k}
        y={-10 / position.k}
      >
        {interferometerlabel(nestedInterferometer)}
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

const InterferometerMap = ({ interferometers }) => {
  const nestedInterferometers = [];
  for (let i = 0; i < interferometers.length; i += 1) {
    if (i === 0) {
      nestedInterferometers.push({
        lat: interferometers[i].lat,
        lon: interferometers[i].lon,
        interferometers: [interferometers[i]],
      });
    } else {
      for (let j = 0; j < nestedInterferometers.length; j += 1) {
        if (
          Math.abs(
            normalizeLatitudeDiff(
              interferometers[i].lat,
              nestedInterferometers[j].lat
            )
          ) < 1 &&
          Math.abs(
            normalizeLongitudeDiff(
              interferometers[i].lon,
              nestedInterferometers[j].lon
            )
          ) < 2
        ) {
          nestedInterferometers[j].interferometers.push(interferometers[i]);
          break;
        } else if (j === nestedInterferometers.length - 1) {
          nestedInterferometers.push({
            lat: interferometers[i].lat,
            lon: interferometers[i].lon,
            interferometers: [interferometers[i]],
          });
          break;
        }
      }
    }
  }

  dispatch = useDispatch();
  return (
    <ComposableMap width={width} height={height}>
      <CustomZoomableGroup center={[0, 0]}>
        {(position) => (
          <>
            <Geographies geography={world_map}>
              {({ geographies }) =>
                geographies.map((geo) => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#EAEAEC"
                    stroke="#D6D6DA"
                  />
                ))
              }
            </Geographies>
            {nestedInterferometers.map(
              (nestedInterferometer) =>
                nestedInterferometer.lon &&
                nestedInterferometer.lat && (
                  <InterferometerMarker
                    key={`${nestedInterferometer.lon},${nestedInterferometer.lat}`}
                    nestedInterferometer={nestedInterferometer}
                    position={position}
                  />
                )
            )}
          </>
        )}
      </CustomZoomableGroup>
    </ComposableMap>
  );
};

InterferometerMap.propTypes = {
  interferometers: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      nickname: PropTypes.string,
      lat: PropTypes.number,
      lon: PropTypes.number,
    })
  ).isRequired,
};

InterferometerMarker.propTypes = {
  nestedInterferometer: PropTypes.shape({
    lat: PropTypes.number.isRequired,
    lon: PropTypes.number.isRequired,
    interferometers: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        nickname: PropTypes.string.isRequired,
        lat: PropTypes.number.isRequired,
        lon: PropTypes.number.isRequired,
      })
    ),
  }).isRequired,
  position: PropTypes.shape({
    k: PropTypes.number,
  }).isRequired,
};

CustomZoomableGroup.propTypes = {
  children: PropTypes.node.isRequired,
};

export default InterferometerMap;
