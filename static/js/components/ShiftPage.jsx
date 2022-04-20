import React from "react";
import { useSelector } from "react-redux";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";
import NewShift from "./NewShift";
import MyCalendar from "./ShiftCalendar";
import CurrentShiftMenu from "./ShiftManagement";

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

function datestringToDate(shiftList) {
  for (let i = 0; i < shiftList.length; i += 1) {
    shiftList[i].start_date = new Date(`${shiftList[i].start_date}Z`);
    shiftList[i].end_date = new Date(`${shiftList[i].end_date}Z`);
  }
  return shiftList;
}

const ShiftPage = () => {
  const classes = useStyles();
  let { shiftList } = useSelector((state) => state.shifts);
  const currentUser = useSelector((state) => state.profile);
  shiftList = datestringToDate(shiftList);

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

      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <CurrentShiftMenu />
        </Paper>
        {permission && (
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add a New Shift</Typography>
              <NewShift />
            </div>
          </Paper>
        )}
      </Grid>
    </Grid>
  );
};

export default ShiftPage;
