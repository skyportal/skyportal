import React, { lazy, Suspense } from "react";
import { useSelector, useDispatch } from "react-redux";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import NewInterferometer from "./NewInterferometer";
import InterferometerInfo from "./InterferometerInfo";
// lazy import the InterferometerMap component
const InterferometerMap = lazy(() => import("./InterferometerMap"));

let dispatch;
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

export function interferometerTitle(interferometer) {
  if (!interferometer?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${interferometer?.nickname}`;
  return result;
}

export function interferometerInfo(interferometer) {
  if (!interferometer?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const array = [
    ...(interferometer?.lat ? [`Latitude: ${interferometer.lat}`] : []),
    ...(interferometer?.lon ? [`Longitude: ${interferometer.lon}`] : []),
    ...(interferometer?.elevation
      ? [`Elevation: ${interferometer.elevation}`]
      : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = "( " + array.join(" / ") + " )";

  return result;
}

const InterferometerPage = () => {
  dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const { interferometerList } = useSelector((state) => state.interferometers);
  const currentInterferometerMenu = useSelector(
    (state) => state.interferometer.currentInterferometerMenu
  );

  function setSelectedMenu(currentSelectedInterferometerMenu) {
    const currentInterferometers = null;
    dispatch({
      type: "skyportal/CURRENT_INTERFEROMETERS_AND_MENU",
      data: {
        currentInterferometers,
        currentInterferometerMenu: currentSelectedInterferometerMenu,
      },
    });
  }

  const classes = useStyles();

  function isMenuSelected(menu) {
    let style;
    if (menu === currentInterferometerMenu) {
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
            <InterferometerMap interferometers={interferometerList} />
          </Paper>
        </Grid>
        <Grid item md={4} sm={12}>
          <Paper className={classes.menu}>
            <Button
              id="interferometer-list"
              onClick={() => setSelectedMenu("Interferometer List")}
              className={isMenuSelected("Interferometer List")}
            >
              Interferometer List
            </Button>
            {currentUser.permissions?.includes("Manage allocations") && (
              <Button
                id="new-interferometer"
                onClick={() => setSelectedMenu("New Interferometer")}
                className={isMenuSelected("New Interferometer")}
              >
                New Interferometer
              </Button>
            )}
          </Paper>
          <Paper className={classes.paperContent}>
            {currentInterferometerMenu === "Interferometer List" ? (
              <InterferometerInfo />
            ) : (
              currentUser.permissions?.includes("Manage allocations") && (
                <NewInterferometer />
              )
            )}
          </Paper>
        </Grid>
      </Grid>
    </Suspense>
  );
};

export default InterferometerPage;
