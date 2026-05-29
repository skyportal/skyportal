import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid";
import { ToggleButton, ToggleButtonGroup } from "@mui/material";
import PropTypes from "prop-types";
import { showNotification } from "baselayer/components/Notifications";

import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import duration from "dayjs/plugin/duration";
import relativeTime from "dayjs/plugin/relativeTime";
import * as observingRunActions from "../../ducks/observingRun";

import Button from "../Button";
import Paper from "../Paper";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import { observingRunTitle } from "./AssignmentForm";
import NewObservingRun from "./NewObservingRun";
import ModifyObservingRun from "./ModifyObservingRun";

dayjs.extend(utc);
dayjs.extend(duration);
dayjs.extend(relativeTime);

export const observingRunInfo = (
  observingRun,
  instrumentList,
  telescopeList,
) => {
  const { instrument_id } = observingRun;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];
  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!observingRun?.calendar_date || !instrument?.name || !telescope?.name) {
    return <CircularProgress />;
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

const ObservingRunList = ({ observingRuns, managePermission }) => {
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);
  const [observingRunToEdit, setObservingRunToEdit] = useState(null);
  const [observingRunToDelete, setObservingRunToDelete] = useState(null);
  const [displayAll, setDisplayAll] = useState(false);

  const nowDate = dayjs()
    .utc()
    .subtract(1.5, "day")
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const dt_month = dayjs.duration(1, "month");

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

  const deleteObservingRun = () => {
    dispatch(observingRunActions.deleteObservingRun(observingRunToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Observing run deleted"));
          setObservingRunToDelete(null);
        }
      },
    );
  };

  return (
    <Paper>
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        flexWrap="wrap"
      >
        <Typography variant="h6">List of Observing Runs</Typography>

        <ToggleButtonGroup
          value={displayAll}
          exclusive
          onChange={(e, newValue) => {
            if (newValue !== null) setDisplayAll(newValue);
          }}
          data-testid="observationRunButton"
        >
          <ToggleButton value={false}>Upcoming runs</ToggleButton>
          <ToggleButton value={true}>All runs</ToggleButton>
        </ToggleButtonGroup>
      </Box>
      <List component="nav">
        {observingRunsToShow?.length > 0 ? (
          observingRunsToShow.map((run) => (
            <ListItem key={run.id}>
              <ListItemText
                primary={
                  <Link to={`/run/${run.id}`} role="link">
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
              {managePermission && (
                <>
                  <Button
                    onClick={() => setObservingRunToEdit(run.id)}
                    size="small"
                  >
                    <EditIcon />
                  </Button>
                  <Button
                    onClick={() => setObservingRunToDelete(run.id)}
                    size="small"
                    color="error"
                  >
                    <DeleteIcon />
                  </Button>
                </>
              )}
            </ListItem>
          ))
        ) : (
          <Typography variant="body1" color="textSecondary" mt={2}>
            No observing runs to show.
          </Typography>
        )}
      </List>
      <Dialog
        open={observingRunToEdit !== null}
        onClose={() => setObservingRunToEdit(null)}
      >
        <DialogTitle>Edit Observing Run</DialogTitle>
        <DialogContent dividers>
          <ModifyObservingRun
            run_id={observingRunToEdit}
            onClose={() => setObservingRunToEdit(null)}
          />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteObservingRun}
        dialogOpen={observingRunToDelete !== null}
        closeDialog={() => setObservingRunToDelete(null)}
        resourceName="observing run"
      />
    </Paper>
  );
};

ObservingRunList.propTypes = {
  observingRuns: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      calendar_date: PropTypes.string.isRequired,
      duration: PropTypes.number.isRequired,
      observers: PropTypes.string,
    }),
  ).isRequired,
  managePermission: PropTypes.bool.isRequired,
};

const ObservingRunPage = () => {
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const currentUser = useSelector((state) => state.profile);

  const managePermission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage observing runs");

  return (
    <Grid container spacing={3}>
      <Grid size={{ md: 6, sm: 12 }}>
        <ObservingRunList
          observingRuns={observingRunList}
          managePermission={managePermission}
        />
      </Grid>
      <Grid size={{ md: 6, sm: 12 }}>
        <NewObservingRun />
      </Grid>
    </Grid>
  );
};

ObservingRunList.propTypes = {
  observingRuns: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      calendar_date: PropTypes.string.isRequired,
      duration: PropTypes.number.isRequired,
      observers: PropTypes.string,
    }),
  ).isRequired,
  managePermission: PropTypes.bool.isRequired,
};

export default ObservingRunPage;
