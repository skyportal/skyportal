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
function setCurrentGWDetectors(currentGWDetectors) {
  const currentGWDetectorMenu = "GWDetector List";
  dispatch({
    type: "skyportal/CURRENT_GWDETECTORS_AND_MENU",
    data: { currentGWDetectors, currentGWDetectorMenu },
  });
}

function gwdetectorlabel(nestedGWDetector) {
  return nestedGWDetector.gwdetectors
    .map((gwdetector) => gwdetector.nickname)
    .join(" / ");
}

function gwdetectorCanObserve(nestedGWDetector) {
  let color = "#f9d71c";
  if (nestedGWDetector.is_night_astronomical_at_least_one) {
    color = "#0c1445";
  }
  return color;
}

function GWDetectorMarker({ nestedGWDetector, position }) {
  return (
    <Marker
      id="gwdetector_marker"
      key={`${nestedGWDetector.lon},${nestedGWDetector.lat}`}
      coordinates={[nestedGWDetector.lon, nestedGWDetector.lat]}
      onClick={() => setCurrentGWDetectors(nestedGWDetector)}
    >
      <circle
        r={6.5 / position.k}
        fill={gwdetectorCanObserve(nestedGWDetector)}
      />
      <text
        id="gwdetectors_label"
        textAnchor="middle"
        fontSize={10 / position.k}
        y={-10 / position.k}
      >
        {gwdetectorlabel(nestedGWDetector)}
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

const GWDetectorMap = ({ gwdetectors }) => {
  const nestedGWDetectors = [];
  for (let i = 0; i < gwdetectors.length; i += 1) {
    if (i === 0) {
      nestedGWDetectors.push({
        lat: gwdetectors[i].lat,
        lon: gwdetectors[i].lon,
        gwdetectors: [gwdetectors[i]],
      });
    } else {
      for (let j = 0; j < nestedGWDetectors.length; j += 1) {
        if (
          Math.abs(
            normalizeLatitudeDiff(gwdetectors[i].lat, nestedGWDetectors[j].lat)
          ) < 1 &&
          Math.abs(
            normalizeLongitudeDiff(gwdetectors[i].lon, nestedGWDetectors[j].lon)
          ) < 2
        ) {
          nestedGWDetectors[j].gwdetectors.push(gwdetectors[i]);
          break;
        } else if (j === nestedGWDetectors.length - 1) {
          nestedGWDetectors.push({
            lat: gwdetectors[i].lat,
            lon: gwdetectors[i].lon,
            gwdetectors: [gwdetectors[i]],
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
            {nestedGWDetectors.map(
              (nestedGWDetector) =>
                nestedGWDetector.lon &&
                nestedGWDetector.lat && (
                  <GWDetectorMarker
                    key={`${nestedGWDetector.lon},${nestedGWDetector.lat}`}
                    nestedGWDetector={nestedGWDetector}
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

GWDetectorMap.propTypes = {
  gwdetectors: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      nickname: PropTypes.string,
      lat: PropTypes.number,
      lon: PropTypes.number,
    })
  ).isRequired,
};

GWDetectorMarker.propTypes = {
  nestedGWDetector: PropTypes.shape({
    lat: PropTypes.number.isRequired,
    lon: PropTypes.number.isRequired,
    gwdetectors: PropTypes.arrayOf(
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

export default GWDetectorMap;
