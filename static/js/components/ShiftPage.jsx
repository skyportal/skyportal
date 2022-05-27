import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { makeStyles } from "@material-ui/core/styles";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import CircularProgress from "@material-ui/core/CircularProgress";
import PropTypes from "prop-types";
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

const ShiftPage = ({ route }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const shiftList = useSelector((state) => state.shifts.shiftList);
  const currentShift = useSelector((state) => state.shift.currentShift);
  const [events, setEvents] = React.useState([]);

  if (shiftList) {
    if (!events || events?.length !== shiftList?.length) {
      setEvents(datestringToDate(shiftList));
    } else if (currentShift?.shift_users && currentShift?.id) {
      if (
        events.find((shift) => shift.id === currentShift.id).shift_users
          .length !== currentShift.shift_users.length
      ) {
        setEvents(datestringToDate(shiftList));
      }
    }
  }

  useEffect(() => {
    if (!currentShift?.id && route) {
      const shift = shiftList.find((s) => s.id === parseInt(route.id, 10));
      if (shift)
        dispatch({
          type: "skyportal/CURRENT_SHIFT",
          data: shift,
        });
    } else if (currentShift) {
      const updatedShift = shiftList.find((s) => s.id === currentShift.id);
      // check if the shift shift_users length is different from the current shift
      if (
        updatedShift &&
        updatedShift.shift_users.length !== currentShift.shift_users.length
      ) {
        dispatch({ type: "skyportal/CURRENT_SHIFT", data: updatedShift });
      } else if (updatedShift) {
        if (
          Object.keys(updatedShift).length > 0 &&
          Object.keys(currentShift).length > 0
        ) {
          let usersHaveChanged = false;
          // check if the users have the same ids, or if they need a replacement when they didnt need one before, and vice versa
          for (let i = 0; i < updatedShift.shift_users.length; i += 1) {
            if (
              updatedShift.shift_users[i].id !==
                currentShift.shift_users[i].id ||
              updatedShift.shift_users[i].needs_replacement !==
                currentShift.shift_users[i].needs_replacement ||
              updatedShift.shift_users[i].modified !==
                currentShift.shift_users[i].modified
            ) {
              usersHaveChanged = true;
              break;
            }
          }
          if (usersHaveChanged) {
            dispatch({ type: "skyportal/CURRENT_SHIFT", data: updatedShift });
          }
        }
      }
    }
  }, [shiftList, dispatch]);

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage shifts");
  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          {events ? (
            <MyCalendar events={events} currentShift={currentShift} />
          ) : (
            <CircularProgress />
          )}
        </Paper>
      </Grid>

      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          {currentShift &&
            (events && Object.keys(currentShift).length > 0 ? (
              <CurrentShiftMenu currentShift={currentShift} />
            ) : null)}
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

ShiftPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }),
};

ShiftPage.defaultProps = {
  route: null,
};

export default ShiftPage;
