import React, { useState } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  useZoomPan,
} from "react-simple-maps";

import { useAppDispatch } from "../../types/hooks";
import world_map from "../../../images/maps/world-110m.json";

const width = 700;
const height = 475;

// Labels are shown when zoom level exceeds this threshold
const ZOOM_LABEL_THRESHOLD = 2.5;

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
      <rect width={width} height={height} fill="transparent" />
      <g transform={transformString}>{children(position)}</g>
    </g>
  );
}
function setCurrentTelescopes(dispatch: any, currentTelescopes: any) {
  dispatch({
    type: "skyportal/CURRENT_TELESCOPES",
    data: { currentTelescopes },
  });
}

function telescopeLabel(nestedTelescope: any) {
  return nestedTelescope.telescopes
    .map((telescope: any) => telescope.nickname)
    .join(" / ");
}

function normalizeLongitudeDiff(alpha: number, beta: number) {
  return 180 - Math.abs(Math.abs(alpha - beta) - 180);
}

function normalizeLatitudeDiff(alpha: number, beta: number) {
  return Math.abs(alpha - beta);
}

interface TelescopeMapProps {
  telescopes: any[];
}

const TelescopeMap = ({ telescopes }: TelescopeMapProps) => {
  const dispatch = useAppDispatch();
  const [hoveredTelescope, setHoveredTelescope] = useState<any>(null);

  const filteredTelescopes = telescopes.filter(
    (telescope) => telescope.fixed_location,
  );
  const nestedTelescopes: any[] = [];
  for (let i = 0; i < filteredTelescopes.length; i += 1) {
    if (i === 0) {
      nestedTelescopes.push({
        lat: filteredTelescopes[i].lat,
        lon: filteredTelescopes[i].lon,
        is_night_astronomical_at_least_one:
          filteredTelescopes[i].is_night_astronomical,
        fixed_location: true,
        telescopes: [filteredTelescopes[i]],
      });
    } else {
      for (let j = 0; j < nestedTelescopes.length; j += 1) {
        if (
          Math.abs(
            normalizeLatitudeDiff(
              filteredTelescopes[i].lat,
              nestedTelescopes[j].lat,
            ),
          ) < 1 &&
          Math.abs(
            normalizeLongitudeDiff(
              filteredTelescopes[i].lon,
              nestedTelescopes[j].lon,
            ),
          ) < 2
        ) {
          nestedTelescopes[j].telescopes.push(filteredTelescopes[i]);
          if (filteredTelescopes[i].is_night_astronomical) {
            nestedTelescopes[j].is_night_astronomical_at_least_one = true;
          }
          break;
        } else if (j === nestedTelescopes.length - 1) {
          nestedTelescopes.push({
            lat: filteredTelescopes[i].lat,
            lon: filteredTelescopes[i].lon,
            is_night_astronomical_at_least_one:
              filteredTelescopes[i].is_night_astronomical,
            fixed_location: true,
            telescopes: [filteredTelescopes[i]],
          });
          break;
        }
      }
    }
  }

  const nonFixedTelescopes = telescopes.filter(
    (telescope) => !telescope.fixed_location,
  );

  if (nonFixedTelescopes.length > 0) {
    nestedTelescopes.push({
      lat: -52,
      lon: 125,
      is_night_astronomical_at_least_one: nonFixedTelescopes.some(
        (telescope) => telescope.is_night_astronomical,
      ),
      fixed_location: false,
      telescopes: nonFixedTelescopes,
    });
  }

  return (
    <ComposableMap
      width={width}
      height={height}
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
            {nestedTelescopes.map((nestedTelescope) => {
              if (!nestedTelescope.lon || !nestedTelescope.lat) return null;
              const key = `${nestedTelescope.lon},${nestedTelescope.lat}`;
              const isHovered =
                hoveredTelescope &&
                hoveredTelescope.lon === nestedTelescope.lon &&
                hoveredTelescope.lat === nestedTelescope.lat;
              const showLabel = position.k >= ZOOM_LABEL_THRESHOLD;
              const markerColor = nestedTelescope.fixed_location
                ? nestedTelescope.is_night_astronomical_at_least_one
                  ? "#0c1445"
                  : "#f9d71c"
                : "#5ca9d6";
              return (
                <Marker
                  key={key}
                  id="telescope_marker"
                  coordinates={[nestedTelescope.lon, nestedTelescope.lat]}
                  onClick={() =>
                    setCurrentTelescopes(dispatch, nestedTelescope.telescopes)
                  }
                >
                  <g
                    onMouseEnter={() => setHoveredTelescope(nestedTelescope)}
                    onMouseLeave={() => setHoveredTelescope(null)}
                    style={{ cursor: "pointer" }}
                  >
                    {isHovered && (
                      <circle
                        r={11 / position.k}
                        fill={markerColor}
                        opacity={0.3}
                      />
                    )}
                    {nestedTelescope.fixed_location ? (
                      <circle
                        r={6.5 / position.k}
                        fill={markerColor}
                        stroke="white"
                        strokeWidth={1.5 / position.k}
                      />
                    ) : (
                      <rect
                        x={-6.5 / position.k}
                        y={-6.5 / position.k}
                        width={13 / position.k}
                        height={13 / position.k}
                        fill={markerColor}
                        stroke="white"
                        strokeWidth={1.5 / position.k}
                      />
                    )}
                    {showLabel && (
                      <text
                        id="telescopes_label"
                        textAnchor="middle"
                        fontSize={10 / position.k}
                        y={-12 / position.k}
                        fill="#1a1a2e"
                        stroke="white"
                        strokeWidth={3 / position.k}
                        paintOrder="stroke"
                        style={{ pointerEvents: "none" }}
                      >
                        {telescopeLabel(nestedTelescope)}
                      </text>
                    )}
                  </g>
                </Marker>
              );
            })}
            {hoveredTelescope &&
              hoveredTelescope.lon &&
              hoveredTelescope.lat &&
              position.k < ZOOM_LABEL_THRESHOLD && (
                <Marker
                  key="hovered-label"
                  coordinates={[hoveredTelescope.lon, hoveredTelescope.lat]}
                  style={{ pointerEvents: "none" }}
                >
                  <text
                    textAnchor="middle"
                    fontSize={10 / position.k}
                    fontFamily="sans-serif"
                    fontWeight="600"
                    y={-12 / position.k}
                    fill="#1a1a2e"
                    stroke="white"
                    strokeWidth={3 / position.k}
                    paintOrder="stroke"
                    style={{ pointerEvents: "none" }}
                  >
                    {telescopeLabel(hoveredTelescope)}
                  </text>
                </Marker>
              )}
          </>
        )}
      </CustomZoomableGroup>
    </ComposableMap>
  );
};

export default TelescopeMap;
