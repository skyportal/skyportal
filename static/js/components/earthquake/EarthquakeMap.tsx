import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  useZoomPan,
} from "react-simple-maps";
import CircularProgress from "@mui/material/CircularProgress";

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

function earthquakelabel(nestedEarthquake: any) {
  return nestedEarthquake.earthquakes
    .map((earthquake: any) => earthquake.event_id)
    .join(" / ");
}

function earthquakeStatus(nestedEarthquake: any) {
  let color = "#f9d71c";
  if (nestedEarthquake.status === "canceled") {
    color = "#0c1445";
  }
  return color;
}

function EarthquakeMarker({ nestedEarthquake, position, onSelect }: any) {
  return (
    <Marker
      id="earthquake_marker"
      key={`${nestedEarthquake.lon},${nestedEarthquake.lat}`}
      coordinates={[nestedEarthquake.lon, nestedEarthquake.lat]}
      onClick={() => onSelect?.(nestedEarthquake)}
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

function normalizeLongitudeDiff(alpha: number, beta: number) {
  return 180 - Math.abs(Math.abs(alpha - beta) - 180);
}

function normalizeLatitudeDiff(alpha: number, beta: number) {
  return Math.abs(alpha - beta);
}

interface Earthquake {
  event_id: string | number;
  notices?: {
    lat?: number;
    lon?: number;
    depth?: number;
  }[];
}

interface EarthquakeMapProps {
  earthquakes: Earthquake[];
  onSelectEarthquakes?: (nestedEarthquake: any) => void;
}

const EarthquakeMap = ({
  earthquakes,
  onSelectEarthquakes,
}: EarthquakeMapProps) => {
  if (!earthquakes) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const nestedEarthquakes: any[] = [];
  let cnt = 0;
  for (let i = 0; i < earthquakes.length; i += 1) {
    const eq = earthquakes[i]!;
    const firstNotice = eq.notices?.[0];
    if (firstNotice) {
      if (cnt === 0) {
        nestedEarthquakes.push({
          lat: firstNotice.lat,
          lon: firstNotice.lon,
          earthquakes: [eq],
        });
        cnt = 1;
      } else {
        for (let j = 0; j < nestedEarthquakes.length; j += 1) {
          if (
            Math.abs(
              normalizeLatitudeDiff(
                firstNotice.lat as number,
                nestedEarthquakes[j].lat,
              ),
            ) < 1 &&
            Math.abs(
              normalizeLongitudeDiff(
                firstNotice.lon as number,
                nestedEarthquakes[j].lon,
              ),
            ) < 2
          ) {
            nestedEarthquakes[j].earthquakes.push(eq);
            break;
          } else if (j === nestedEarthquakes.length - 1) {
            nestedEarthquakes.push({
              lat: firstNotice.lat,
              lon: firstNotice.lon,
              earthquakes: [eq],
            });
            break;
          }
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
            {nestedEarthquakes.map(
              (nestedEarthquake) =>
                nestedEarthquake.lon &&
                nestedEarthquake.lat && (
                  <EarthquakeMarker
                    key={`${nestedEarthquake.lon},${nestedEarthquake.lat}`}
                    nestedEarthquake={nestedEarthquake}
                    position={position}
                    onSelect={onSelectEarthquakes}
                  />
                ),
            )}
          </>
        )}
      </CustomZoomableGroup>
    </ComposableMap>
  );
};

export default EarthquakeMap;
