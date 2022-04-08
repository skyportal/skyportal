import React from "react";
import { useSelector, useDispatch } from "react-redux";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import PropTypes from "prop-types";
import CircularProgress from "@material-ui/core/CircularProgress";
import NewTelescope from "./NewTelescope";
import TelescopeMap from "./TelescopeMap";
import Button from "@material-ui/core/Button";

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

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
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

const TelescopeList = ({ telescopes }) => {
  const classes = useStyles();
  const textClasses = textStyles();

  return (
    <div className={classes.root}>
      <List component="nav">
        {telescopes?.map((telescope) => (
          <ListItem button key={telescope.id}>
            <ListItemText
              primary={telescopeTitle(telescope)}
              secondary={telescopeInfo(telescope)}
              classes={textClasses}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const TelescopePage = () => {
  dispatch = useDispatch();
  const { telescopeList } = useSelector((state) => state.telescopes);
  const currentUser = useSelector((state) => state.profile);
  const currentTelescopeMenu = useSelector(
    (state) => state.telescope.currentTelescopeMenu
  );

  function setSelectedMenu(currentTelescopeMenu) {
    const currentTelescopes = null;
    dispatch({
      type: "skyportal/CURRENT_TELESCOPES_AND_MENU",
      data: { currentTelescopes, currentTelescopeMenu },
    });
  }

  const classes = useStyles();

  function isMenuSelected(menu) {
    if (menu === currentTelescopeMenu) {
      return classes.selectedMenu;
    } else {
      return classes.nonSelectedMenu;
    }
  }
  return (
    <>
      <Paper className={classes.menu}>
        <Button
          onClick={() => setSelectedMenu("Telescope List")}
          className={isMenuSelected("Telescope List")}
        >
          Telescope List
        </Button>
        <Button
          onClick={() => setSelectedMenu("Telescope Map")}
          className={isMenuSelected("Telescope Map")}
        >
          Telescope Map
        </Button>
      </Paper>
      {currentTelescopeMenu === "Telescope List" ? (
        <Grid container spacing={3}>
          <Grid item md={6} sm={12}>
            <Paper elevation={1}>
              <div className={classes.paperContent}>
                <Typography variant="h6">List of Telescopes</Typography>
                <TelescopeList telescopes={telescopeList} />
              </div>
            </Paper>
          </Grid>
          {currentUser.permissions?.includes("System admin") && (
            <Grid item md={6} sm={12}>
              <Paper>
                <div className={classes.paperContent}>
                  <Typography variant="h6">Add a New Telescope</Typography>
                  <NewTelescope />
                </div>
              </Paper>
            </Grid>
          )}
        </Grid>
      ) : (
        <TelescopeMap telescopes={telescopeList} />
      )}
    </>
  );
};

TelescopeList.propTypes = {
  telescopes: PropTypes.arrayOf(PropTypes.any).isRequired,
};

export default TelescopePage;
