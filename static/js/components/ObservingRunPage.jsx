import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";
import {
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  DialogActions,
} from "@mui/material";
import CircularProgress from "@mui/material/CircularProgress";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import duration from "dayjs/plugin/duration";
import relativeTime from "dayjs/plugin/relativeTime";

import { observingRunTitle } from "./AssignmentForm";
import NewObservingRun from "./NewObservingRun";

import * as observingRunActions from "../ducks/observingRun";

dayjs.extend(utc);
dayjs.extend(duration);
dayjs.extend(relativeTime);

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paperContent: {
    padding: "1rem",
  },
  observingRunDelete: {
    fontSize: "2em",
  },
  observingRunDeleteDisabled: {
    opacity: 0,
  },
  hover: {
    "&:hover": {
      textDecoration: "underline",
    },
    color: theme.palette.mode === "dark" ? "#fafafa !important" : null,
  },
}));

export const observingRunInfo = (
  observingRun,
  instrumentList,
  telescopeList
) => {
  const { instrument_id } = observingRun;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!(observingRun?.calendar_date && instrument?.name && telescope?.name)) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const nowDate = dayjs().utc();
  const runDate = dayjs(observingRun?.calendar_date);
  const dt = dayjs.duration(runDate.diff(nowDate));

  const result = dt.humanize(true);

  return result;
};

const DeleteObservingRunDialog = ({ run, deletePermission }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);
  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };
  const deleteObservingRun = (observingRun) => {
    dispatch(observingRunActions.deleteObservingRun(observingRun.id)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Observing run deleted"));
          closeDialog();
        }
      }
    );
  };
  return (
    <div>
      <Button
        key={`${run.id}-delete_button`}
        id="delete_button"
        classes={{
          root: classes.observingRunDelete,
          disabled: classes.observingRunDeleteDisabled,
        }}
        onClick={openDialog}
        disabled={!deletePermission}
        size="small"
      >
        &times;
      </Button>
      <Dialog open={dialogOpen} onClose={closeDialog}>
        <DialogTitle>Delete Observing Run?</DialogTitle>
        <DialogContent>
          Are you sure you want to delete this observing run?
        </DialogContent>
        <DialogActions>
          <Button autoFocus onClick={closeDialog}>
            Dismiss
          </Button>
          <Button color="primary" onClick={() => deleteObservingRun(run)}>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

const ObservingRunList = ({ observingRuns, deletePermission }) => {
  const classes = useStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const dt_month = dayjs.duration(1, "month");

  const [displayAll, setDisplayAll] = useState(false);

  const toggleDisplayAllCheckbox = () => {
    setDisplayAll(!displayAll);
  };

  let observingRunsToShow = [];
  if (!displayAll) {
    observingRuns?.forEach((run) => {
      const dt = dayjs.duration(dayjs(run.calendar_date).diff(nowDate));
      if (dt.$ms < dt_month.$ms && dt.$ms > 0) {
        observingRunsToShow.push(run);
      }
    });
  } else {
    observingRunsToShow = [...observingRuns];
  }

  return (
    <div className={classes.root}>
      <List component="nav">
        <Button
          onClick={toggleDisplayAllCheckbox}
          data-testid="observationRunButton"
          variant="contained"
        >
          {displayAll
            ? "Show only upcoming observing runs"
            : "Show all observing runs"}
        </Button>
        {observingRunsToShow === 0 ? (
          <Typography>No observing runs to display...</Typography>
        ) : (
          ""
        )}
        {observingRunsToShow?.map((run) => (
          <ListItem key={run.id}>
            <ListItemText
              primary={
                <Link
                  to={`/run/${run.id}`}
                  role="link"
                  className={classes.hover}
                >
                  {observingRunTitle(
                    run,
                    instrumentList,
                    telescopeList,
                    groups
                  )}
                </Link>
              }
              secondary={observingRunInfo(run, instrumentList, telescopeList)}
            />
            <DeleteObservingRunDialog
              run={run}
              deletePermission={deletePermission}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const ObservingRunPage = () => {
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage observing runs");

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Observing Runs</Typography>
            <ObservingRunList
              observingRuns={observingRunList}
              deletePermission={permission}
            />
          </div>
        </Paper>
      </Grid>
      <Grid item md={6} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Add a New Observing Run</Typography>
            <NewObservingRun />
          </div>
        </Paper>
      </Grid>
    </Grid>
  );
};

ObservingRunList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  observingRuns: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

DeleteObservingRunDialog.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
  }).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

export default ObservingRunPage;
