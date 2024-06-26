import React, { lazy, Suspense } from "react";
import { useDispatch, useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import NewEarthquake from "./NewEarthquake";
import EarthquakeInfo from "./EarthquakeInfo";
// lazy import the EarthquakeMap component
const EarthquakeMap = lazy(() => import("./EarthquakeMap"));

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    backgroundColor: theme.palette.background.paper,
    maxHeight: "90%",
    overflowY: "auto",
  },
  paperContent: {
    padding: "1rem",
  },
  menu: {
    display: "flex",
    direction: "row",
    justifyContent: "space-around",
    alignItems: "center",
    marginBottom: "1rem",
  },
  selectedMenu: {
    height: "3rem",
    backgroundColor: "lightblue",
    fontSize: "1.2rem",
  },
  nonSelectedMenu: {
    height: "3rem",
    fontSize: "1.2rem",
  },
}));

export function earthquakeTitle(earthquake) {
  if (!earthquake?.event_id) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${earthquake?.event_id}`;
  return result;
}

export function earthquakeInfo(earthquake) {
  if (!earthquake?.event_id) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const array = [
    ...(earthquake?.lat ? [`Latitude: ${earthquake.lat}`] : []),
    ...(earthquake?.lon ? [`Longitude: ${earthquake.lon}`] : []),
    ...(earthquake?.depth ? [`Depth: ${earthquake.depth}`] : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = "( " + array.join(" / ") + " )";

  return result;
}

const EarthquakePage = () => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const currentUser = useSelector((state) => state.profile);
  const earthquakes = useSelector((state) => state.earthquakes);
  const currentEarthquakeMenu = useSelector(
    (state) => state.earthquake.currentEarthquakeMenu,
  );

  if (!earthquakes) {
    return <p>No earthquakes available...</p>;
  }

  const { events } = earthquakes;

  function setSelectedMenu(currentSelectedEarthquakeMenu) {
    const currentEarthquakes = null;
    dispatch({
      type: "skyportal/CURRENT_EARTHQUAKES_AND_MENU",
      data: {
        currentEarthquakes,
        currentEarthquakeMenu: currentSelectedEarthquakeMenu,
      },
    });
  }

  function isMenuSelected(menu) {
    let style;
    if (menu === currentEarthquakeMenu) {
      style = classes.selectedMenu;
    } else {
      style = classes.nonSelectedMenu;
    }
    return style;
  }

  return (
    <Suspense
      fallback={
        <div>
          <CircularProgress color="secondary" />
        </div>
      }
    >
      <Grid container spacing={3}>
        <Grid item md={8} sm={12}>
          <Paper className={classes.paperContent}>
            <EarthquakeMap earthquakes={events} />
          </Paper>
        </Grid>
        <Grid item md={4} sm={12}>
          <Paper className={classes.menu}>
            <Button
              id="earthquake-list"
              onClick={() => setSelectedMenu("Earthquake List")}
              className={isMenuSelected("Earthquake List")}
            >
              Earthquake List
            </Button>
            {currentUser.permissions?.includes("Manage allocations") && (
              <Button
                id="new-earthquake"
                onClick={() => setSelectedMenu("New Earthquake")}
                className={isMenuSelected("New Earthquake")}
              >
                New Earthquake
              </Button>
            )}
          </Paper>
          <Paper className={classes.paperContent}>
            {currentEarthquakeMenu === "Earthquake List" ? (
              <EarthquakeInfo />
            ) : (
              currentUser.permissions?.includes("Manage allocations") && (
                <NewEarthquake />
              )
            )}
          </Paper>
        </Grid>
      </Grid>
    </Suspense>
  );
};

export default EarthquakePage;
