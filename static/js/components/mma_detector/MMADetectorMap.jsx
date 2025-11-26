import React from "react";
import PropTypes from "prop-types";
import { Marker } from "react-simple-maps";
import { CustomMap } from "../CustomMap";

function MMADetectorMarker({ nestedMMADetector, position }) {
  return (
    <Marker coordinates={[nestedMMADetector.lon, nestedMMADetector.lat]}>
      <circle
        r={6.5 / position.k}
        fill={
          nestedMMADetector.is_night_astronomical_at_least_one
            ? "#0c1445"
            : "#f9d71c"
        }
      />
      <text textAnchor="middle" fontSize={10 / position.k} y={-10 / position.k}>
        {nestedMMADetector.mmadetectors.map((m) => m.nickname).join(" / ")}
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

  return (
    <CustomMap>
      {(position) =>
        nestedMMADetectors.map(
          (nestedMMADetector) =>
            nestedMMADetector.lon &&
            nestedMMADetector.lat && (
              <MMADetectorMarker
                key={`${nestedMMADetector.lon},${nestedMMADetector.lat}`}
                nestedMMADetector={nestedMMADetector}
                position={position}
              />
            ),
        )
      }
    </CustomMap>
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
    is_night_astronomical_at_least_one: PropTypes.bool.isRequired,
  }).isRequired,
  position: PropTypes.shape({
    k: PropTypes.number,
  }).isRequired,
};

export default MMADetectorMap;
