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

function mmadetectorlabel(nestedMMADetector) {
  return nestedMMADetector.mmadetectors
    .map((mmadetector) => mmadetector.nickname)
    .join(" / ");
}

function mmadetectorCanObserve(nestedMMADetector) {
  let color = "#f9d71c";
  if (nestedMMADetector.is_night_astronomical_at_least_one) {
    color = "#0c1445";
  }
  return color;
}

function MMADetectorMarker({ nestedMMADetector, position }) {
  return (
    <Marker coordinates={[nestedMMADetector.lon, nestedMMADetector.lat]}>
      <circle
        r={6.5 / position.k}
        fill={mmadetectorCanObserve(nestedMMADetector)}
      />
      <text textAnchor="middle" fontSize={10 / position.k} y={-10 / position.k}>
        {mmadetectorlabel(nestedMMADetector)}
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

const MMADetectorMap = ({ mmadetectors }) => {
  const nestedMMADetectors = [];
  for (let i = 0; i < mmadetectors.length; i += 1) {
    if (i === 0) {
      nestedMMADetectors.push({
        lat: mmadetectors[i].lat,
        lon: mmadetectors[i].lon,
        mmadetectors: [mmadetectors[i]],
      });
    } else {
      for (let j = 0; j < nestedMMADetectors.length; j += 1) {
        if (
          Math.abs(
            normalizeLatitudeDiff(
              mmadetectors[i].lat,
              nestedMMADetectors[j].lat,
            ),
          ) < 1 &&
          Math.abs(
            normalizeLongitudeDiff(
              mmadetectors[i].lon,
              nestedMMADetectors[j].lon,
            ),
          ) < 2
        ) {
          nestedMMADetectors[j].mmadetectors.push(mmadetectors[i]);
          break;
        } else if (j === nestedMMADetectors.length - 1) {
          nestedMMADetectors.push({
            lat: mmadetectors[i].lat,
            lon: mmadetectors[i].lon,
            mmadetectors: [mmadetectors[i]],
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
            {nestedMMADetectors.map(
              (nestedMMADetector) =>
                nestedMMADetector.lon &&
                nestedMMADetector.lat && (
                  <MMADetectorMarker
                    key={`${nestedMMADetector.lon},${nestedMMADetector.lat}`}
                    nestedMMADetector={nestedMMADetector}
                    position={position}
                  />
                ),
            )}
          </>
        )}
      </CustomZoomableGroup>
    </ComposableMap>
  );
};

MMADetectorMap.propTypes = {
  mmadetectors: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      nickname: PropTypes.string,
      lat: PropTypes.number,
      lon: PropTypes.number,
    }),
  ).isRequired,
};

MMADetectorMarker.propTypes = {
  nestedMMADetector: PropTypes.shape({
    lat: PropTypes.number.isRequired,
    lon: PropTypes.number.isRequired,
    mmadetectors: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        nickname: PropTypes.string.isRequired,
        lat: PropTypes.number.isRequired,
        lon: PropTypes.number.isRequired,
      }),
    ),
  }).isRequired,
  position: PropTypes.shape({
    k: PropTypes.number,
  }).isRequired,
};

CustomZoomableGroup.propTypes = {
  children: PropTypes.node.isRequired,
};

export default MMADetectorMap;
