import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import PropTypes from "prop-types";

import ExecutedObservationsTable from "./ExecutedObservationsTable";
import QueuedObservationsTable from "./QueuedObservationsTable";
import NewObservation from "./NewObservation";
import NewAPIObservation from "./NewAPIObservation";
import NewAPIQueuedObservation from "./NewAPIQueuedObservation";

import * as observationsActions from "../ducks/observations";
import * as queuedObservationsActions from "../ducks/queued_observations";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  paperContent: {
    padding: "1rem",
  },
}));

const defaultNumPerPage = 10;

const ExecutedObservationList = ({
  observations,
  fetchParams,
  handleTableChange,
}) => {
  if (!observations?.observations || observations.observations.length === 0) {
    return <p>No observations available...</p>;
  }

  return (
    <ExecutedObservationsTable
      observations={observations.observations}
      pageNumber={fetchParams.pageNumber}
      numPerPage={fetchParams.numPerPage}
      handleTableChange={handleTableChange}
      totalMatches={observations.totalMatches}
    />
  );
};

ExecutedObservationList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  observations: PropTypes.arrayOf(PropTypes.any).isRequired,
  handleTableChange: PropTypes.func.isRequired,
  fetchParams: PropTypes.shape({
    pageNumber: PropTypes.number,
    numPerPage: PropTypes.number,
  }).isRequired,
};

const QueuedObservationList = ({
  observations,
  fetchParams,
  handleTableChange,
}) => {
  if (!observations?.observations || observations.observations.length === 0) {
    return <p>No observations available...</p>;
  }

  return (
    <QueuedObservationsTable
      observations={observations.observations}
      pageNumber={fetchParams.pageNumber}
      numPerPage={fetchParams.numPerPage}
      handleTableChange={handleTableChange}
      totalMatches={observations.totalMatches}
    />
  );
};

QueuedObservationList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  observations: PropTypes.arrayOf(PropTypes.any).isRequired,
  handleTableChange: PropTypes.func.isRequired,
  fetchParams: PropTypes.shape({
    pageNumber: PropTypes.number,
    numPerPage: PropTypes.number,
  }).isRequired,
};

const ObservationPage = () => {
  const observations = useSelector((state) => state.observations);
  const queued_observations = useSelector((state) => state.queued_observations);
  const currentUser = useSelector((state) => state.profile);
  const dispatch = useDispatch();
  const classes = useStyles();

  const [fetchExecutedParams, setFetchExecutedParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  const [fetchQueuedParams, setFetchQueuedParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  useEffect(() => {
    const params = {
      ...fetchExecutedParams,
      numPerPage: defaultNumPerPage,
      pageNumber: 1,
    };
    dispatch(observationsActions.fetchObservations(params));
  }, [dispatch]);

  useEffect(() => {
    const params = {
      ...fetchQueuedParams,
      numPerPage: defaultNumPerPage,
      pageNumber: 1,
    };
    dispatch(queuedObservationsActions.fetchQueuedObservations(params));
  }, [dispatch]);

  if (!observations) {
    return <p>No observations available...</p>;
  }

  if (!queued_observations) {
    return <p>No queued observations available...</p>;
  }

  const handleExecutedPageChange = async (page, numPerPage) => {
    const params = {
      ...fetchExecutedParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future
    setFetchExecutedParams(params);
    await dispatch(observationsActions.fetchObservations(params));
  };

  const handleQueuedPageChange = async (page, numPerPage) => {
    const params = {
      ...fetchQueuedParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future
    setFetchQueuedParams(params);
    await dispatch(queuedObservationsActions.fetchQueuedObservations(params));
  };

  const handleExecutedTableChange = (action, tableState) => {
    if (action === "changePage") {
      handleExecutedPageChange(tableState.page, tableState.rowsPerPage);
    }
  };

  const handleQueuedTableChange = (action, tableState) => {
    if (action === "changePage") {
      handleQueuedPageChange(tableState.page, tableState.rowsPerPage);
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Executed Observations</Typography>
            <ExecutedObservationList
              observations={observations.observations}
              fetchParams={fetchExecutedParams}
              handleTableChange={handleExecutedTableChange}
            />
          </div>
        </Paper>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Queued Observations</Typography>
            <QueuedObservationList
              observations={queued_observations.queued_observations}
              fetchParams={fetchQueuedParams}
              handleTableChange={handleQueuedTableChange}
            />
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("System admin") && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add New Observations</Typography>
              <NewObservation />
            </div>
          </Paper>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">
                Add API Executed Observations
              </Typography>
              <NewAPIObservation />
            </div>
          </Paper>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add API Queued Observations</Typography>
              <NewAPIQueuedObservation />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

ExecutedObservationList.propTypes = {
  observations: PropTypes.shape({
    observations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.string,
        obstime: PropTypes.instanceOf(Date),
        filt: PropTypes.string,
        exposure_time: PropTypes.number,
        airmass: PropTypes.number,
        limmag: PropTypes.number,
        seeing: PropTypes.number,
        processed_fraction: PropTypes.number,
      })
    ),
    totalMatches: PropTypes.number,
  }),
};

QueuedObservationList.propTypes = {
  observations: PropTypes.shape({
    observations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.string,
        obstime: PropTypes.instanceOf(Date),
        filt: PropTypes.string,
        exposure_time: PropTypes.number,
        queue_name: PropTypes.number,
        validity_window_start: PropTypes.instanceOf(Date),
        validity_window_end: PropTypes.instanceOf(Date),
      })
    ),
    totalMatches: PropTypes.number,
  }),
};

ExecutedObservationList.defaultProps = {
  observations: null,
};

QueuedObservationList.defaultProps = {
  observations: null,
};

export default ObservationPage;
