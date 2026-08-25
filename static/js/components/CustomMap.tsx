import React from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  useZoomPan,
} from "react-simple-maps";
import world_map from "../../images/maps/world-110m.json";

const WIDTH = 700;
const HEIGHT = 475;

interface CustomZoomableGroupProps {
  children: (position: any) => React.ReactNode;
  [key: string]: any;
}

function CustomZoomableGroup({
  children,
  ...restProps
}: CustomZoomableGroupProps) {
  const { mapRef, transformString, position } = useZoomPan(restProps);
  return (
    <g ref={mapRef}>
      <rect width={WIDTH} height={HEIGHT} fill="transparent" />
      <g transform={transformString}>{children(position)}</g>
    </g>
  );
}

interface CustomMapProps {
  children: (position: any) => React.ReactNode;
}

export function CustomMap({ children }: CustomMapProps) {
  return (
    <ComposableMap
      width={WIDTH}
      height={HEIGHT}
      style={{ width: "100%", height: "auto" }}
    >
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
            {children(position)}
          </>
        )}
      </CustomZoomableGroup>
    </ComposableMap>
  );
}
