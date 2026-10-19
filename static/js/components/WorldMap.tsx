import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  useZoomPan,
} from "react-simple-maps";

import world_map from "../../images/maps/world-110m.json";

const width = 700;
const height = 475;

export interface WorldMapMarker {
  lat: number;
  lon: number;
  label: string;
}

const CustomZoomableGroup = ({ children, ...restProps }: any) => {
  const { mapRef, transformString, position } = useZoomPan(restProps);
  return (
    <g ref={mapRef}>
      <rect width={width} height={height} fill="transparent" />
      <g transform={transformString}>{children(position)}</g>
    </g>
  );
};

const longitudeDiff = (alpha: number, beta: number) =>
  180 - Math.abs(Math.abs(alpha - beta) - 180);

const WorldMap = ({ markers }: { markers: WorldMapMarker[] }) => {
  const groups: (WorldMapMarker & { labels: string[] })[] = [];
  markers.forEach((marker) => {
    const group = groups.find(
      (g) =>
        Math.abs(marker.lat - g.lat) < 1 &&
        longitudeDiff(marker.lon, g.lon) < 2,
    );
    if (group) group.labels.push(marker.label);
    else groups.push({ ...marker, labels: [marker.label] });
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
            {groups
              .filter(({ lat, lon }) => lat && lon)
              .map(({ lat, lon, labels }) => (
                <Marker key={`${lon},${lat}`} coordinates={[lon, lat]}>
                  <circle r={6.5 / position.k} fill="#f9d71c" />
                  <text
                    textAnchor="middle"
                    fontSize={10 / position.k}
                    y={-10 / position.k}
                  >
                    {labels.join(" / ")}
                  </text>
                </Marker>
              ))}
          </>
        )}
      </CustomZoomableGroup>
    </ComposableMap>
  );
};

export default WorldMap;
