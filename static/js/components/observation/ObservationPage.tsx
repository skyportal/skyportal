import { useGetProfileQuery } from "../../ducks/profile";
import React, { useState } from "react";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import { makeStyles } from "tss-react/mui";
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

import {
  useGetObservationsQuery,
  useLazyGetObservationsQuery,
} from "../../ducks/observations";
import {
  useGetQueuedObservationsQuery,
  useLazyGetQueuedObservationsQuery,
} from "../../ducks/queued_observations";
import { useAppDispatch } from "../../types/hooks";

interface ObservationListProps {
  observations?: any;
  fetchParams: { pageNumber: number; numPerPage: number };
  handleTableChange: (...a: any[]) => void;
  handleFilterSubmit: (...a: any[]) => void;
  downloadCallback: (...a: any[]) => void;
}

const useStyles = makeStyles()((theme) => ({
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
}: ObservationListProps) => {
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

const QueuedObservationList = ({
  observations,
  fetchParams,
  handleTableChange,
  handleFilterSubmit,
  downloadCallback,
}: ObservationListProps) => {
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

const ObservationPage = () => {
  const { data: currentUser } = useGetProfileQuery();
  const dispatch = useAppDispatch();
  const { classes } = useStyles();

  const [fetchExecutedParams, setFetchExecutedParams] = useState<any>({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  const [fetchQueuedParams, setFetchQueuedParams] = useState<any>({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  const { data: observations } = useGetObservationsQuery(fetchExecutedParams);
  const [fetchObservations] = useLazyGetObservationsQuery();

  const { data: queuedObservations } =
    useGetQueuedObservationsQuery(fetchQueuedParams);
  const [fetchQueuedObservations] = useLazyGetQueuedObservationsQuery();

  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  const [tabIndex, setTabIndex] = React.useState(0);

  if (observations == null) {
    return <p>No observations available...</p>;
  }

  if (queuedObservations == null) {
    return <p>No queued observations available...</p>;
  }

  const handleChangeTab = (_event: any, newValue: number) => {
    setTabIndex(newValue);
  };

  const handleExecutedPageChange = async (
    page: number,
    numPerPage: number,
    sortData?: any,
  ) => {
    const params = {
      ...fetchExecutedParams,
      numPerPage,
      pageNumber: page + 1,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      params.sortBy = sortData.name;
      params.sortOrder = sortData.direction;
    }
    // Save state for future (triggers the observations query refetch)
    setFetchExecutedParams(params);
  };

  const handleQueuedPageChange = async (
    page: number,
    numPerPage: number,
    _sortData?: any,
  ) => {
    const params = {
      ...fetchQueuedParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future (triggers the queued observations query refetch)
    setFetchQueuedParams(params);
  };

  const handleExecutedTableSorting = async (sortData: any) => {
    const params = {
      ...fetchExecutedParams,
      pageNumber: 1,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchExecutedParams(params);
  };

  const handleQueuedTableSorting = async (sortData: any) => {
    const params = {
      ...fetchQueuedParams,
      pageNumber: 1,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchQueuedParams(params);
  };

  const handleExecutedTableChange = (action: string, tableState: any) => {
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

  const handleQueuedTableChange = (action: string, tableState: any) => {
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
    pageNumber: number,
    numPerPage: number,
    filterData?: any,
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
    // Save state for future (triggers the observations query refetch)
    setFetchExecutedParams(params);
  };

  const handleQueuedTableFilter = async (
    pageNumber: number,
    numPerPage: number,
    filterData?: any,
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
    // Save state for future (triggers the queued observations query refetch)
    setFetchQueuedParams(params);
  };

  const handleExecutedFilterSubmit = async (formData: any) => {
    const data = filterOutEmptyValues(formData);
    handleExecutedTableFilter(1, defaultNumPerPage, data);
  };

  const handleQueuedFilterSubmit = async (formData: any) => {
    const data = filterOutEmptyValues(formData);
    handleQueuedTableFilter(1, defaultNumPerPage, data);
  };

  const handleExecutedDownload = async () => {
    const observationsAll: any[] = [];
    if (observations.totalMatches === 0) {
      dispatch(showNotification("No observations to download", "warning"));
    } else {
      setDownloadProgressTotal(observations.totalMatches);
      for (
        let i = 1;
        i <=
        Math.ceil(observations.totalMatches / fetchExecutedParams.numPerPage);
        i += 1
      ) {
        const data = {
          ...fetchExecutedParams,
          pageNumber: i,
        };

        try {
          const result: any = await fetchObservations(data).unwrap();
          observationsAll.push(...result.observations);
          setDownloadProgressCurrent(observationsAll.length);
          setDownloadProgressTotal(observations.totalMatches);
        } catch {
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
    const observationsAll: any[] = [];

    if (queuedObservations.totalMatches === 0) {
      dispatch(showNotification("No observations to download", "warning"));
    } else {
      setDownloadProgressTotal(queuedObservations.totalMatches);
      for (
        let i = 1;
        i <=
        Math.ceil(
          queuedObservations.totalMatches / fetchQueuedParams.numPerPage,
        );
        i += 1
      ) {
        const data = {
          ...fetchQueuedParams,
          pageNumber: i,
        };

        try {
          const result: any = await fetchQueuedObservations(data).unwrap();
          observationsAll.push(...result.observations);
          setDownloadProgressCurrent(observationsAll.length);
          setDownloadProgressTotal(queuedObservations.totalMatches);
        } catch {
          // break the loop and set progress to 0 and show error message
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (queuedObservations.observations?.length === 0) {
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
    if (observationsAll?.length === queuedObservations.totalMatches?.length) {
      dispatch(showNotification("Observations downloaded successfully"));
    }
    return observationsAll;
  };

  return (
    <Grid container spacing={3}>
      <Grid size={12}>
        <Tabs value={tabIndex} onChange={handleChangeTab} centered>
          <Tab label="Executed Observations" />
          <Tab label="Queued Observations" />
          {currentUser?.permissions?.includes("System admin") && (
            <Tab label="Queue Interactions" />
          )}
        </Tabs>
      </Grid>
      {tabIndex === 0 && (
        <Grid size={12} style={{ paddingTop: 0 }}>
          <div className={classes.Container}>
            <ExecutedObservationList
              observations={observations}
              fetchParams={fetchExecutedParams}
              handleTableChange={handleExecutedTableChange}
              handleFilterSubmit={handleExecutedFilterSubmit}
              downloadCallback={handleExecutedDownload}
            />
            <Dialog open={downloadProgressTotal > 0} maxWidth="md">
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
        <Grid size={12} style={{ paddingTop: 0 }}>
          <div className={classes.Container}>
            <QueuedObservationList
              observations={queuedObservations}
              fetchParams={fetchQueuedParams}
              handleTableChange={handleQueuedTableChange}
              handleFilterSubmit={handleQueuedFilterSubmit}
              downloadCallback={handleQueuedDownload}
            />
          </div>
        </Grid>
      )}
      {tabIndex === 2 && currentUser?.permissions?.includes("System admin") && (
        <Grid container size={12} spacing={1} style={{ paddingTop: 0 }}>
          <Grid size={{ xs: 12, lg: 6 }}>
            <Paper style={{ padding: "1rem" }}>
              <Typography className={classes.accordionHeading}>
                Queue Interaction
              </Typography>
              <div className={classes.Container}>
                <QueueAPIDisplay />
              </div>
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
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

export default ObservationPage;
