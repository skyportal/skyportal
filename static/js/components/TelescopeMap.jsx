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
function setCurrentTelescope(currentTelescope) {
  const currentTelescopeMenu = "Telescope Map";
  dispatch({
    type: "skyportal/CURRENT_TELESCOPE_AND_MENU",
    data: { currentTelescope, currentTelescopeMenu },
  });
}

const TelescopeMarker = ({ telescope, position }) => {
  return (
    <Marker
      key={telescope.name}
      coordinates={[telescope.lon, telescope.lat]}
      onClick={() => setCurrentTelescope(telescope)}
    >
      <circle r={12 / position.k} fill="#F53" />
      <text textAnchor="middle" fontSize={14 / position.k} y={-15 / position.k}>
        {telescope.name}
      </text>
    </Marker>
  );
};

const TelescopeMap = ({ telescopes }) => {
  dispatch = useDispatch();
  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
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
                  {telescopes.map(
                    (telescope) =>
                      telescope.lon &&
                      telescope.lat && (
                        <TelescopeMarker
                          telescope={telescope}
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
      <Grid item md={6} sm={12}>
        <Paper>
          <TelescopeInfo />
        </Paper>
      </Grid>
    </Grid>
  );
};

export default TelescopeMap;
