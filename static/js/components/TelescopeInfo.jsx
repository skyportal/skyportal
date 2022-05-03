import React from "react";
import { useSelector } from "react-redux";
import { makeStyles } from "@material-ui/core/styles";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import { Divider } from "@material-ui/core";

const useStyles = makeStyles(() => ({
  root: {
    width: "100%",
    height: "100%",
    padding: "1rem",
    gap: "1rem",
    maxHeight: "85vh",
    overflowY: "auto",
  },
  listItem: {
    display: "flex",
    flexDirection: "column",
    justifyItems: "left",
    alignItems: "left",
  },
  telescope_header: {
    display: "flex",
    flexDirection: "row",
    justifyItems: "center",
    alignItems: "center",
    gap: "0.5rem",
  },
  h2: {
    textAlign: "left",
    fontSize: "1.4rem",
    padding: "0",
    margin: "0",
  },
  h3: {
    textAlign: "left",
    fontSize: "1rem",
    marginTop: "0.5rem",
    padding: "0",
    margin: "0",
  },
  a: {
    textAlign: "left",
    fontSize: "0.8rem",
    marginTop: "1rem",
    padding: "0",
    margin: "0",
  },
  canObserve: {
    height: "1rem",
    width: "1rem",
    backgroundColor: "#0c1445",
    borderRadius: "50%",
  },
  cannotObserve: {
    height: "1rem",
    width: "1rem",
    backgroundColor: "#f9d71c",
    borderRadius: "50%",
  },
}));

const TelescopeInfo = () => {
  const classes = useStyles();
  const currentTelescopes = useSelector(
    (state) => state.telescope.currentTelescopes
  );
  // return a list of telescopes with their information
  return currentTelescopes ? (
    <List className={classes.root}>
      {currentTelescopes.telescopes.map((telescope) => (
        <>
          <ListItem
            id={`${telescope.name}_info`}
            className={classes.listItem}
            key={telescope.id}
          >
            <div className={classes.telescope_header}>
              {telescope.is_night_astronomical ? (
                <span className={classes.canObserve} />
              ) : (
                <span className={classes.cannotObserve} />
              )}
              <h2 className={classes.h2}>
                {telescope.name} ({telescope.nickname})
              </h2>
            </div>
            {telescope.robotic ? (
              <h3 className={classes.h3}>Robotic : Yes</h3>
            ) : (
              <h3 className={classes.h3}>Robotic : No</h3>
            )}
            <h3 className={classes.h3}>
              Diameter :{" "}
              {telescope.diameter ? telescope.diameter.toFixed(1) : null}
            </h3>
            <h3 className={classes.h3}>
              Location : {telescope.lat ? telescope.lat.toFixed(4) : null},{" "}
              {telescope.lon ? telescope.lon.toFixed(4) : null}
            </h3>
            <h3 className={classes.h3}>
              Elevation :{" "}
              {telescope.elevation ? telescope.elevation.toFixed(1) : null}
            </h3>
            {telescope.skycam_link && (
              <a className={classes.a} href={telescope.skycam_link}>
                skycam link
              </a>
            )}
          </ListItem>
          <Divider />
        </>
      ))}
    </List>
  ) : (
    <h2 className={classes.h2}>No telescope selected</h2>
  );
};

export default TelescopeInfo;
