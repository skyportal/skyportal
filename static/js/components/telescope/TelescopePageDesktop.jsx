import React, { lazy, Suspense } from "react";
import { useDispatch, useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import { Tooltip } from "@mui/material";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import Button from "../Button";
import NewTelescope from "../NewTelescope";
import TelescopeInfo from "./TelescopeInfo";

import TelescopeSearchBar from "./TelescopeSearchBar";

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
    fontSize: "1.2rem",
  },
  nonSelectedMenu: {
    height: "3rem",
    fontSize: "1.2rem",
  },
  help: {
    display: "flex",
    justifyContent: "right",
    alignItems: "center",
  },
  tooltip: {
    maxWidth: "60rem",
    fontSize: "1.2rem",
  },
  tooltipContent: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    width: "100%",
  },
  legend: {
    width: "100%",
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    gap: "10px",
  },
  circle: {
    borderRadius: "50%",
    width: "25px",
    height: "25px",
    display: "inline-block",
  },
  rect: {
    width: "25px",
    height: "25px",
    display: "inline-block",
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
  const currentUser = useSelector((state) => state.profile);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const currentTelescopeMenu = useSelector(
    (state) => state.telescope.currentTelescopeMenu,
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

  const Title = () => (
    <div className={classes.tooltipContent}>
      <div className={classes.legend}>
        <div style={{ background: "#f9d71c" }} className={classes.circle} />
        <p> Daytime</p>
      </div>
      <div className={classes.legend}>
        <div style={{ background: "#0c1445" }} className={classes.circle} />
        <p> Nighttime</p>
      </div>
      <div className={classes.legend}>
        <div style={{ background: "#5ca9d6" }} className={classes.rect} />
        <p> Networks and Space-based Instruments</p>
      </div>
    </div>
  );
  const TelescopeToolTip = () => (
    <Tooltip
      title={Title()}
      placement="bottom-end"
      classes={{ tooltip: classes.tooltip }}
    >
      <HelpOutlineOutlinedIcon />
    </Tooltip>
  );

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
            <div className={classes.help}>
              <TelescopeToolTip />
            </div>
          </Paper>
        </Grid>
        <Grid item md={4} sm={12}>
          <Paper className={classes.menu}>
            <Button
              secondary
              id="telescope-list"
              onClick={() => setSelectedMenu("Telescope List")}
              className={isMenuSelected("Telescope List")}
            >
              Telescope List
            </Button>
            {currentUser.permissions?.includes("Manage telescopes") && (
              <Button
                primary
                id="new-telescope"
                onClick={() => setSelectedMenu("New Telescope")}
                className={isMenuSelected("New Telescope")}
              >
                New Telescope
              </Button>
            )}
          </Paper>
          <Paper className={classes.paperContent}>
            <Paper>
              <TelescopeSearchBar id="search" telescopeList={telescopeList} />
            </Paper>
            {currentTelescopeMenu === "Telescope List" ? (
              <TelescopeInfo />
            ) : (
              currentUser.permissions?.includes("Manage telescopes") && (
                <NewTelescope />
              )
            )}
          </Paper>
        </Grid>
      </Grid>
    </Suspense>
  );
};

export default TelescopePage;
