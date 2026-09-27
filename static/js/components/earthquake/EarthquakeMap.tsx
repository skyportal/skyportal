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

function EarthquakeMarker({ nestedEarthquake, position }: any) {
  return (
    <Marker coordinates={[nestedEarthquake.lon, nestedEarthquake.lat]}>
      <circle r={6.5 / position.k} fill="#f9d71c" />
      <text textAnchor="middle" fontSize={10 / position.k} y={-10 / position.k}>
        {nestedEarthquake.earthquakes
          .map((earthquake: any) => earthquake.event_id)
          .join(" / ")}
      </text>
    </Marker>
  );
}

function normalizeLongitudeDiff(alpha: number, beta: number) {
  return 180 - Math.abs(Math.abs(alpha - beta) - 180);
}

interface EarthquakeMapProps {
  earthquakes: any[];
}

const EarthquakeMap = ({ earthquakes }: EarthquakeMapProps) => {
  const nestedEarthquakes: any[] = [];
  earthquakes.forEach((earthquake) => {
    const notice = earthquake.notices?.[0];
    if (!notice) return;
    const nested = nestedEarthquakes.find(
      (n) =>
        Math.abs(notice.lat - n.lat) < 1 &&
        normalizeLongitudeDiff(notice.lon, n.lon) < 2,
    );
    if (nested) {
      nested.earthquakes.push(earthquake);
    } else {
      nestedEarthquakes.push({
        lat: notice.lat,
        lon: notice.lon,
        earthquakes: [earthquake],
      });
    }
  });

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
