import React, { lazy, Suspense } from "react";
import { useDispatch, useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import Button from "../Button";
import NewMMADetector from "../NewMMADetector";
import MMADetectorInfo from "./MMADetectorInfo";
// lazy import the MMADetectorMap component
const MMADetectorMap = lazy(() => import("./MMADetectorMap"));

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
    fontSize: "1.2rem",
  },
  nonSelectedMenu: {
    height: "3rem",
    fontSize: "1.2rem",
  },
}));

export function mmadetectorTitle(mmadetector) {
  if (!mmadetector?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${mmadetector?.nickname}`;
  return result;
}

export function mmadetectorInfo(mmadetector) {
  if (!mmadetector?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const array = [
    ...(mmadetector?.lat ? [`Latitude: ${mmadetector.lat}`] : []),
    ...(mmadetector?.lon ? [`Longitude: ${mmadetector.lon}`] : []),
    ...(mmadetector?.elevation ? [`Elevation: ${mmadetector.elevation}`] : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = "( " + array.join(" / ") + " )";

  return result;
}

const MMADetectorPageDesktop = () => {
  dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const { mmadetectorList } = useSelector((state) => state.mmadetectors);
  const currentMMADetectorMenu = useSelector(
    (state) => state.mmadetector.currentMMADetectorMenu,
  );

  function setSelectedMenu(currentSelectedMMADetectorMenu) {
    const currentMMADetectors = null;
    dispatch({
      type: "skyportal/CURRENT_MMADETECTORS_AND_MENU",
      data: {
        currentMMADetectors,
        currentMMADetectorMenu: currentSelectedMMADetectorMenu,
      },
    });
  }

  const classes = useStyles();

  function isMenuSelected(menu) {
    let style;
    if (menu === currentMMADetectorMenu) {
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
            <MMADetectorMap mmadetectors={mmadetectorList} />
          </Paper>
        </Grid>
        <Grid item md={4} sm={12}>
          <Paper className={classes.menu}>
            <Button
              secondary
              id="mmadetector-list"
              onClick={() => setSelectedMenu("MMADetector List")}
              className={isMenuSelected("MMADetector List")}
            >
              MMADetector List
            </Button>
            {currentUser.permissions?.includes("Manage allocations") && (
              <Button
                id="new-mmadetector"
                onClick={() => setSelectedMenu("New MMADetector")}
                className={isMenuSelected("New MMADetector")}
              >
                New MMADetector
              </Button>
            )}
          </Paper>
          <Paper className={classes.paperContent}>
            {currentMMADetectorMenu === "MMADetector List" ? (
              <MMADetectorInfo />
            ) : (
              currentUser.permissions?.includes("Manage allocations") && (
                <NewMMADetector />
              )
            )}
          </Paper>
        </Grid>
      </Grid>
    </Suspense>
  );
};

export default MMADetectorPageDesktop;
