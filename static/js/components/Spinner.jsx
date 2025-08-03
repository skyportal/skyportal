import React from "react";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";

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

// This component renders a spinner in the center of the screen.
const Spinner = () => {
  const classes = useStyles();
  return <CircularProgress className={classes.spinner} />;
};

export default Spinner;
