import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
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
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Box from "@mui/material/Box";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import duration from "dayjs/plugin/duration";
import relativeTime from "dayjs/plugin/relativeTime";

import { Link } from "react-router-dom";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import { observingRunTitle } from "./RunSummary";
import NewObservingRun from "./NewObservingRun";
import ModifyObservingRun from "./ModifyObservingRun";

import * as observingRunActions from "../../ducks/observingRun";
import { utcString } from "../../utils/format";

dayjs.extend(utc);
dayjs.extend(duration);
dayjs.extend(relativeTime);

const useStyles = makeStyles(() => ({
  paperContent: {
    padding: "1rem",
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
  const [observingRunToModify, setObservingRunToModify] = useState(null);
  return (
    <div>
      <Button
        id="edit_button"
        onClick={() => setObservingRunToModify(run.id)}
        disabled={!modifyPermission}
        size="small"
      >
        <EditIcon />
      </Button>
      <Dialog
        open={!!observingRunToModify}
        onClose={() => observingRunToModify(null)}
      >
        <DialogTitle>Edit Observing Run</DialogTitle>
        <DialogContent dividers>
          <ModifyObservingRun
            run_id={observingRunToModify}
            onClose={() => observingRunToModify(null)}
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
        id="delete_button"
        onClick={() => openDialog(run.id)}
        disabled={!deletePermission}
        size="small"
        color="error"
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

const ObservingRunPage = () => {
  const classes = useStyles();
  const currentUser = useSelector((state) => state.profile);
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);
  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage observing runs");
  const [displayAll, setDisplayAll] = useState(false);

  const minusOneAndHalfDay = utcString(dayjs().subtract(1.5, "day"));
  const dt_month = dayjs.duration(1, "month");

  let observingRunsToShow = [];
  if (!displayAll) {
    observingRunList?.forEach((run) => {
      const dt = dayjs.duration(
        dayjs(run.calendar_date)
          .add(run.duration - 1, "day")
          .diff(minusOneAndHalfDay),
      );
      if (dt.$ms < dt_month.$ms && dt.$ms > 0) {
        observingRunsToShow.push(run);
      }
    });
  } else {
    observingRunsToShow = [...observingRunList];
  }

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper className={classes.paperContent}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              flexWrap: "wrap",
            }}
          >
            <Typography variant="h6">
              {displayAll ? "All observing" : "Upcoming observing"} runs
            </Typography>
            <Button
              secondary
              onClick={() => setDisplayAll(!displayAll)}
              data-testid="observationRunButton"
            >
              {displayAll ? "Show only upcoming" : "Show all"} observing runs
            </Button>
          </Box>
          <List>
            {!observingRunsToShow?.length ? (
              <ListItem>
                <Typography variant="body1" color="textSecondary">
                  No observing runs to display...
                </Typography>
              </ListItem>
            ) : (
              observingRunsToShow?.map((run) => (
                <ListItem key={run.id}>
                  <ListItemText
                    primary={
                      <Link to={`/run/${run.id}`}>
                        {observingRunTitle(
                          run,
                          instrumentList,
                          telescopeList,
                          groups,
                        )}
                      </Link>
                    }
                    secondary={observingRunInfo(
                      run,
                      instrumentList,
                      telescopeList,
                    )}
                  />
                  <ModifyObservingRunDialog
                    run={run}
                    modifyPermission={permission}
                  />
                  <DeleteObservingRunDialog
                    run={run}
                    deletePermission={permission}
                  />
                </ListItem>
              ))
            )}
          </List>
        </Paper>
      </Grid>
      <Grid item md={6} sm={12}>
        <Paper className={classes.paperContent}>
          <Typography variant="h6">Add a New Observing Run</Typography>
          <NewObservingRun />
        </Paper>
      </Grid>
    </Grid>
  );
};

export default ObservingRunPage;
