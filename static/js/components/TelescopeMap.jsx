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
function setCurrentTelescopes(currentTelescopes) {
  const currentTelescopeMenu = "Telescope List";
  dispatch({
    type: "skyportal/CURRENT_TELESCOPES_AND_MENU",
    data: { currentTelescopes, currentTelescopeMenu },
  });
}

function telescopelabel(nestedTelescope) {
  return nestedTelescope.telescopes
    .map((telescope) => telescope.nickname)
    .join(" / ");
}

function telescopeCanObserve(nestedTelescope) {
  let color = "#f9d71c";
  if (nestedTelescope.is_night_astronomical_at_least_one) {
    color = "#0c1445";
  }
  return color;
}

function TelescopeMarker({ nestedTelescope, position }) {
  return (
    <Marker
      id="telescope_marker"
      key={`${nestedTelescope.lon},${nestedTelescope.lat}`}
      coordinates={[nestedTelescope.lon, nestedTelescope.lat]}
      onClick={() => setCurrentTelescopes(nestedTelescope)}
    >
      <circle
        r={6.5 / position.k}
        fill={telescopeCanObserve(nestedTelescope)}
      />
      <text
        id="telescopes_label"
        textAnchor="middle"
        fontSize={10 / position.k}
        y={-10 / position.k}
      >
        {telescopelabel(nestedTelescope)}
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

const TelescopeMap = ({ telescopes }) => {
  const filteredTelescopes = telescopes.filter(
    (telescope) => telescope.fixed_location
  );
  const nestedTelescopes = [];
  for (let i = 0; i < filteredTelescopes.length; i += 1) {
    if (i === 0) {
      nestedTelescopes.push({
        lat: filteredTelescopes[i].lat,
        lon: filteredTelescopes[i].lon,
        is_night_astronomical_at_least_one:
          filteredTelescopes[i].is_night_astronomical,
        telescopes: [filteredTelescopes[i]],
      });
    } else {
      for (let j = 0; j < nestedTelescopes.length; j += 1) {
        if (
          Math.abs(
            normalizeLatitudeDiff(
              filteredTelescopes[i].lat,
              nestedTelescopes[j].lat
            )
          ) < 1 &&
          Math.abs(
            normalizeLongitudeDiff(
              filteredTelescopes[i].lon,
              nestedTelescopes[j].lon
            )
          ) < 2
        ) {
          nestedTelescopes[j].telescopes.push(filteredTelescopes[i]);
          if (filteredTelescopes[i].is_night_astronomical) {
            nestedTelescopes[j].is_night_astronomical_at_least_one = true;
          }
          break;
        } else if (j === nestedTelescopes.length - 1) {
          nestedTelescopes.push({
            lat: filteredTelescopes[i].lat,
            lon: filteredTelescopes[i].lon,
            is_night_astronomical_at_least_one:
              filteredTelescopes[i].is_night_astronomical,
            telescopes: [filteredTelescopes[i]],
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
            {nestedTelescopes.map(
              (nestedTelescope) =>
                nestedTelescope.lon &&
                nestedTelescope.lat && (
                  <TelescopeMarker
                    nestedTelescope={nestedTelescope}
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

TelescopeMap.propTypes = {
  telescopes: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      nickname: PropTypes.string,
      lat: PropTypes.number,
      lon: PropTypes.number,
      fixed_location: PropTypes.bool,
    })
  ).isRequired,
};

TelescopeMarker.propTypes = {
  nestedTelescope: PropTypes.shape({
    lat: PropTypes.number.isRequired,
    lon: PropTypes.number.isRequired,
    telescopes: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        nickname: PropTypes.string.isRequired,
        lat: PropTypes.number.isRequired,
        lon: PropTypes.number.isRequired,
        fixed_location: PropTypes.bool,
        is_night_astronomical: PropTypes.bool.isRequired,
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

export default TelescopeMap;
