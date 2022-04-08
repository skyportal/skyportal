import React from "react";
import { useSelector } from "react-redux";
import { makeStyles } from "@material-ui/core/styles";
// get the current telescope using useEffect

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    height: "100%",
    padding: "1rem",
  },
  h2: {
    padding: "0",
    margin: "0",
  },
}));

const TelescopeInfo = () => {
  const classes = useStyles();
  const currentTelescope = useSelector(
    (state) => state.telescope.currentTelescope
  );
  return (
    <div className={classes.root}>
      {currentTelescope ? (
        <>
          <h2 className={classes.h3}>
            {currentTelescope.name} ({currentTelescope.nickname})
          </h2>
          <h3>{currentTelescope.description}</h3>
          <a href={currentTelescope.skycam_link}>skycam link</a>
        </>
      ) : (
        <h2 className={classes.h3}>No telescope selected</h2>
      )}
    </div>
  );
};

export default TelescopeInfo;
