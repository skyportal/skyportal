import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Divider from "@mui/material/Divider";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";

import ExecutedObservationsTable from "./ExecutedObservationsTable";
import QueuedObservationsTable from "./QueuedObservationsTable";
import NewObservation from "./NewObservation";
import NewAPIObservation from "./NewAPIObservation";
import NewAPIQueuedObservation from "./NewAPIQueuedObservation";
import QueueAPIDisplay from "./QueueAPIDisplay";

import * as observationsActions from "../ducks/observations";
import * as queuedObservationsActions from "../ducks/queued_observations";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  header: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  content: {
    margin: "1rem",
  },
  paperContent: {
    marginBottom: "1rem",
  },
  dividerHeader: {
    background: theme.palette.primary.main,
    height: "2px",
  },
  divider: {
    background: theme.palette.secondary.main,
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  Container: {
    display: "flex",
    overflow: "hidden",
    flexDirection: "column",
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
    if (action === "changePage" || action === "changeRowsPerPage") {
      handleExecutedPageChange(tableState.page, tableState.rowsPerPage);
    }
  };

  const handleQueuedTableChange = (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      handleQueuedPageChange(tableState.page, tableState.rowsPerPage);
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Accordion defaultExpanded elevation={0}>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="executed-observations-content"
                id="executed-observations-header"
              >
                <Typography className={classes.accordionHeading}>
                  List of Executed Observations
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <div className={classes.Container}>
                  <ExecutedObservationList
                    observations={observations.observations}
                    fetchParams={fetchExecutedParams}
                    handleTableChange={handleExecutedTableChange}
                  />
                </div>
              </AccordionDetails>
            </Accordion>
          </div>
        </Paper>
        <Paper>
          <div className={classes.paperContent}>
            <Accordion defaultExpanded elevation={0}>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="queued-observations-content"
                id="queued-observations-header"
              >
                <Typography className={classes.accordionHeading}>
                  List of Queued Observations
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <div className={classes.Container}>
                  <QueuedObservationList
                    observations={queued_observations.queued_observations}
                    fetchParams={fetchQueuedParams}
                    handleTableChange={handleQueuedTableChange}
                  />
                </div>
              </AccordionDetails>
            </Accordion>
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("System admin") && (
        <Grid item md={6} sm={12}>
          <Paper className={classes.paperContent}>
            <div>
              <Accordion defaultExpanded elevation={0}>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="add-new-observations-content"
                  id="add-new-observations-header"
                >
                  <Typography className={classes.accordionHeading}>
                    Add New Observations
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <div>
                    <br style={{ marginBottom: "1rem" }} />
                    <Divider
                      variant="middle"
                      className={classes.dividerHeader}
                    />
                    <br />
                    <div className={classes.content}>
                      <Typography variant="h6">
                        Add Observations from File
                      </Typography>
                      <NewObservation />
                    </div>
                    <br />
                    <Divider variant="middle" className={classes.divider} />
                    <br />
                    <div className={classes.content}>
                      <Typography variant="h6">
                        Add API Executed Observations
                      </Typography>
                      <NewAPIObservation />
                    </div>
                    <br />
                    <Divider variant="middle" className={classes.divider} />
                    <br />
                    <div className={classes.content}>
                      <Typography variant="h6">
                        Add API Queued Observations
                      </Typography>
                      <NewAPIQueuedObservation />
                    </div>
                  </div>
                </AccordionDetails>
              </Accordion>
            </div>
          </Paper>
          <Paper>
            <div className={classes.paperContent}>
              <Accordion defaultExpanded elevation={0}>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="queue-interaction-content"
                  id="queue-interaction-header"
                >
                  <Typography className={classes.accordionHeading}>
                    Queue Interaction
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <div className={classes.Container}>
                    <QueueAPIDisplay />
                  </div>
                </AccordionDetails>
              </Accordion>
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
