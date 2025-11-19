import React, { lazy, Suspense } from "react";
import { useDispatch, useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import NewEarthquake from "./NewEarthquake";
import EarthquakeInfo from "./EarthquakeInfo";
import Spinner from "../Spinner";
// lazy import the EarthquakeMap component
const EarthquakeMap = lazy(() => import("./EarthquakeMap"));

const useStyles = makeStyles((theme) => ({
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

const EarthquakePage = () => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const currentUser = useSelector((state) => state.profile);
  const earthquakes = useSelector((state) => state.earthquakes);
  const currentEarthquakeMenu = useSelector(
    (state) => state.earthquake.currentEarthquakeMenu,
  );

  if (!earthquakes) return <Spinner />;

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
    return menu === currentEarthquakeMenu
      ? classes.selectedMenu
      : classes.nonSelectedMenu;
  }

  return (
    <Suspense fallback={<CircularProgress color="secondary" />}>
      <Grid container spacing={3}>
        <Grid item md={8} sm={12}>
          <Paper className={classes.paperContent}>
            <EarthquakeMap earthquakes={earthquakes.events} />
          </Paper>
        </Grid>
        <Grid item md={4} sm={12}>
          <Paper className={classes.menu}>
            <Button
              onClick={() => setSelectedMenu("Earthquake List")}
              className={isMenuSelected("Earthquake List")}
            >
              Earthquake List
            </Button>
            {currentUser.permissions?.includes("Manage allocations") && (
              <Button
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
