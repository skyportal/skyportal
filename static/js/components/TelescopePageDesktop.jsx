import React, { lazy, Suspense } from "react";
import { useSelector, useDispatch } from "react-redux";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import NewTelescope from "./NewTelescope";
import TelescopeInfo from "./TelescopeInfo";
// lazy import the TelescopeMap component
const TelescopeMap = lazy(() => import("./TelescopeMap"));

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

export function telescopeTitle(telescope) {
  if (!telescope?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${telescope?.nickname}`;
  return result;
}

export function telescopeInfo(telescope) {
  if (!telescope?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const array = [
    ...(telescope?.lat ? [`Latitude: ${telescope.lat}`] : []),
    ...(telescope?.lon ? [`Longitude: ${telescope.lon}`] : []),
    ...(telescope?.elevation ? [`Elevation: ${telescope.elevation}`] : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = "( " + array.join(" / ") + " )";

  return result;
}

const TelescopePage = () => {
  dispatch = useDispatch();
  const { telescopeList } = useSelector((state) => state.telescopes);
  const currentTelescopeMenu = useSelector(
    (state) => state.telescope.currentTelescopeMenu
  );

  function setSelectedMenu(currentSelectedTelescopeMenu) {
    const currentTelescopes = null;
    dispatch({
      type: "skyportal/CURRENT_TELESCOPES_AND_MENU",
      data: {
        currentTelescopes,
        currentTelescopeMenu: currentSelectedTelescopeMenu,
      },
    });
  }

  const classes = useStyles();

  function isMenuSelected(menu) {
    let style;
    if (menu === currentTelescopeMenu) {
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
            <TelescopeMap telescopes={telescopeList} />
          </Paper>
        </Grid>
        <Grid item md={4} sm={12}>
          <Paper className={classes.menu}>
            <Button
              id="telescope-list"
              onClick={() => setSelectedMenu("Telescope List")}
              className={isMenuSelected("Telescope List")}
            >
              Telescope List
            </Button>
            <Button
              id="new-telescope"
              onClick={() => setSelectedMenu("New Telescope")}
              className={isMenuSelected("New Telescope")}
            >
              New Telescope
            </Button>
          </Paper>
          <Paper className={classes.paperContent}>
            {currentTelescopeMenu === "Telescope List" ? (
              <TelescopeInfo />
            ) : (
              <NewTelescope />
            )}
          </Paper>
        </Grid>
      </Grid>
    </Suspense>
  );
};

export default TelescopePage;
