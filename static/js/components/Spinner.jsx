import React from "react";
import { makeStyles } from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";

const useStyles = makeStyles(() => ({
  spinner: {
    marginTop: "1rem",
    marginLeft: "auto",
    marginRight: "auto",
    display: "flex",
    top: "50%",
    left: "50%",
    position: "fixed",
  },
}));

const Spinner = () => {
  const classes = useStyles();
  return <CircularProgress className={classes.spinner} />;
};

export default Spinner;
