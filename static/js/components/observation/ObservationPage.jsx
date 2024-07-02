import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import { showNotification } from "baselayer/components/Notifications";
import { filterOutEmptyValues } from "../../API";
import ExecutedObservationsTable from "./ExecutedObservationsTable";
import QueuedObservationsTable from "./QueuedObservationsTable";
import QueueAPIDisplay from "./QueueAPIDisplay";
import ProgressIndicator from "../ProgressIndicators";
import SkymapTriggerAPIDisplay from "./SkymapTriggerAPIDisplay";

import * as observationsActions from "../../ducks/observations";
import * as queuedObservationsActions from "../../ducks/queued_observations";

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
  handleFilterSubmit,
  downloadCallback,
}) => {
  if (!observations?.observations) {
    return <p>No observations available...</p>;
  }

  return (
    <ExecutedObservationsTable
      observations={observations.observations}
      pageNumber={fetchParams.pageNumber}
      numPerPage={fetchParams.numPerPage}
      handleTableChange={handleTableChange}
      handleFilterSubmit={handleFilterSubmit}
      totalMatches={observations.totalMatches}
      downloadCallback={downloadCallback}
    />
  );
};

ExecutedObservationList.propTypes = {
  observations: PropTypes.arrayOf(PropTypes.any).isRequired,
  handleTableChange: PropTypes.func.isRequired,
  handleFilterSubmit: PropTypes.func.isRequired,
  fetchParams: PropTypes.shape({
    pageNumber: PropTypes.number,
    numPerPage: PropTypes.number,
  }).isRequired,
  downloadCallback: PropTypes.func.isRequired,
};

const QueuedObservationList = ({
  observations,
  fetchParams,
  handleTableChange,
  handleFilterSubmit,
  downloadCallback,
}) => {
  if (!observations?.observations) {
    return <p>No observations available...</p>;
  }

  return (
    <QueuedObservationsTable
      observations={observations.observations}
      pageNumber={fetchParams.pageNumber}
      numPerPage={fetchParams.numPerPage}
      handleTableChange={handleTableChange}
      handleFilterSubmit={handleFilterSubmit}
      totalMatches={observations.totalMatches}
      downloadCallback={downloadCallback}
    />
  );
};

