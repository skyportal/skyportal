import React from "react";
import { useSelector } from "react-redux";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";
import NewShift from "./NewShift";
import MyCalendar from "./ShiftCalendar";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "23.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paperContent: {
    padding: "1rem",
  },
}));

const ShiftPage = () => {
  const classes = useStyles();
  const { shiftList } = useSelector((state) => state.shifts);
  const currentUser = useSelector((state) => state.profile);

  if (!shiftList) {
    return <CircularProgress />;
  }

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage shifts");

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <MyCalendar shifts={shiftList} />
        </Paper>
      </Grid>
      {permission && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add a New Shift</Typography>
              <NewShift />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

export default ShiftPage;
