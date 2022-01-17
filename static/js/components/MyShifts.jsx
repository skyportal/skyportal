import React from "react";
import { useSelector } from "react-redux";
import Typography from "@material-ui/core/Typography";
import { Link } from "react-router-dom";
import { makeStyles } from "@material-ui/core/styles";


import UserProfileInfo from "./UserProfileInfo";

const useStyles = makeStyles((theme) => ({
    avatar: {
      padding: `${theme.spacing(2)}px 0 ${theme.spacing(1)}px 0`,
    },
    nodecor: {
      textDecoration: "none",
      textAlign: "center",
      color: theme.palette.text.primary,
    },
    centerContent: {
      justifyContent: "center",
    },
    signOutMargin: {
      margin: `0 0 ${theme.spacing(2)}px 0`,
    },
    typography: {
      padding: theme.spacing(1),
    },
    invisible: {
      display: "none",
    },
    paddingSides: {
      margin: `0 ${theme.spacing(2)}px 0 ${theme.spacing(2)}px`,
    },
    popoverMenu: {
      minWidth: "10rem",
      maxWidth: "20rem",
    },
  }));

const MyShifts = () => {
  const profile = useSelector((state) => state.profile);
  const groups = useSelector((state) => state.groups.user);
  const classes = useStyles();

  return (
    <div>
        <Typography variant="h5">Your next shifts</Typography>
      <div>

      </div>
      &nbsp;
      <br />
      <div>
        <Link
            to="/list_shifts"
            role="link"
            className={classes.nodecor}
        >
            <p className={classes.centerContent}>See all shifts here</p>
        </Link>
      </div>
      &nbsp;
    </div>
  );
};

export default MyShifts;
