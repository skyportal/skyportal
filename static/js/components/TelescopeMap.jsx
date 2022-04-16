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

const geoUrl =
  "https://raw.githubusercontent.com/zcreativelabs/react-simple-maps/master/topojson-maps/world-110m.json";

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
  let label = "";
  if (nestedTelescope.telescopes.length === 1) {
    label = nestedTelescope.telescopes[0].name;
  } else {
    for (let i = 0; i < nestedTelescope.telescopes.length; i += 1) {
      label += nestedTelescope.telescopes[i].nickname;
      if (i < nestedTelescope.telescopes.length - 1) {
        label += " / ";
      }
    }
  }
  return label;
}

function TelescopeMarker({ nestedTelescope, position }) {
  return (
    <Marker
      id="telescope_marker"
      key={`${nestedTelescope.lon},${nestedTelescope.lat}`}
      coordinates={[nestedTelescope.lon, nestedTelescope.lat]}
      onClick={() => setCurrentTelescopes(nestedTelescope)}
    >
      <circle r={6.5 / position.k} fill="#457B9C" />
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

function normalizeLongitude(longitude) {
  if (longitude < 0) {
    return longitude + 360;
  }
  return longitude;
}

function normalizeLatitude(latitude) {
  if (latitude < 0) {
    return latitude + 180;
  }
  return latitude;
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
        telescopes: [filteredTelescopes[i]],
      });
    } else {
      for (let j = 0; j < nestedTelescopes.length; j += 1) {
        if (
          Math.abs(
            normalizeLatitude(filteredTelescopes[i].lat) -
              normalizeLatitude(nestedTelescopes[j].lat)
          ) < 1 &&
          Math.abs(
            normalizeLongitude(filteredTelescopes[i].lon) -
              normalizeLongitude(nestedTelescopes[j].lon)
          ) < 2
        ) {
          nestedTelescopes[j].telescopes.push(filteredTelescopes[i]);
          break;
        } else if (j === nestedTelescopes.length - 1) {
          nestedTelescopes.push({
            lat: filteredTelescopes[i].lat,
            lon: filteredTelescopes[i].lon,
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
            <Geographies geography={geoUrl}>
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
    lat: PropTypes.number,
    lon: PropTypes.number,
    telescopes: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
        nickname: PropTypes.string,
        lat: PropTypes.number,
        lon: PropTypes.number,
        fixed_location: PropTypes.bool,
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
