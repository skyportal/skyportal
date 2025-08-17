import React from "react";
import PropTypes from "prop-types";
import {
  ComposableMap,
  Geographies,
  Geography,
  useZoomPan,
} from "react-simple-maps";
import world_map from "../../images/maps/world-110m.json";

const WIDTH = 700;
const HEIGHT = 475;

function CustomZoomableGroup({ children, ...restProps }) {
  const { mapRef, transformString, position } = useZoomPan(restProps);
  return (
    <g ref={mapRef}>
      <rect width={WIDTH} height={HEIGHT} fill="transparent" />
      <g transform={transformString}>{children(position)}</g>
    </g>
  );
}
CustomZoomableGroup.propTypes = {
  children: PropTypes.func.isRequired,
};

export function CustomMap({ children }) {
  return (
    <ComposableMap width={WIDTH} height={HEIGHT}>
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
            {children(position)}
          </>
        )}
      </CustomZoomableGroup>
    </ComposableMap>
  );
}
CustomMap.propTypes = {
  children: PropTypes.func.isRequired,
};
