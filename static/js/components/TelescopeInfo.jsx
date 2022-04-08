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
    fontSize: "2.4rem",
    padding: "0",
    margin: "0",
  },
  h3: {
    fontSize: "1.5rem",
    marginTop: "0.5rem",
    padding: "0",
    margin: "0",
    },
  a: {
    fontSize: "1.5rem",
    marginTop: "2rem",
    padding: "0",
    margin: "0",
    }
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
          <h2 className={classes.h2}> {currentTelescope.name} ({currentTelescope.nickname})</h2>
          {currentTelescope.robotic ? (
                <h3 className={classes.h3}>Robotic : Yes</h3>
            ) : (
                <h3 className={classes.h3}>Robotic : Yes</h3>
            )}
          <h3 className={classes.h3}>Diameter : {currentTelescope.diameter} </h3>
          <h3 className={classes.h3}>Location : {currentTelescope.lat}, {currentTelescope.lon}</h3>
          <h3 className={classes.h3}>Elevation : {currentTelescope.elevation}</h3>

          <a className={classes.a} href={currentTelescope.skycam_link}>skycam link</a>
        </>
      ) : (
        <h2 className={classes.h3}>No telescope selected</h2>
      )}
    </div>
  );
};

export default TelescopeInfo;
