import React, { Suspense, useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import CircularProgress from "@mui/material/CircularProgress";
import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import NewShift from "./NewShift";
import MyCalendar from "./ShiftCalendar";
import ShiftManagement from "./ShiftManagement";
import ShiftSummary from "./ShiftSummary";
import Reminders from "../Reminders";

import { fetchShift, getShiftsSummary } from "../../ducks/shift";
import * as shiftsActions from "../../ducks/shifts";

const CommentList = React.lazy(() => import("../comment/CommentList"));

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
  comments: {
    paddingTop: "0.5rem",
    paddingBottom: "1rem",
    marginBottom: "1rem",
    marginLeft: "1rem",
    marginRight: "1rem",
  },
}));

const ShiftPage = ({ route }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const shiftList = useSelector((state) => state.shifts.shiftList);
  const currentShift = useSelector((state) => state.shift.currentShift);
  const [show, setShow] = useState(true);
  const [loadedFromRoute, setLoadedFromRoute] = useState(false);

  useEffect(() => {
    dispatch(shiftsActions.fetchShifts());
  }, []);

  useEffect(() => {
    if (
      route &&
      shiftList?.length > 0 &&
      !currentShift?.id &&
      !loadedFromRoute
    ) {
      const shift = shiftList.find((s) => s.id === parseInt(route.id, 10));
      if (shift) {
        dispatch(fetchShift(shift?.id));
        dispatch(
          getShiftsSummary({
            shiftID: parseInt(route.id, 10),
          }),
        );
        setShow(false);
      } else {
        dispatch(showNotification("Shift not found", "warning"));
      }
      setLoadedFromRoute(true);
    }
    if (currentShift?.id && shiftList?.length > 0) {
      // if the current shift is not in the shift list, then we need to set the currentShift back to null
      const shift = shiftList.find((s) => s.id === currentShift?.id);
      if (!shift) {
        dispatch(
          showNotification(
            "The shift currently selected has been deleted",
            "warning",
          ),
        );
        dispatch({ type: "skyportal/FETCH_SHIFT_OK", data: {} });
      }
    }
  }, [route, shiftList]);

  useEffect(() => {
    if (currentShift?.id) {
      setShow(false);
    }
  }, [currentShift]);

  return (
    <Grid container spacing={3}>
      <Grid item md={8} sm={12}>
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

      <Grid item md={4} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Button
              primary
              name="add_shift_button"
              onClick={() => setShow((prev) => !prev)}
            >
              Add New Shift
            </Button>
            {show ? <NewShift /> : null}
          </div>
        </Paper>
        <Paper elevation={1}>
          {shiftList && !show && currentShift?.id ? (
            <ShiftManagement currentShift={currentShift} />
          ) : null}
        </Paper>
        <Paper elevation={1}>
          {shiftList && !show && currentShift?.id ? (
            <div id="current_shift_comment" className={classes.comments}>
              <Suspense fallback={<CircularProgress />}>
                <CommentList
                  associatedResourceType="shift"
                  shiftID={currentShift?.id}
                />
              </Suspense>
            </div>
          ) : null}
        </Paper>
        <Paper elevation={1}>
          {shiftList && !show && currentShift?.id ? (
            <Reminders
              resourceId={currentShift.id.toString()}
              resourceType="shift"
            />
          ) : null}
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
