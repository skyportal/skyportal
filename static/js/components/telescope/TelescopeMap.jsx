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

import world_map from "../../../images/maps/world-110m.json";

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
  dispatch({
    type: "skyportal/CURRENT_TELESCOPES",
    data: { currentTelescopes },
  });
}

function telescopeLabel(nestedTelescope) {
  return nestedTelescope.telescopes
    .map((telescope) => telescope.nickname)
    .join(" / ");
}

function normalizeLongitudeDiff(alpha, beta) {
  return 180 - Math.abs(Math.abs(alpha - beta) - 180);
}

function normalizeLatitudeDiff(alpha, beta) {
  return Math.abs(alpha - beta);
}

const TelescopeMap = ({ telescopes }) => {
  const filteredTelescopes = telescopes.filter(
    (telescope) => telescope.fixed_location,
  );
  const nestedTelescopes = [];
  for (let i = 0; i < filteredTelescopes.length; i += 1) {
    if (i === 0) {
      nestedTelescopes.push({
        lat: filteredTelescopes[i].lat,
        lon: filteredTelescopes[i].lon,
        is_night_astronomical_at_least_one:
          filteredTelescopes[i].is_night_astronomical,
        fixed_location: true,
        telescopes: [filteredTelescopes[i]],
      });
    } else {
      for (let j = 0; j < nestedTelescopes.length; j += 1) {
        if (
          Math.abs(
            normalizeLatitudeDiff(
              filteredTelescopes[i].lat,
              nestedTelescopes[j].lat,
            ),
          ) < 1 &&
          Math.abs(
            normalizeLongitudeDiff(
              filteredTelescopes[i].lon,
              nestedTelescopes[j].lon,
            ),
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
            fixed_location: true,
            telescopes: [filteredTelescopes[i]],
          });
          break;
        }
      }
    }
  }

  const nonFixedTelescopes = telescopes.filter(
    (telescope) => !telescope.fixed_location,
  );

  if (nonFixedTelescopes.length > 0) {
    nestedTelescopes.push({
      lat: -52,
      lon: 125,
      is_night_astronomical_at_least_one: nonFixedTelescopes.some(
        (telescope) => telescope.is_night_astronomical,
      ),
      fixed_location: false,
      telescopes: nonFixedTelescopes,
    });
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
                  <Marker
                    key={`${nestedTelescope.lon},${nestedTelescope.lat}`}
                    id="telescope_marker"
                    coordinates={[nestedTelescope.lon, nestedTelescope.lat]}
                    onClick={() =>
                      setCurrentTelescopes(nestedTelescope.telescopes)
                    }
                  >
                    {nestedTelescope.fixed_location ? (
                      <circle
                        r={6.5 / position.k}
                        fill={
                          nestedTelescope.is_night_astronomical_at_least_one
                            ? "#0c1445"
                            : "#f9d71c"
                        }
                      />
                    ) : (
                      <rect
                        x={-6.5 / position.k}
                        y={-6.5 / position.k}
                        width={13 / position.k}
                        height={13 / position.k}
                        fill="#5ca9d6"
                      />
                    )}
                    <text
                      id="telescopes_label"
                      textAnchor="middle"
                      fontSize={10 / position.k}
                      y={-10 / position.k}
                    >
                      {telescopeLabel(nestedTelescope)}
                    </text>
                  </Marker>
                ),
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
    }),
  ).isRequired,
};

CustomZoomableGroup.propTypes = {
  children: PropTypes.func.isRequired,
};

export default TelescopeMap;
