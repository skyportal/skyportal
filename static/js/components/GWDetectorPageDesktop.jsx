import React, { lazy, Suspense } from "react";
import { useSelector, useDispatch } from "react-redux";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import NewGWDetector from "./NewGWDetector";
import GWDetectorInfo from "./GWDetectorInfo";
// lazy import the GWDetectorMap component
const GWDetectorMap = lazy(() => import("./GWDetectorMap"));

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

export function gwdetectorTitle(gwdetector) {
  if (!gwdetector?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${gwdetector?.nickname}`;
  return result;
}

export function gwdetectorInfo(gwdetector) {
  if (!gwdetector?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const array = [
    ...(gwdetector?.lat ? [`Latitude: ${gwdetector.lat}`] : []),
    ...(gwdetector?.lon ? [`Longitude: ${gwdetector.lon}`] : []),
    ...(gwdetector?.elevation ? [`Elevation: ${gwdetector.elevation}`] : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = "( " + array.join(" / ") + " )";

  return result;
}

const GWDetectorPage = () => {
  dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const { gwdetectorList } = useSelector((state) => state.gwdetectors);
  const currentGWDetectorMenu = useSelector(
    (state) => state.gwdetector.currentGWDetectorMenu
  );

  function setSelectedMenu(currentSelectedGWDetectorMenu) {
    const currentGWDetectors = null;
    dispatch({
      type: "skyportal/CURRENT_GWDETECTORS_AND_MENU",
      data: {
        currentGWDetectors,
        currentGWDetectorMenu: currentSelectedGWDetectorMenu,
      },
    });
  }

  const classes = useStyles();

  function isMenuSelected(menu) {
    let style;
    if (menu === currentGWDetectorMenu) {
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
            <GWDetectorMap gwdetectors={gwdetectorList} />
          </Paper>
        </Grid>
        <Grid item md={4} sm={12}>
          <Paper className={classes.menu}>
            <Button
              id="gwdetector-list"
              onClick={() => setSelectedMenu("GWDetector List")}
              className={isMenuSelected("GWDetector List")}
            >
              GWDetector List
            </Button>
            {currentUser.permissions?.includes("Manage allocations") && (
              <Button
                id="new-gwdetector"
                onClick={() => setSelectedMenu("New GWDetector")}
                className={isMenuSelected("New GWDetector")}
              >
                New GWDetector
              </Button>
            )}
          </Paper>
          <Paper className={classes.paperContent}>
            {currentGWDetectorMenu === "GWDetector List" ? (
              <GWDetectorInfo />
            ) : (
              currentUser.permissions?.includes("Manage allocations") && (
                <NewGWDetector />
              )
            )}
          </Paper>
        </Grid>
      </Grid>
    </Suspense>
  );
};

export default GWDetectorPage;
