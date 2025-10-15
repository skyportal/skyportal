import React, { useState } from "react";
import propTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import CheckIcon from "@mui/icons-material/Check";
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

import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import duration from "dayjs/plugin/duration";
import relativeTime from "dayjs/plugin/relativeTime";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import { observingRunTitle } from "./AssignmentForm";
import NewObservingRun from "./NewObservingRun";
import ModifyObservingRun from "./ModifyObservingRun";

import * as observingRunActions from "../../ducks/observingRun";

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
  observingRunEdit: {
    fontSize: "2em",
  },
  observingRunEditDisabled: {
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
  telescopeList,
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

  let result = dt.humanize(true);
  if (observingRun?.observers) {
    result += ` / observers: ${observingRun.observers}`;
  }
  if (observingRun?.duration) {
    result += ` / # of nights: ${observingRun.duration}`;
  }

  return result;
};

const ModifyObservingRunDialog = ({ run, modifyPermission }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [observingRunToModify, setObservingRunToModify] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setObservingRunToModify(id);
  };

  const closeDialog = () => {
    setDialogOpen(false);
    setObservingRunToModify(null);
  };
  return (
    <div>
      <Button
        key={`${run.id}-edit_button`}
        id="edit_button"
        classes={{
          root: classes.observingRunEdit,
          disabled: classes.observingRunEditDisabled,
        }}
        onClick={() => openDialog(run.id)}
        disabled={!modifyPermission}
        size="small"
      >
        <EditIcon />
      </Button>
      <Dialog
        open={dialogOpen && observingRunToModify !== null}
        onClose={closeDialog}
        maxWidth="md"
      >
        <DialogTitle>Edit Observing Run</DialogTitle>
        <DialogContent dividers>
          <ModifyObservingRun
            run_id={observingRunToModify}
            onClose={closeDialog}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

ModifyObservingRunDialog.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
  }).isRequired,
  modifyPermission: PropTypes.bool.isRequired,
};

const DeleteObservingRunDialog = ({ run, deletePermission }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [observingRunToDelete, setObservingRunToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setObservingRunToDelete(id);
  };

  const closeDialog = () => {
    setDialogOpen(false);
    setObservingRunToDelete(null);
  };
  const deleteObservingRun = () => {
    dispatch(observingRunActions.deleteObservingRun(observingRunToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Observing run deleted"));
          closeDialog();
        }
      },
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
        onClick={() => openDialog(run.id)}
        disabled={!deletePermission}
        size="small"
      >
        <DeleteIcon />
      </Button>
      <ConfirmDeletionDialog
        deleteFunction={deleteObservingRun}
        dialogOpen={dialogOpen}
        closeDialog={closeDialog}
        resourceName="observing run"
      />
    </div>
  );
};

DeleteObservingRunDialog.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
  }).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

const ObservingRunList = ({ observingRuns, deletePermission }) => {
  const classes = useStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const nowDate = dayjs()
    .utc()
    .subtract(1.5, "day")
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const dt_month = dayjs.duration(1, "month");

  const [displayAll, setDisplayAll] = useState(false);

  const toggleDisplayAllCheckbox = () => {
    setDisplayAll(!displayAll);
  };

  let observingRunsToShow = [];
  if (!displayAll) {
    observingRuns?.forEach((run) => {
      const dt = dayjs.duration(
        dayjs(run.calendar_date)
          .add(run.duration - 1, "day")
          .diff(nowDate),
      );
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
          secondary
          onClick={toggleDisplayAllCheckbox}
          data-testid="observationRunButton"
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
                    groups,
                  )}
                </Link>
              }
              secondary={observingRunInfo(run, instrumentList, telescopeList)}
            />
            <ModifyObservingRunDialog
              run={run}
              modifyPermission={deletePermission}
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

ObservingRunList.propTypes = {
  observingRuns: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
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
