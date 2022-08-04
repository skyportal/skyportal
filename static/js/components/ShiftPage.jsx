import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import { showNotification } from "baselayer/components/Notifications";
import NewShift from "./NewShift";
import MyCalendar from "./ShiftCalendar";
import { CurrentShiftMenu, CommentOnShift } from "./ShiftManagement";
import ShiftSummary from "./ShiftSummary";

import { getShiftsSummary } from "../ducks/shift";
import * as shiftsActions from "../ducks/shifts";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "23.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paperContent: {
    marginBottom: theme.spacing(2),
    padding: "1rem",
  },
}));

const ShiftPage = ({ route }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const shiftList = useSelector((state) => state.shifts.shiftList);
  const currentShift = useSelector((state) => state.shift.currentShift);
  const [show, setShow] = useState(true);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!loaded) {
      dispatch(shiftsActions.fetchShifts()).then((data) => {
        console.log(data);
        if (data.status === "success" && data.data.length === 0) {
          dispatch(showNotification("No shifts found", "warning"));
        } else if (data.status !== "success") {
          dispatch(showNotification("Error fetching shifts", "error"));
        }
      });
    }
    if (route && loaded) {
      const shift = shiftList.find((s) => s.id === parseInt(route.id, 10));
      if (shift) {
        dispatch({
          type: "skyportal/CURRENT_SHIFT",
          data: shift,
        });
        dispatch(
          getShiftsSummary({
            shiftID: parseInt(route.id, 10),
          })
        );
        setShow(false);
      } else {
        dispatch(showNotification("Shift not found", "error"));
      }
    }
  }, [loaded]);

  useEffect(() => {
    if (!loaded && shiftList?.length > 0) {
      setLoaded(true);
    }
    if (currentShift) {
      const updatedShift = shiftList.find((s) => s.id === currentShift.id);
      // check if the shift shift_users length is different from the current shift
      if (
        updatedShift &&
        updatedShift.shift_users.length !== currentShift.shift_users.length
      ) {
        dispatch({ type: "skyportal/CURRENT_SHIFT", data: updatedShift });
        setShow(false);
      } else if (updatedShift) {
        if (
          Object.keys(updatedShift).length > 0 &&
          Object.keys(currentShift).length > 0
        ) {
          if (
            updatedShift?.comments?.length !== currentShift?.comments?.length
          ) {
            dispatch({ type: "skyportal/CURRENT_SHIFT", data: updatedShift });
          } else {
            let usersHaveChanged = false;
            // check if the users have the same ids, or if they need a replacement when they didnt need one before, and vice versa
            for (let i = 0; i < updatedShift.shift_users.length; i += 1) {
              const old_shift_user = currentShift.shift_users[i];
              const new_shift_user = updatedShift.shift_users[i];
              if (
                new_shift_user.id !== old_shift_user.id ||
                new_shift_user.needs_replacement !==
                  old_shift_user.needs_replacement ||
                new_shift_user.modified !== old_shift_user.modified
              ) {
                usersHaveChanged = true;
                break;
              }
            }
            if (usersHaveChanged) {
              dispatch({ type: "skyportal/CURRENT_SHIFT", data: updatedShift });
              setShow(false);
            }
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
          {shiftList ? (
            <MyCalendar
              events={shiftList}
              currentShift={currentShift}
              setShow={setShow}
            />
          ) : (
            <CircularProgress />
          )}
        </Paper>
      </Grid>

      <Grid item md={6} sm={12}>
        {permission && (
          <Paper>
            <div className={classes.paperContent}>
              <Button
                name="add_shift_button"
                onClick={() => setShow((prev) => !prev)}
              >
                Add New Shift
              </Button>
              {show ? <NewShift /> : null}
            </div>
          </Paper>
        )}
        <Paper elevation={1}>
          {shiftList && !show && currentShift ? (
            <CurrentShiftMenu currentShift={currentShift} />
          ) : null}
        </Paper>
        <Paper elevation={1}>
          {shiftList && !show && currentShift ? <CommentOnShift /> : null}
        </Paper>
      </Grid>
      <Grid item md={12} sm={12}>
        <ShiftSummary />
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
