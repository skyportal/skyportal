import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  useZoomPan,
} from "react-simple-maps";

import world_map from "../../../images/maps/world-110m.json";

const width = 700;
const height = 475;

function CustomZoomableGroup({ children, ...restProps }: any) {
  const { mapRef, transformString, position } = useZoomPan(restProps);
  return (
    <g ref={mapRef}>
      <rect width={width} height={height} fill="transparent" />
      <g transform={transformString}>{children(position)}</g>
    </g>
  );
}

function mmadetectorlabel(nestedMMADetector: any) {
  return nestedMMADetector.mmadetectors
    .map((mmadetector: any) => mmadetector.nickname)
    .join(" / ");
}

function mmadetectorCanObserve(nestedMMADetector: any) {
  let color = "#f9d71c";
  if (nestedMMADetector.is_night_astronomical_at_least_one) {
    color = "#0c1445";
  }
  return color;
}

function MMADetectorMarker({ nestedMMADetector, position }: any) {
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

function normalizeLongitudeDiff(alpha: number, beta: number) {
  return 180 - Math.abs(Math.abs(alpha - beta) - 180);
}

function normalizeLatitudeDiff(alpha: number, beta: number) {
  return Math.abs(alpha - beta);
}

interface MMADetector {
  id?: number;
  name?: string;
  nickname?: string;
  lat?: number;
  lon?: number;
}

interface MMADetectorMapProps {
  mmadetectors: MMADetector[];
}

const MMADetectorMap = ({ mmadetectors }: MMADetectorMapProps) => {
  const nestedMMADetectors: any[] = [];
  for (let i = 0; i < mmadetectors.length; i += 1) {
    const det = mmadetectors[i]!;
    if (i === 0) {
      nestedMMADetectors.push({
        lat: det.lat,
        lon: det.lon,
        mmadetectors: [det],
      });
    } else {
      for (let j = 0; j < nestedMMADetectors.length; j += 1) {
        if (
          Math.abs(
            normalizeLatitudeDiff(det.lat as number, nestedMMADetectors[j].lat),
          ) < 1 &&
          Math.abs(
            normalizeLongitudeDiff(
              det.lon as number,
              nestedMMADetectors[j].lon,
            ),
          ) < 2
        ) {
          nestedMMADetectors[j].mmadetectors.push(det);
          break;
        } else if (j === nestedMMADetectors.length - 1) {
          nestedMMADetectors.push({
            lat: det.lat,
            lon: det.lon,
            mmadetectors: [det],
          });
          break;
        }
      }
    }
  }

  return (
    <ComposableMap width={width} height={height}>
      <CustomZoomableGroup center={[0, 0]}>
        {(position: any) => (
          <>
            <Geographies geography={world_map}>
              {({ geographies }: any) =>
                geographies.map((geo: any) => (
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

export default MMADetectorMap;
