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
            <h2 className={classes.h2}>
              {telescope.name} ({telescope.nickname})
            </h2>
            {telescope.robotic ? (
              <h3 className={classes.h3}>Robotic : Yes</h3>
            ) : (
              <h3 className={classes.h3}>Robotic : No</h3>
            )}
            <h3 className={classes.h3}>Diameter : {telescope.diameter} </h3>
            <h3 className={classes.h3}>
              Location : {telescope.lat}, {telescope.lon}
            </h3>
            <h3 className={classes.h3}>Elevation : {telescope.elevation}</h3>
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
