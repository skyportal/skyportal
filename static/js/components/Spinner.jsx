import React from "react";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";

const useStyles = makeStyles(() => ({
  spinner: {
    marginLeft: "auto",
    marginRight: "auto",
    display: "flex",
    top: "50%",
    left: "50%",
    position: "fixed",
    transform: "translate(-50%, -50%)",
  },
}));

const Spinner = () => {
  const classes = useStyles();
  return (
    <div className={classes.spinner}>
      <CircularProgress />
    </div>
  );
};

export default Spinner;
