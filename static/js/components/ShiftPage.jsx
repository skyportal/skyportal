import React from "react";
import { useSelector, useDispatch } from "react-redux";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import PropTypes from "prop-types";
import CircularProgress from "@material-ui/core/CircularProgress";
import { showNotification } from "baselayer/components/Notifications";
import { Button } from "@material-ui/core";
import NewShift from "./NewShift";

import * as shiftActions from "../ducks/shift";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "23.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paperContent: {
    padding: "1rem",
  },
  shiftDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "130%",
  },
  secondary: {
    fontSize: "120%",
    whiteSpace: "pre-wrap",
  },
}));

export function shiftTitle(shift) {
  if (!shift?.group.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  let result = `${shift?.group.name}`;
  if (shift?.name) {
    result += `: ${shift?.name}`;
  }

  return result;
}

export function shiftInfo(shift) {
  if (!shift?.group.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  const startDate = new Date(`${shift.start_date}Z`).toLocaleString("en-US", {
    hour12: false,
  });
  const endDate = new Date(`${shift.end_date}Z`).toLocaleString("en-US", {
    hour12: false,
  });

  const array = [
    ...(shift?.start_date ? [`Start Date: ${startDate}`] : []),
    ...(shift?.end_date ? [`End Date: ${endDate}`] : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = array.join("\n");

  return result;
}

const ShiftList = ({ shifts }) => {
  const dispatch = useDispatch();
  const deleteShift = (shift) => {
    dispatch(shiftActions.deleteShift(shift.id)).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Shift deleted", "warning"));
      }
    });
  };

  const classes = useStyles();
  const textClasses = textStyles();
  return (
    <div className={classes.root}>
      <List component="nav">
        {shifts?.map((shift) => (
          <ListItem button key={shift.id}>
            <ListItemText
              primary={shiftTitle(shift)}
              secondary={shiftInfo(shift)}
              classes={textClasses}
            />
            <Button
              key={shift.id}
              id="delete_button"
              className={classes.shiftDelete}
              onClick={() => deleteShift(shift)}
            >
              &times;
            </Button>
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const ShiftPage = () => {
  const classes = useStyles();
  const { shiftList } = useSelector((state) => state.shifts);
  const currentUser = useSelector((state) => state.profile);

  if (!shiftList) {
    return <CircularProgress />;
  }

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Shifts</Typography>
            <ShiftList shifts={shiftList} />
          </div>
        </Paper>
      </Grid>
      {(currentUser.permissions?.includes("System admin") ||
        currentUser.permissions?.includes("Manage groups") ||
        currentUser.permissions?.includes("Manage shifts")) && (
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

ShiftList.propTypes = {
  shifts: PropTypes.arrayOf(PropTypes.any).isRequired,
};

export default ShiftPage;