QueuedObservationList.propTypes = {
  observations: PropTypes.arrayOf(PropTypes.any).isRequired,
  handleTableChange: PropTypes.func.isRequired,
  handleFilterSubmit: PropTypes.func.isRequired,
  fetchParams: PropTypes.shape({
    pageNumber: PropTypes.number,
    numPerPage: PropTypes.number,
  }).isRequired,
  downloadCallback: PropTypes.func.isRequired,
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

  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  const [tabIndex, setTabIndex] = React.useState(0);

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

  const handleChangeTab = (event, newValue) => {
    setTabIndex(newValue);
  };

  const handleExecutedPageChange = async (page, numPerPage, sortData) => {
    const params = {
      ...fetchExecutedParams,
      numPerPage,
      pageNumber: page + 1,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      params.sortBy = sortData.name;
      params.sortOrder = sortData.direction;
    }
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

  const handleExecutedTableSorting = async (sortData) => {
    const params = {
      ...fetchExecutedParams,
      pageNumber: 1,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchExecutedParams(params);
    await dispatch(observationsActions.fetchObservations(params));
  };

  const handleQueuedTableSorting = async (sortData) => {
    const params = {
      ...fetchQueuedParams,
      pageNumber: 1,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchQueuedParams(params);
    await dispatch(queuedObservationsActions.fetchQueuedObservations(params));
  };

  const handleExecutedTableChange = (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      handleExecutedPageChange(
        tableState.page + 1,
        tableState.rowsPerPage,
        tableState.sortOrder,
      );
    }
    if (action === "sort") {
      if (tableState.sortOrder.direction === "none") {
        handleExecutedPageChange(1, tableState.rowsPerPage, {});
      } else {
        handleExecutedTableSorting(tableState.sortOrder);
      }
    }
  };

  const handleQueuedTableChange = (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      handleQueuedPageChange(tableState.page, tableState.rowsPerPage);
    }
    if (action === "sort") {
      if (tableState.sortOrder.direction === "none") {
        handleQueuedPageChange(1, tableState.rowsPerPage, {});
      } else {
        handleQueuedTableSorting(tableState.sortOrder);
      }
    }
  };

  const handleExecutedTableFilter = async (
    pageNumber,
    numPerPage,
    filterData,
  ) => {
    const params = {
      ...fetchExecutedParams,
      pageNumber,
      numPerPage,
    };
    if (filterData && Object.keys(filterData).length > 0) {
      params.startDate = filterData.startDate;
      params.endDate = filterData.endDate;
      params.instrumentName = filterData.instrumentName;
    }
    // Save state for future
    setFetchExecutedParams(params);
    await dispatch(observationsActions.fetchObservations(params));
  };

  const handleQueuedTableFilter = async (
    pageNumber,
    numPerPage,
    filterData,
  ) => {
    const params = {
      ...fetchQueuedParams,
      pageNumber,
      numPerPage,
    };
    if (filterData && Object.keys(filterData).length > 0) {
      params.startDate = filterData.startDate;
      params.endDate = filterData.endDate;
      params.instrumentName = filterData.instrumentName;
    }
    // Save state for future
    setFetchQueuedParams(params);
    await dispatch(queuedObservationsActions.fetchQueuedObservations(params));
  };

  const handleExecutedFilterSubmit = async (formData) => {
    const data = filterOutEmptyValues(formData);
    handleExecutedTableFilter(1, defaultNumPerPage, data);
  };

  const handleQueuedFilterSubmit = async (formData) => {
    const data = filterOutEmptyValues(formData);
    handleQueuedTableFilter(1, defaultNumPerPage, data);
  };

  const handleExecutedDownload = async () => {
    const observationsAll = [];
    if (observations.observations.totalMatches === 0) {
      dispatch(showNotification("No observations to download", "warning"));
    } else {
      setDownloadProgressTotal(observations.observations.totalMatches);
      for (
        let i = 1;
        i <=
        Math.ceil(
          observations.observations.totalMatches /
            fetchExecutedParams.numPerPage,
        );
        i += 1
      ) {
        const data = {
          ...fetchExecutedParams,
          pageNumber: i,
        };

        const result = await dispatch(
          observationsActions.fetchObservations(data),
        );
        if (result && result.data && result?.status === "success") {
          observationsAll.push(...result.data.observations);
          setDownloadProgressCurrent(observationsAll.length);
          setDownloadProgressTotal(observations.observations.totalMatches);
        } else if (result && result?.status !== "success") {
          // break the loop and set progress to 0 and show error message
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (observations.observations?.length === 0) {
            dispatch(
              showNotification(
                "Failed to fetch some observations. Download cancelled.",
                "error",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Failed to fetch some observations, please try again. Observations fetched so far will be downloaded.",
                "error",
              ),
            );
          }
          break;
        }
      }
    }
    setDownloadProgressCurrent(0);
    setDownloadProgressTotal(0);
    if (observationsAll?.length === observations.totalMatches?.length) {
      dispatch(showNotification("Observations downloaded successfully"));
    }
    return observationsAll;
  };

  const handleQueuedDownload = async () => {
    const observationsAll = [];

    if (queued_observations.queued_observations.totalMatches === 0) {
      dispatch(showNotification("No observations to download", "warning"));
    } else {
      setDownloadProgressTotal(
        queued_observations.queued_observations.totalMatches,
      );
      for (
        let i = 1;
        i <=
        Math.ceil(
          queued_observations.queued_observations.totalMatches /
            fetchQueuedParams.numPerPage,
        );
        i += 1
      ) {
        const data = {
          ...fetchQueuedParams,
          pageNumber: i,
        };

        const result = await dispatch(
          queuedObservationsActions.fetchQueuedObservations(data),
        );
        if (result && result.data && result?.status === "success") {
          observationsAll.push(...result.data.observations);
          setDownloadProgressCurrent(observationsAll.length);
          setDownloadProgressTotal(
            queued_observations.queued_observations.totalMatches,
          );
        } else if (result && result?.status !== "success") {
          // break the loop and set progress to 0 and show error message
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (
            queued_observations.queued_observations.observations?.length === 0
          ) {
            dispatch(
              showNotification(
                "Failed to fetch some observations. Download cancelled.",
                "error",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Failed to fetch some observations, please try again. Observations fetched so far will be downloaded.",
                "error",
              ),
            );
          }
          break;
        }
      }
    }
    setDownloadProgressCurrent(0);
    setDownloadProgressTotal(0);
    if (
      observationsAll?.length ===
      queued_observations.queued_observations.totalMatches?.length
    ) {
      dispatch(showNotification("Observations downloaded successfully"));
    }
    return observationsAll;
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Tabs value={tabIndex} onChange={handleChangeTab} centered>
          <Tab label="Executed Observations" />
          <Tab label="Queued Observations" />
          {currentUser.permissions?.includes("System admin") && (
            <Tab label="Queue Interactions" />
          )}
        </Tabs>
      </Grid>
      {tabIndex === 0 && (
        <Grid item xs={12} style={{ paddingTop: 0 }}>
          <div className={classes.Container}>
            <ExecutedObservationList
              observations={observations.observations}
              fetchParams={fetchExecutedParams}
              handleTableChange={handleExecutedTableChange}
              handleFilterSubmit={handleExecutedFilterSubmit}
              downloadCallback={handleExecutedDownload}
            />
            <Dialog
              open={downloadProgressTotal > 0}
              style={{ position: "fixed" }}
              maxWidth="md"
            >
              <DialogContent
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                <Typography variant="h6" display="inline">
                  Downloading {downloadProgressTotal} observations
                </Typography>
                <div
                  style={{
                    height: "5rem",
                    width: "5rem",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    alignItems: "center",
                  }}
                >
                  <ProgressIndicator
                    current={downloadProgressCurrent}
                    total={downloadProgressTotal}
                    percentage={false}
                  />
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </Grid>
      )}
      {tabIndex === 1 && (
        <Grid item xs={12} style={{ paddingTop: 0 }}>
          <div className={classes.Container}>
            <QueuedObservationList
              observations={queued_observations.queued_observations}
              fetchParams={fetchQueuedParams}
              handleTableChange={handleQueuedTableChange}
              handleFilterSubmit={handleQueuedFilterSubmit}
              downloadCallback={handleQueuedDownload}
            />
          </div>
        </Grid>
      )}
      {tabIndex === 2 && currentUser.permissions?.includes("System admin") && (
        <Grid container item xs={12} spacing={1} style={{ paddingTop: 0 }}>
          <Grid item xs={12} lg={6}>
            <Paper style={{ padding: "1rem" }}>
              <Typography className={classes.accordionHeading}>
                Queue Interaction
              </Typography>
              <div className={classes.Container}>
                <QueueAPIDisplay />
              </div>
            </Paper>
          </Grid>
          <Grid item xs={12} lg={6}>
            <Paper style={{ padding: "1rem" }}>
              <Typography className={classes.accordionHeading}>
                Skymap Queue Interaction
              </Typography>
              <div className={classes.Container}>
                <SkymapTriggerAPIDisplay />
              </div>
            </Paper>
          </Grid>
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
      }),
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
      }),
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
