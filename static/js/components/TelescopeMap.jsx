import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { makeStyles } from "@material-ui/core/styles";
import Grid from "@material-ui/core/Grid";
import Paper from "@material-ui/core/Paper";
import PropTypes from "prop-types";
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup,
  useZoomPan,
} from "react-simple-maps";
import TelescopeInfo from "./TelescopeInfo";

import telescopeActions from "../ducks/telescope";

let dispatch;
const geoUrl =
  "https://raw.githubusercontent.com/zcreativelabs/react-simple-maps/master/topojson-maps/world-110m.json";

const width = 800;
const height = 600;

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    height: "100%",
    display: "grid",
    gridTemplateColumns: "2fr 1fr",
    gridTemplateRows: "1fr",
    gap: "2rem",
  },
}));

const CustomZoomableGroup = ({ children, ...restProps }) => {
  const { mapRef, transformString, position } = useZoomPan(restProps);
  return (
    <g ref={mapRef}>
      <rect width={width} height={height} fill="transparent" />
      <g transform={transformString}>{children(position)}</g>
    </g>
  );
};
function setCurrentTelescopes(currentTelescopes) {
  const currentTelescopeMenu = "Telescope Map";
  dispatch({
    type: "skyportal/CURRENT_TELESCOPES_AND_MENU",
    data: { currentTelescopes, currentTelescopeMenu },
  });
}

function telescopelabel(nestedTelescope) {
  if (nestedTelescope.telescopes.length === 1) {
    return nestedTelescope.telescopes[0].name;
  } else {
    return `${nestedTelescope.telescopes[0].name} and ${nestedTelescope.telescopes.length - 1} others`
  }
}

const TelescopeMarker = ({ nestedTelescope, position }) => {
  return (
    <Marker
      key={`${nestedTelescope.lon},${nestedTelescope.lat}`}
      coordinates={[nestedTelescope.lon, nestedTelescope.lat]}
      onClick={() => setCurrentTelescopes(nestedTelescope)}
    >
      <circle r={12 / position.k} fill="#F53" />
      <text textAnchor="middle" fontSize={14 / position.k} y={-15 / position.k}>
        {telescopelabel(nestedTelescope)}
      </text>
    </Marker>
  );
};

function normalizeLongitude(longitude) {
  if (longitude < 0) {
    return longitude + 360;
  }
  return longitude;
}

function normalizeLatitude(latitude) {
  if (latitude < 0) {
    return latitude + 180;
  }
  return latitude;
}

const TelescopeMap = ({ telescopes }) => {
  //remove telescopes that have fixed location to false
  const filteredTelescopes = telescopes.filter((telescope) => telescope.fixed_location);
  // create a nested list of telescopes using how close they are to each other
  let nestedTelescopes = [];
  for(let i = 0; i < filteredTelescopes.length; i++) {
    if (i === 0) {
      nestedTelescopes.push({
        lat: filteredTelescopes[i].lat,
        lon: filteredTelescopes[i].lon,
        telescopes: [filteredTelescopes[i]],
      });
    } else {
    for(let j = 0; j < nestedTelescopes.length; j++) {
      if (Math.abs(normalizeLatitude(filteredTelescopes[i].lat) - normalizeLatitude(nestedTelescopes[j].lat)) < 1 && Math.abs(normalizeLongitude(filteredTelescopes[i].lon) - normalizeLongitude(nestedTelescopes[j].lon)) < 2) {
        nestedTelescopes[j].telescopes.push(filteredTelescopes[i]);
        break;
      } else if (j === nestedTelescopes.length - 1) {
        nestedTelescopes.push({
          lat: filteredTelescopes[i].lat,
          lon: filteredTelescopes[i].lon,
          telescopes: [filteredTelescopes[i]],
        });
        break;
      }
      }
    }
  }
  console.log(nestedTelescopes);

  dispatch = useDispatch();
  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={9} sm={12}>
        <Paper elevation={3}>
          <ComposableMap width={width} height={height}>
            <CustomZoomableGroup center={[0, 0]}>
              {(position) => (
                <>
                  <Geographies geography={geoUrl}>
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
                  {nestedTelescopes.map(
                    (nestedTelescope) =>
                    nestedTelescope.lon &&
                    nestedTelescope.lat && (
                        <TelescopeMarker
                          nestedTelescope={nestedTelescope}
                          position={position}
                        />
                      )
                  )}
                </>
              )}
            </CustomZoomableGroup>
          </ComposableMap>
        </Paper>
      </Grid>
      <Grid item md={3} sm={12}>
        <Paper>
          <TelescopeInfo />
        </Paper>
      </Grid>
    </Grid>
  );
};

export default TelescopeMap;
